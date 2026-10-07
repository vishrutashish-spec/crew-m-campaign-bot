"""
Biomarker out-of-range analysis by age cohort.

DATA ACCESSED: local de-identified exports data/hc_data.xlsx (health checkup
labs) and data/th_consultation_data.xlsx (telehealth consults, supplies member
age). Member and org IDs are opaque tokens; no names, phones or emails exist in
either file.
WHY: population-health report - which biomarkers are most often out of range and
in which age cohort, plus consult-demand patterns.
PROTECTION: every output is an aggregate count/percentage. Cohort cells with
n<100 are suppressed from headline claims. Nothing is written outside the repo's
own report file. No per-member rows are printed or exported.
WINDOW: bounded to the 12 months 2025-08-01 .. 2026-07-31 (<=1 year).
"""
import sys, json, warnings
import pandas as pd, numpy as np
sys.path.insert(0, '/Users/vishrut/insurwreck/scripts/health-report')
from ranges import FLAGS, PLAUSIBLE, ALIASES, FAMILY_ORDER
warnings.filterwarnings('ignore')

SCRATCH = '/private/tmp/claude-502/-Users-vishrut-insurwreck/c53c0c8e-b2fd-4e11-b930-2348a6360bb5/scratchpad'
WIN_START, WIN_END = pd.Timestamp('2025-08-01'), pd.Timestamp('2026-07-31')

COHORTS = [('Under 20', 0, 20), ('21-25', 21, 25), ('26-35', 26, 35),
           ('36-40', 36, 40), ('41-50', 41, 50), ('51+', 51, 120)]
COHORT_NAMES = [c[0] for c in COHORTS]

def cohort_of(age):
    for name, lo, hi in COHORTS:
        if lo <= age <= hi:
            return name
    return None

# ---------- load ----------
hc = pd.read_pickle(f'{SCRATCH}/hc.pkl')
th = pd.read_pickle(f'{SCRATCH}/th.pkl')

# ---------- age join (validated) ----------
# The telehealth file records the age of the PATIENT on each consult, not the
# member. 15,486 of 133,218 consults are paediatric and 8,169 members show more
# than one patient_gender - i.e. members book for children, spouses and parents
# under their own member_id. A naive member -> median-age map therefore maps a
# parent's labs onto a toddler's age. Guards applied:
#   1. drop consults with age <18 and drop Paediatrics / Veterinary specialties
#   2. key the age by (member_id, patient_gender) and join on the HC booking's
#      own gender, so a male member's labs cannot inherit his wife's age
#   3. restrict the cohort analysis to patient_relationship == 'SELF' bookings
#   4. per member-gender, take the modal 2-year age bucket (birthday drift), so
#      a same-gender parent's occasional consult cannot drag the age
th_all = th.copy()
th_win = th_all[(th_all.appointment_created_at >= WIN_START) & (th_all.appointment_created_at <= WIN_END)]
tha = th_all[(th_all.patient_age >= 18) & (th_all.patient_age <= 95)]
tha = tha[~tha.specialist_specialty.isin(['Pediatrician', 'Veterinary Medicine'])]

def modal_age(s):
    b = (s // 2 * 2)
    return s[b == b.value_counts().idxmax()].median()

grp = tha.groupby(['unique_member_id', 'patient_gender']).patient_age
age_gender = grp.agg(modal_age).rename('age').reset_index()
age_gender['n_consults'] = grp.size().values

# ---------- coalesce duplicate assay columns ----------
for primary, alist in ALIASES.items():
    present = [c for c in alist if c in hc.columns]
    if len(present) > 1:
        base = pd.to_numeric(hc[present[0]], errors='coerce')
        for extra in present[1:]:
            base = base.fillna(pd.to_numeric(hc[extra], errors='coerce'))
        hc[primary] = base

# ---------- window + numeric coercion + plausibility caps ----------
hc = hc[(hc.appointment_date >= WIN_START) & (hc.appointment_date <= WIN_END)].copy()
markers = sorted({f[0] for f in FLAGS})
for m in markers:
    if m not in hc.columns:
        print(f'WARN missing marker column: {m}', file=sys.stderr); continue
    s = pd.to_numeric(hc[m], errors='coerce')
    lo, hi = PLAUSIBLE.get(m, (None, None))
    if lo is not None:
        s = s.where((s >= lo) & (s <= hi))
    hc[m] = s

# one booking per member: the most recent in window (avoid double counting repeats)
hc = hc.sort_values('appointment_date').drop_duplicates(['member_id', 'patient_relationship'], keep='last')
hc['sex'] = hc.patient_gender
_ag = age_gender.rename(columns={'unique_member_id': 'member_id', 'patient_gender': 'sex'})
hc = hc.merge(_ag[['member_id', 'sex', 'age', 'n_consults']], on=['member_id', 'sex'], how='left')
hc.loc[hc.patient_relationship != 'SELF', 'age'] = np.nan  # age is only trustworthy for SELF
hc['cohort'] = hc.age.apply(lambda a: cohort_of(a) if pd.notna(a) else None)

# ---------- evaluate flags ----------
def cut(v, sex):
    if isinstance(v, dict):
        return sex.map(v)
    return v

flag_cols, flag_meta = [], []
for f in FLAGS:
    col, label, family, lo, hi, sev, source = f[:7]
    if col not in hc.columns:
        continue
    s = hc[col]
    if len(f) > 7 and f[7] == 'band':
        blo, bhi = f[8], f[9]
        bad = (s >= blo) & (s <= bhi)
    else:
        bad = pd.Series(False, index=hc.index)
        if lo is not None:
            bad = bad | (s < cut(lo, hc.sex))
        if hi is not None:
            bad = bad | (s > cut(hi, hc.sex))
    key = f'FLAG::{label}'
    hc[key] = np.where(s.notna(), bad, np.nan)
    flag_cols.append(key)
    flag_meta.append(dict(key=key, marker=col, label=label, family=family,
                          severity=sev, source=source))

# ---------- summaries ----------
def rate(sub, key):
    s = sub[key].dropna()
    return (len(s), s.sum(), 100 * s.mean() if len(s) else np.nan)

out = {}
out['coverage'] = dict(
    hc_bookings_in_window=int(len(hc)),
    hc_members=int(hc.member_id.nunique()),
    orgs=int(hc.organisation_id.nunique()),
    with_age=int(hc.cohort.notna().sum()),
    window=[str(WIN_START.date()), str(WIN_END.date())],
    th_consults_in_window=int(len(th_win)),
    self_bookings=int((hc.patient_relationship=='SELF').sum()),
    th_members_in_window=int(th_win.unique_member_id.nunique()),
    corporate=int((hc.package == 'CORPORATE').sum()),
    retail=int((hc.package == 'RETAIL').sum()),
    male=int((hc.sex == 'MALE').sum()), female=int((hc.sex == 'FEMALE').sum()),
)

aged = hc[hc.cohort.notna()]
out['cohort_sizes'] = {c: int((aged.cohort == c).sum()) for c in COHORT_NAMES}
out['age_stats'] = dict(median=float(aged.age.median()), mean=round(float(aged.age.mean()), 1),
                        p90=float(aged.age.quantile(.9)))

rows = []
for m in flag_meta:
    n, k, p = rate(hc, m['key'])
    r = dict(**{x: m[x] for x in ('label', 'marker', 'family', 'severity', 'source')},
             tested=int(n), flagged=int(k), pct=round(p, 1) if n else None)
    for c in COHORT_NAMES:
        cn, ck, cp = rate(aged[aged.cohort == c], m['key'])
        r[f'{c}_n'] = int(cn); r[f'{c}_pct'] = round(cp, 1) if cn >= 30 else None
    for sx in ('MALE', 'FEMALE'):
        sn, sk, sp = rate(hc[hc.sex == sx], m['key'])
        r[f'{sx}_pct'] = round(sp, 1) if sn >= 30 else None
        r[f'{sx}_n'] = int(sn)
    for pk in ('CORPORATE', 'RETAIL'):
        pn, pkk, pp = rate(hc[hc.package == pk], m['key'])
        r[f'{pk}_pct'] = round(pp, 1) if pn >= 30 else None
    rows.append(r)
res = pd.DataFrame(rows).sort_values('pct', ascending=False)
res.to_csv(f'{SCRATCH}/flag_summary.csv', index=False)

# ---------- burden: how many red flags per person ----------
CORE = [  # one flag per system, no double-counting of severity tiers
    'Vitamin D below sufficiency (<30 ng/mL)', 'B12 low or borderline (<300 pg/mL)',
    'Prediabetic HbA1c (5.7-6.4%)', 'Diabetic range HbA1c (>=6.5%)',
    'Triglycerides high (>=150 mg/dL)', 'LDL high (>=130 mg/dL)', 'HDL low (<40 M / <50 F)',
    'TSH high - hypothyroid pattern (>4.5)', 'Anaemia (Hb <13 M / <12 F)',
    'ALT elevated (>40 M / >33 F)', 'hsCRP high CV risk (>3 mg/L)',
    'Hyperuricemia (>7.0 M / >6.0 F)', 'Homocysteine elevated (>15 umol/L)',
]
core_keys = [f'FLAG::{c}' for c in CORE if f'FLAG::{c}' in hc.columns]
sub = hc[core_keys]
tested_ct = sub.notna().sum(axis=1)
flag_ct = (sub == 1).sum(axis=1)
elig = tested_ct >= 8
hc['n_flags'] = flag_ct
out['burden'] = dict(
    n_evaluated=int(elig.sum()),
    mean_flags=round(float(flag_ct[elig].mean()), 2),
    dist={str(i): int((flag_ct[elig] == i).sum()) for i in range(0, 11)},
    pct_zero=round(100 * float((flag_ct[elig] == 0).mean()), 1),
    pct_3plus=round(100 * float((flag_ct[elig] >= 3).mean()), 1),
    pct_5plus=round(100 * float((flag_ct[elig] >= 5).mean()), 1),
)
bc = []
for c in COHORT_NAMES:
    m = elig & (hc.cohort == c)
    if m.sum() >= 100:
        bc.append(dict(cohort=c, n=int(m.sum()), mean=round(float(flag_ct[m].mean()), 2),
                       pct_3plus=round(100 * float((flag_ct[m] >= 3).mean()), 1),
                       pct_5plus=round(100 * float((flag_ct[m] >= 5).mean()), 1),
                       pct_zero=round(100 * float((flag_ct[m] == 0).mean()), 1)))
out['burden_by_cohort'] = bc

# ---------- co-occurrence: which pairs travel together ----------
pairs = []
for i in range(len(core_keys)):
    for j in range(i + 1, len(core_keys)):
        a, b = core_keys[i], core_keys[j]
        m = hc[a].notna() & hc[b].notna()
        if m.sum() < 500: continue
        A, B = hc.loc[m, a] == 1, hc.loc[m, b] == 1
        pa, pb = A.mean(), B.mean()
        both = (A & B).mean()
        if pa * pb == 0: continue
        lift = both / (pa * pb)
        cond = (B[A].mean() * 100) if A.sum() else np.nan
        pairs.append(dict(a=a.replace('FLAG::', ''), b=b.replace('FLAG::', ''), n=int(m.sum()),
                          both_pct=round(100 * both, 1), lift=round(lift, 2),
                          p_b_given_a=round(cond, 1), base_b=round(100 * pb, 1)))
pd.DataFrame(pairs).sort_values('lift', ascending=False).to_csv(f'{SCRATCH}/pairs.csv', index=False)

json.dump(out, open(f'{SCRATCH}/summary.json', 'w'), indent=1)
hc[['member_id', 'cohort', 'sex', 'package', 'n_flags'] + flag_cols].to_pickle(f'{SCRATCH}/flagged.pkl')

print(json.dumps({k: out[k] for k in ('coverage', 'cohort_sizes', 'age_stats', 'burden', 'burden_by_cohort')}, indent=1))
print('\n=== TOP 30 FLAGS (all-cohort prevalence) ===')
pd.set_option('display.width', 250)
print(res[['label', 'family', 'severity', 'tested', 'pct'] + [f'{c}_pct' for c in COHORT_NAMES] +
          ['MALE_pct', 'FEMALE_pct']].head(35).to_string(index=False))
