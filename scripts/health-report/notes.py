"""
Clinical-theme classification of telehealth doctor notes.

DATA ACCESSED: data/th_consultation_data.xlsx doctor_notes (106,284 free-text
notes across 132,235 consults). Notes contain no member names; they are written
by the Plum panel doctor about the consult.
WHY: quantify which health issues drive telehealth demand, by age cohort, to sit
alongside the lab-biomarker view.
PROTECTION: regex counts only. No note text, no member id and no doctor id
appears in any output. Free-text notes are never printed verbatim into a report.
WINDOW: 2025-08-01 .. 2026-07-31 (12 months).
"""
import re, sys, json
import pandas as pd, numpy as np

SCRATCH = '/private/tmp/claude-502/-Users-vishrut-insurwreck/c53c0c8e-b2fd-4e11-b930-2348a6360bb5/scratchpad'
COHORTS = [('Under 20', 0, 20), ('21-25', 21, 25), ('26-35', 26, 35),
           ('36-40', 36, 40), ('41-50', 41, 50), ('51+', 51, 120)]

# Patterns are deliberately narrow: a term only counts when it appears in a
# clinical rather than a dietary-advice sense. e.g. plain "sugar" is excluded
# because it dominates diet counselling text; "blood sugar" / "hba1c" are kept.
THEMES = {
    'Vitamin D deficiency': r'vit(?:amin)?\.?\s*-?\s*d\b|vit d3|cholecalciferol|\bd3\b',
    'B12 deficiency': r'vit(?:amin)?\.?\s*-?\s*b\s*-?12|b12|cyanocobalamin|methylcobalamin',
    'Iron deficiency / anaemia': r'\banaemi|\banemi|iron deficien|ferritin|\bhb\b\s*(?:is|of|:)?\s*\d|low h(?:a)?emoglobin|ferrous',
    'Thyroid disorder': r'thyroid|hypothyroid|hyperthyroid|\btsh\b|levothyrox|thyronorm|eltroxin|\bt3\b.*\bt4\b',
    'Diabetes / blood sugar': r'diabet|hba1c|blood sugar|\bfbs\b|\bppbs\b|glycemi|glycaemi|metformin|prediabet|pre-diabet|insulin resist',
    'Hypertension / BP': r'hypertens|high\s*b\.?p\b|blood pressure|\bbp\b\s*(?:is|of|:|\d)|amlodipine|telmisartan',
    'Dyslipidemia / cholesterol': r'cholesterol|dyslipid|lipid profile|triglycerid|\bldl\b|statin|atorvastatin|rosuvastatin',
    'PCOS / menstrual': r'\bpcos\b|\bpcod\b|polycystic|irregular (?:period|menses|cycle)|menstrua|amenorrh|dysmenorrh|heavy bleed',
    'Pregnancy / fertility': r'pregnan|antenatal|conceiv|fertilit|\bivf\b|ovulat|trying to conceive|\bttc\b|lactat|breastfeed',
    'Mental health - anxiety': r'anxiet|anxious|panic attack|\bgad\b|overthink',
    'Mental health - depression': r'depress|low mood|suicidal|\bmdd\b|anhedonia',
    'Mental health - stress/burnout': r'\bstress\b|burnout|burn out|work pressure|overwhelm',
    'Sleep disorder': r'insomni|sleep (?:issue|problem|disturb|hygiene|deprivation)|poor sleep|unable to sleep|disturbed sleep',
    'Obesity / weight': r'obes|overweight|weight (?:loss|gain|management|reduction)|\bbmi\b|belly fat|central obesity',
    'Fatty liver / liver enzymes': r'fatty liver|\bnafld\b|hepatic steatos|\bsgpt\b|\bsgot\b|\balt\b\s*(?:is|of|:|\d)|deranged (?:lft|liver)|\blft\b',
    'Acne': r'\bacne\b|pimple|comedone|isotretinoin|adapalene|benzoyl',
    'Hair loss': r'hair (?:fall|loss|thinning)|alopecia|telogen|androgenetic|minoxidil',
    'Fungal / skin infection': r'fungal|tinea|ringworm|candid|dermatophyt|itraconazol|terbinafin|scabies',
    'Eczema / dermatitis': r'eczema|dermatitis|psorias|urticaria|\bhives\b|atopic',
    'Acid reflux / gastritis': r'gastritis|acidity|\bgerd\b|reflux|heartburn|pantoprazol|omeprazol|rabeprazol|\bapd\b',
    'IBS / bowel': r'\bibs\b|irritable bowel|constipat|diarrh|loose (?:motion|stool)|bloating|flatulen',
    'Respiratory infection / cough': r'\bcough\b|cold|sore throat|pharyngitis|tonsillitis|\buri\b|upper respiratory|rhinitis|sinusitis',
    'Asthma / allergy': r'asthma|allerg|wheez|bronchospasm|montelukast|levocetirizine|cetirizine',
    'Musculoskeletal pain': r'back pain|neck pain|knee pain|joint pain|arthralgia|arthritis|cervical spondyl|lumbar|sciatica|myalgia',
    'Headache / migraine': r'migraine|headache|cephalgia',
    'Vitamin/mineral other': r'\bcalcium\b|magnesium|folate|folic acid|\bzinc\b',
    'Dengue / vector fever': r'dengue|malaria|typhoid|chikungunya|widal',
    'Urinary tract infection': r'\buti\b|urinary tract infect|dysuria|burning micturition|cystitis',
    'Sexual health': r'erectile|premature ejacul|libido|\bstd\b|\bsti\b|sexual (?:health|dysfunction)',
    'Contraception': r'contracept|\bipill\b|i-pill|emergency pill|\bocp\b|condom',
    'Eye strain / vision': r'eye strain|dry eye|refractive|myopia|spectacle|blurred vision|conjunctivitis',
}

th = pd.read_pickle(f'{SCRATCH}/th.pkl')
th = th[(th.appointment_created_at >= '2025-08-01') & (th.appointment_created_at <= '2026-07-31')]
th = th[(th.patient_age >= 0) & (th.patient_age <= 100)]

def cohort_of(a):
    for nm, lo, hi in COHORTS:
        if lo <= a <= hi: return nm
    return None
th['cohort'] = th.patient_age.apply(cohort_of)
notes = th.doctor_notes.fillna('').astype(str).str.lower()
has = notes.str.len() > 3
adult = th.patient_age >= 18

rows = []
for name, pat in THEMES.items():
    hit = notes.str.contains(pat, regex=True, na=False) & has
    th[f'T::{name}'] = hit
    base = has.sum()
    r = dict(theme=name, consults=int(hit.sum()), pct_of_noted=round(100 * hit.sum() / base, 2),
             members=int(th.loc[hit, 'unique_member_id'].nunique()))
    for nm, lo, hi in COHORTS:
        m = has & (th.cohort == nm)
        r[f'{nm}_pct'] = round(100 * (hit & m).sum() / m.sum(), 2) if m.sum() >= 200 else None
    for sx in ('MALE', 'FEMALE'):
        m = has & (th.patient_gender == sx) & adult
        r[f'{sx}_pct'] = round(100 * (hit & m).sum() / m.sum(), 2) if m.sum() >= 200 else None
    top = th.loc[hit, 'specialist_specialty'].value_counts().head(2)
    r['top_specialties'] = '; '.join(f'{k} {100*v/max(hit.sum(),1):.0f}%' for k, v in top.items())
    rows.append(r)

res = pd.DataFrame(rows).sort_values('pct_of_noted', ascending=False)
res.to_csv(f'{SCRATCH}/theme_summary.csv', index=False)

meta = dict(consults=int(len(th)), with_notes=int(has.sum()), members=int(th.unique_member_id.nunique()),
            paediatric_share=round(100 * float((th.patient_age < 18).mean()), 1),
            female_share_adult=round(100 * float((th.loc[adult, 'patient_gender'] == 'FEMALE').mean()), 1),
            cohort_consults={nm: int((th.cohort == nm).sum()) for nm, _, _ in COHORTS},
            repeat_rate=round(100 * float((th.groupby('unique_member_id').size() > 1).mean()), 1),
            mean_consults_per_member=round(float(len(th) / th.unique_member_id.nunique()), 2))
json.dump(meta, open(f'{SCRATCH}/theme_meta.json', 'w'), indent=1)
th[['unique_member_id', 'cohort', 'patient_gender', 'patient_age', 'specialist_specialty'] +
   [f'T::{k}' for k in THEMES]].to_pickle(f'{SCRATCH}/themed.pkl')

pd.set_option('display.width', 260)
print(json.dumps(meta, indent=1))
print(res.to_string(index=False))
