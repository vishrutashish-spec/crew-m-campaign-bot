"""
Composite phenotypes, seasonality, segment splits and confidence intervals.

DATA ACCESSED: data/hc_data.xlsx (labs) + age join from analyse.py, de-identified.
WHY: turn single-marker prevalence into decision-ready patterns - metabolic
clustering, the seasonal vitamin-D swing, corporate vs retail differences, and
error bars on the headline claims so nothing is over-read.
PROTECTION: aggregate output only. Cohort/segment cells with n<150 are suppressed.
WINDOW: 2025-08-01 .. 2026-07-31 (12 months).
"""
import json, math
import pandas as pd, numpy as np

SCRATCH = '/private/tmp/claude-502/-Users-vishrut-insurwreck/c53c0c8e-b2fd-4e11-b930-2348a6360bb5/scratchpad'
W0, W1 = pd.Timestamp('2025-08-01'), pd.Timestamp('2026-07-31')
COHORTS = ['21-25', '26-35', '36-40', '41-50', '51+']
pd.set_option('display.width', 250)

hc = pd.read_pickle(f'{SCRATCH}/hc.pkl')
th = pd.read_pickle(f'{SCRATCH}/th.pkl')
tha = th[(th.patient_age >= 18) & (th.patient_age <= 95)]
tha = tha[~tha.specialist_specialty.isin(['Pediatrician', 'Veterinary Medicine'])]
def modal(s):
    b = s // 2 * 2
    return s[b == b.value_counts().idxmax()].median()
ag = tha.groupby(['unique_member_id', 'patient_gender']).patient_age.agg(modal).rename('age').reset_index()
ag.columns = ['member_id', 'patient_gender', 'age']

hc = hc[(hc.appointment_date >= W0) & (hc.appointment_date <= W1)].copy()
num = lambda c: pd.to_numeric(hc[c], errors='coerce')
hc['hba1c'] = num('Glycosylated Haemoglobin').fillna(num('Glycosylated Haemoglobin (HbA1c)'))
for c in ['Vitamin D 25-OH','Vitamin B12','Glucose Fasting','Triglycerides','Cholesterol HDL',
          'Cholesterol LDL - Direct','Thyroid Stimulating Hormone','Haemoglobin','Uric Acid',
          'C Reactive Protein High Sensitivity','Alanine Aminotransferase (SGPT)','Homocysteine']:
    hc[c] = num(c)
hc.loc[~hc['Thyroid Stimulating Hormone'].between(0.005, 150), 'Thyroid Stimulating Hormone'] = np.nan
hc.loc[~hc['Vitamin D 25-OH'].between(1, 200), 'Vitamin D 25-OH'] = np.nan
hc.loc[~hc['Triglycerides'].between(20, 3000), 'Triglycerides'] = np.nan
hc.loc[~hc['Alanine Aminotransferase (SGPT)'].between(2, 2000), 'Alanine Aminotransferase (SGPT)'] = np.nan
hc = hc.sort_values('appointment_date').drop_duplicates(['member_id','patient_relationship'], keep='last')
hc = hc.merge(ag, on=['member_id','patient_gender'], how='left')
hc.loc[hc.patient_relationship != 'SELF', 'age'] = np.nan
def coh(a):
    if pd.isna(a): return None
    for nm, lo, hi in [('21-25',21,25),('26-35',26,35),('36-40',36,40),('41-50',41,50),('51+',51,120)]:
        if lo <= a <= hi: return nm
hc['cohort'] = hc.age.apply(coh)

# ---------- 1. central tendency: where does the MEDIAN employee sit? ----------
print('=== median value vs clinical target ===')
targets = {'Vitamin D 25-OH': ('>=30 ng/mL', 30), 'Vitamin B12': ('>=300 pg/mL', 300),
           'Homocysteine': ('<15 umol/L', 15), 'C Reactive Protein High Sensitivity': ('<1 mg/L', 1),
           'Cholesterol LDL - Direct': ('<100 mg/dL', 100), 'Cholesterol HDL': ('>=40/50 mg/dL', 40),
           'Triglycerides': ('<150 mg/dL', 150), 'hba1c': ('<5.7 %', 5.7),
           'Glucose Fasting': ('<100 mg/dL', 100), 'Thyroid Stimulating Hormone': ('0.45-4.5 uIU/mL', 4.5)}
for c, (t, _) in targets.items():
    s = hc[c].dropna()
    print(f'  {c[:38]:40s} n={len(s):6d}  p25={s.quantile(.25):7.1f}  median={s.median():7.1f}  p75={s.quantile(.75):7.1f}   target {t}')

# ---------- 2. metabolic clustering (ATP-III proxy, 3 of 5 criteria available) ----------
crit = pd.DataFrame({
    'tg':  hc['Triglycerides'] >= 150,
    'hdl': hc['Cholesterol HDL'] < hc.patient_gender.map({'MALE': 40, 'FEMALE': 50}),
    'glu': (hc['Glucose Fasting'] >= 100) | (hc['hba1c'] >= 5.7),
})
avail = pd.DataFrame({k: hc[v].notna() for k, v in
                      [('tg','Triglycerides'),('hdl','Cholesterol HDL'),('glu','Glucose Fasting')]})
ok = avail.all(axis=1)
cnt = crit[ok].sum(axis=1)
print(f'\n=== metabolic risk clustering (ATP-III proxy: TG>=150, low HDL, dysglycaemia) ===')
print(f'  evaluable n={ok.sum()}  0 criteria={100*(cnt==0).mean():.1f}%  1={100*(cnt==1).mean():.1f}%'
      f'  2={100*(cnt==2).mean():.1f}%  3={100*(cnt==3).mean():.1f}%   >=2 = {100*(cnt>=2).mean():.1f}%')
hc['met_n'] = np.nan; hc.loc[ok, 'met_n'] = cnt
for c in COHORTS:
    m = ok & (hc.cohort == c)
    if m.sum() >= 150:
        print(f'    {c:8s} n={m.sum():5d}  >=2 criteria = {100*(crit[m].sum(axis=1)>=2).mean():.1f}%')

# ---------- 3. seasonality of vitamin D ----------
print('\n=== vitamin D by month of test (seasonal swing) ===')
vd = hc[hc['Vitamin D 25-OH'].notna()].copy()
vd['m'] = vd.appointment_date.dt.strftime('%Y-%m')
g = vd.groupby('m')['Vitamin D 25-OH'].agg(n='size', median='median')
g['deficient_%'] = vd.assign(d=vd['Vitamin D 25-OH'] < 20).groupby('m').d.mean() * 100
print(g[g.n >= 150].round(1).to_string())

# ---------- 4. corporate vs retail ----------
print('\n=== corporate vs retail (self-selection signal) ===')
rows = []
for lab, col, fn in [('Vit D <20', 'Vitamin D 25-OH', lambda s: s < 20),
                     ('B12 <200', 'Vitamin B12', lambda s: s < 200),
                     ('HbA1c >=6.5', 'hba1c', lambda s: s >= 6.5),
                     ('TG >=150', 'Triglycerides', lambda s: s >= 150),
                     ('LDL >=130', 'Cholesterol LDL - Direct', lambda s: s >= 130),
                     ('TSH >4.5', 'Thyroid Stimulating Hormone', lambda s: s > 4.5),
                     ('hsCRP >3', 'C Reactive Protein High Sensitivity', lambda s: s > 3)]:
    r = {'flag': lab}
    for pk in ['CORPORATE', 'RETAIL']:
        s = hc.loc[hc.package == pk, col].dropna()
        r[pk] = round(100 * fn(s).mean(), 1) if len(s) >= 150 else None
        r[f'{pk}_n'] = len(s)
    rows.append(r)
print(pd.DataFrame(rows).to_string(index=False))

# ---------- 5. Wilson CI on headline claims ----------
def wilson(k, n, z=1.96):
    if n == 0: return (None, None)
    p = k / n; d = 1 + z*z/n
    c = (p + z*z/(2*n)) / d
    h = z*math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / d
    return (round(100*(c-h), 1), round(100*(c+h), 1))
print('\n=== 95% CI on headline prevalences ===')
for lab, col, fn in [('Vit D <30', 'Vitamin D 25-OH', lambda s: s < 30),
                     ('Vit D <20', 'Vitamin D 25-OH', lambda s: s < 20),
                     ('B12 <300', 'Vitamin B12', lambda s: s < 300),
                     ('HbA1c >=5.7', 'hba1c', lambda s: s >= 5.7),
                     ('TG >=150', 'Triglycerides', lambda s: s >= 150),
                     ('TSH >4.5', 'Thyroid Stimulating Hormone', lambda s: s > 4.5),
                     ('Anaemia F (Hb<12)', 'Haemoglobin', None)]:
    if lab.startswith('Anaemia'):
        s = hc.loc[hc.patient_gender == 'FEMALE', 'Haemoglobin'].dropna(); k = int((s < 12).sum())
    else:
        s = hc[col].dropna(); k = int(fn(s).sum())
    lo, hi = wilson(k, len(s))
    print(f'  {lab:20s} {100*k/len(s):5.1f}%  n={len(s):6d}  95% CI [{lo}, {hi}]')

# ---------- 6. representativeness of the age-joined subset ----------
print('\n=== is the age-joined subset representative of the full lab population? ===')
sub = hc.cohort.notna()
for lab, col, fn in [('Vit D <20','Vitamin D 25-OH',lambda s: s<20), ('B12 <200','Vitamin B12',lambda s: s<200),
                     ('HbA1c >=6.5','hba1c',lambda s: s>=6.5), ('TG >=150','Triglycerides',lambda s: s>=150),
                     ('TSH >4.5','Thyroid Stimulating Hormone',lambda s: s>4.5)]:
    a = hc.loc[sub, col].dropna(); b = hc.loc[~sub, col].dropna()
    print(f'  {lab:14s} age-joined {100*fn(a).mean():5.1f}% (n={len(a)})   rest {100*fn(b).mean():5.1f}% (n={len(b)})')
