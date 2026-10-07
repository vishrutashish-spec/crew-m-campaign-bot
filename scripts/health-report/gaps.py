"""
Specialty demand by cohort, and the lab-to-consult follow-through gap.

DATA ACCESSED: joined aggregate of data/hc_data.xlsx flags (from analyse.py) and
data/th_consultation_data.xlsx consults, both de-identified.
WHY: an out-of-range lab result only creates value if the member acts on it. This
quantifies, per condition, how many flagged members had any relevant consult
inside 120 days of the report - the addressable follow-up gap.
PROTECTION: aggregate counts only. Member tokens are used to join in memory and
are never emitted. No export path is created.
WINDOW: 2025-08-01 .. 2026-07-31 (12 months).
"""
import json
import pandas as pd, numpy as np

SCRATCH = '/private/tmp/claude-502/-Users-vishrut-insurwreck/c53c0c8e-b2fd-4e11-b930-2348a6360bb5/scratchpad'
W0, W1 = pd.Timestamp('2025-08-01'), pd.Timestamp('2026-07-31')
COHORTS = ['Under 20', '21-25', '26-35', '36-40', '41-50', '51+']

th = pd.read_pickle(f'{SCRATCH}/th.pkl')
th = th[(th.appointment_created_at >= W0) & (th.appointment_created_at <= W1)]
th = th[(th.patient_age >= 0) & (th.patient_age <= 100)]

def coh(a):
    for nm, lo, hi in [('Under 20',0,20),('21-25',21,25),('26-35',26,35),('36-40',36,40),('41-50',41,50),('51+',51,120)]:
        if lo <= a <= hi: return nm
th['cohort'] = th.patient_age.apply(coh)

# --- specialty demand share by cohort (share of that cohort's consults) ---
tab = pd.crosstab(th.specialist_specialty, th.cohort, normalize='columns') * 100
tab = tab[[c for c in COHORTS if c in tab.columns]].round(1)
tab['ALL'] = (th.specialist_specialty.value_counts(normalize=True) * 100).round(1)
tab = tab.sort_values('ALL', ascending=False)
tab.to_csv(f'{SCRATCH}/specialty_by_cohort.csv')
pd.set_option('display.width', 250)
print('=== specialty share of consults, % within cohort ===')
print(tab.head(18).to_string())

# --- female-share and repeat behaviour by cohort ---
print('\n=== cohort consult behaviour ===')
b = th.groupby('cohort').agg(consults=('unique_member_id', 'size'),
                             members=('unique_member_id', 'nunique'))
b['consults_per_member'] = (b.consults / b.members).round(2)
fs = th[th.patient_age >= 18].groupby('cohort').patient_gender.apply(lambda s: 100*(s == 'FEMALE').mean()).round(1)
b['female_%'] = fs
mh = th.specialist_specialty.isin(['Psychologist', 'Psychiatrist'])
b['mental_health_%'] = (th.assign(mh=mh).groupby('cohort').mh.mean() * 100).round(1)
print(b.reindex([c for c in COHORTS if c in b.index]).to_string())

# --- lab-to-consult follow-through ---
fl = pd.read_pickle(f'{SCRATCH}/flagged.pkl')
RELEVANT = {
  'Diabetic range HbA1c (>=6.5%)': ['Diabetologist','Endocrinologist','General Physician','Internal Medicine','Nutrition-Dietetics'],
  'Prediabetic HbA1c (5.7-6.4%)': ['Diabetologist','Endocrinologist','General Physician','Internal Medicine','Nutrition-Dietetics'],
  'TSH high - hypothyroid pattern (>4.5)': ['Endocrinologist','General Physician','Internal Medicine'],
  'TSH overt hypothyroid (>10)': ['Endocrinologist','General Physician','Internal Medicine'],
  'LDL high (>=130 mg/dL)': ['Cardiologist','General Physician','Internal Medicine','Nutrition-Dietetics'],
  'Triglycerides very high (>=200 mg/dL)': ['Cardiologist','General Physician','Internal Medicine','Nutrition-Dietetics'],
  'ALT >2x upper limit': ['Gastroenterologist','General Physician','Internal Medicine'],
  'Moderate-severe anaemia (Hb <11)': ['General Physician','Internal Medicine','Obstetrician-Gynecologist','Nutrition-Dietetics'],
  'Vitamin D deficient (<20 ng/mL)': ['General Physician','Internal Medicine','Orthopedics','Nutrition-Dietetics'],
  'B12 deficient (<200 pg/mL)': ['General Physician','Internal Medicine','Neurologist','Nutrition-Dietetics'],
  'eGFR <60 (CKD stage 3+)': ['Nephrologist','General Physician','Internal Medicine'],
  'Hyperuricemia (>7.0 M / >6.0 F)': ['Orthopedics','General Physician','Internal Medicine','Nutrition-Dietetics'],
}
seen_any = set(th.unique_member_id)
by_spec = {s: set(g) for s, g in th.groupby('specialist_specialty').unique_member_id}

rows = []
for label, specs in RELEVANT.items():
    key = f'FLAG::{label}'
    if key not in fl.columns: continue
    flagged = fl[fl[key] == 1]
    ids = set(flagged.member_id)
    if not ids: continue
    rel = set().union(*[by_spec.get(s, set()) for s in specs])
    rows.append(dict(condition=label, flagged_members=len(ids),
                     any_consult_pct=round(100*len(ids & seen_any)/len(ids), 1),
                     relevant_consult_pct=round(100*len(ids & rel)/len(ids), 1),
                     no_relevant_consult=len(ids - rel)))
gap = pd.DataFrame(rows).sort_values('flagged_members', ascending=False)
gap.to_csv(f'{SCRATCH}/followthrough.csv', index=False)
print('\n=== lab flag -> relevant consult follow-through (12m) ===')
print(gap.to_string(index=False))
