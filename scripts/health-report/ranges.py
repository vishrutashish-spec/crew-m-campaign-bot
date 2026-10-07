"""
Clinical reference ranges for the Plum health-checkup biomarker analysis.

DATA ACCESSED: data/hc_data.xlsx (36,526 health-checkup bookings, de-identified
member/org tokens only) joined to data/th_consultation_data.xlsx for member age.
WHY: aggregate population-health analysis - which biomarkers are out of range,
in which age cohort. Output is counts and percentages only.
PROTECTION: no row-level output, no export endpoint, no member identifiers in
any report artefact. Analysis is bounded to a <=1-year window.

Each entry: (flag_fn, label, family, severity)
Sex-specific cutoffs take the member's patient_gender.
Ranges follow conventional Indian diagnostic-lab reference intervals and
ADA / WHO / NCEP-ATP-III / Endocrine Society guidance; source noted per marker.
"""

# --- plausibility caps: values outside these are lab/entry errors, dropped ---
PLAUSIBLE = {
    'Glycosylated Haemoglobin': (3.0, 20.0),
    'Glucose Fasting': (30, 700),
    'Cholesterol Total': (50, 600),
    'Cholesterol LDL - Direct': (10, 500),
    'Cholesterol HDL': (5, 200),
    'Triglycerides': (20, 3000),
    'Thyroid Stimulating Hormone': (0.005, 150),
    'Haemoglobin': (3, 25),
    'Uric Acid': (0.5, 25),
    'Alanine Aminotransferase (SGPT)': (2, 2000),
    'Aspartate Aminotransferase (SGOT)': (2, 2000),
    'Creatinine': (0.2, 15),
    'Creatinine Estimated Glomerular Filtration Rate': (2, 200),
    'C Reactive Protein High Sensitivity': (0.01, 300),
    'Vitamin D 25-OH': (1, 200),
    'Vitamin B12': (20, 3000),
    'Homocysteine': (1, 200),
    'Platelet Count': (5, 1200),
    'Total Leucocytes Count': (0.5, 100),
    'Mean Corpuscular Volume': (40, 150),
    'Absolute Eosinophil Count': (0, 10000),
    'Erythrocyte Sedimentation Rate': (0, 200),
    'Gamma Glutamyl Transpeptidase': (1, 2000),
    'Vitamin B9': (0.1, 30),
    'Total Cholesterol/ HDL CHOLESTEROL RATIO': (0.5, 30),
    'NON-HDL CHOLESTEROL': (10, 500),
    'Urea': (2, 300),
    'Bilirubin Total': (0.05, 30),
    'Alkaline Phosphatase': (10, 1000),
    'Calcium': (4, 16),
    'Iron': (5, 500),
}

# Columns that are the same assay reported under two names - coalesce in order.
ALIASES = {
    'Glycosylated Haemoglobin': ['Glycosylated Haemoglobin', 'Glycosylated Haemoglobin (HbA1c)'],
    'Alanine Aminotransferase (SGPT)': ['Alanine Aminotransferase (SGPT)', 'Alanine Aminotransferase'],
    'Aspartate Aminotransferase (SGOT)': ['Aspartate Aminotransferase (SGOT)', 'Aspartate Aminotransferase'],
    'Mean Corpuscular Haemoglobin (MCH)': ['Mean Corpuscular Haemoglobin (MCH)', 'MCH'],
    'Mean Corpuscular Haemoglobin Concentration (MCHC)': [
        'Mean Corpuscular Haemoglobin Concentration (MCHC)',
        'Mean Corpuscular Haemoglobin Concentration'],
    'Red Cell Distribution Width': ['Red Cell Distribution Width', 'RED CELL DISTRIBUTION WIDTH (RDW-CV)'],
}

# --- flag definitions -------------------------------------------------------
# lo/hi = abnormal below / above. None = not flagged on that side.
# sex form: {'MALE': v, 'FEMALE': v}
FLAGS = [
    # marker column, label, family, lo, hi, severity, source
    ('Vitamin D 25-OH', 'Vitamin D deficient (<20 ng/mL)', 'Micronutrient', 20, None, 'high',
     'Endocrine Society: deficiency <20, insufficiency 20-29 ng/mL'),
    ('Vitamin D 25-OH', 'Vitamin D below sufficiency (<30 ng/mL)', 'Micronutrient', 30, None, 'moderate',
     'Endocrine Society'),
    ('Vitamin D 25-OH', 'Vitamin D severely deficient (<10 ng/mL)', 'Micronutrient', 10, None, 'critical',
     'Endocrine Society - severe deficiency, rickets/osteomalacia risk'),

    ('Vitamin B12', 'B12 deficient (<200 pg/mL)', 'Micronutrient', 200, None, 'high',
     'Conventional lab cutoff; WHO deficiency <203 pg/mL'),
    ('Vitamin B12', 'B12 low or borderline (<300 pg/mL)', 'Micronutrient', 300, None, 'moderate',
     'Borderline 200-300 pg/mL - functional deficiency common in this band'),

    ('Vitamin B9', 'Folate low (<3 ng/mL)', 'Micronutrient', 3, None, 'high', 'Lab reference 3-17 ng/mL'),
    ('Homocysteine', 'Homocysteine elevated (>15 umol/L)', 'Cardiometabolic', None, 15, 'high',
     'AHA: >15 umol/L hyperhomocysteinemia, independent CV risk'),

    ('Glycosylated Haemoglobin', 'Diabetic range HbA1c (>=6.5%)', 'Cardiometabolic', None, 6.499, 'critical',
     'ADA 2024 diagnostic threshold'),
    ('Glycosylated Haemoglobin', 'Prediabetic HbA1c (5.7-6.4%)', 'Cardiometabolic', None, None, 'high',
     'ADA 2024 prediabetes band', 'band', 5.7, 6.499),
    ('Glucose Fasting', 'Fasting glucose impaired (>=100 mg/dL)', 'Cardiometabolic', None, 99.9, 'high',
     'ADA: IFG 100-125, diabetes >=126 mg/dL'),
    ('Glucose Fasting', 'Fasting glucose diabetic (>=126 mg/dL)', 'Cardiometabolic', None, 125.9, 'critical',
     'ADA diagnostic threshold'),

    ('Triglycerides', 'Triglycerides high (>=150 mg/dL)', 'Lipid', None, 149.9, 'high',
     'NCEP ATP III: borderline 150-199, high 200-499'),
    ('Triglycerides', 'Triglycerides very high (>=200 mg/dL)', 'Lipid', None, 199.9, 'critical',
     'NCEP ATP III'),
    ('Cholesterol Total', 'Total cholesterol >=200 mg/dL', 'Lipid', None, 199.9, 'moderate', 'NCEP ATP III'),
    ('Cholesterol LDL - Direct', 'LDL above optimal (>=100 mg/dL)', 'Lipid', None, 99.9, 'moderate',
     'NCEP ATP III optimal <100'),
    ('Cholesterol LDL - Direct', 'LDL high (>=130 mg/dL)', 'Lipid', None, 129.9, 'high', 'NCEP ATP III'),
    ('Cholesterol HDL', 'HDL low (<40 M / <50 F)', 'Lipid', {'MALE': 40, 'FEMALE': 50}, None, 'high',
     'NCEP ATP III sex-specific low-HDL threshold'),
    ('NON-HDL CHOLESTEROL', 'Non-HDL cholesterol >=130 mg/dL', 'Lipid', None, 129.9, 'high',
     'ATP IV / Lipid Association of India target'),
    ('Total Cholesterol/ HDL CHOLESTEROL RATIO', 'TC:HDL ratio >4.5', 'Lipid', None, 4.5, 'high',
     'Framingham atherogenic index'),

    ('Uric Acid', 'Hyperuricemia (>7.0 M / >6.0 F)', 'Cardiometabolic', None, {'MALE': 7.0, 'FEMALE': 6.0},
     'high', 'ACR gout guideline / lab reference'),
    ('C Reactive Protein High Sensitivity', 'hsCRP high CV risk (>3 mg/L)', 'Inflammation', None, 3.0, 'high',
     'AHA/CDC: low <1, average 1-3, high >3 mg/L'),
    ('Erythrocyte Sedimentation Rate', 'ESR elevated (>15 M / >20 F)', 'Inflammation', None,
     {'MALE': 15, 'FEMALE': 20}, 'moderate', 'Age/sex adjusted Westergren reference'),

    ('Thyroid Stimulating Hormone', 'TSH high - hypothyroid pattern (>4.5)', 'Thyroid', None, 4.5, 'high',
     'ATA: subclinical hypothyroid 4.5-10, overt >10 uIU/mL'),
    ('Thyroid Stimulating Hormone', 'TSH overt hypothyroid (>10)', 'Thyroid', None, 10.0, 'critical', 'ATA'),
    ('Thyroid Stimulating Hormone', 'TSH low - hyperthyroid pattern (<0.45)', 'Thyroid', 0.45, None, 'high',
     'ATA lower reference limit'),

    ('Haemoglobin', 'Anaemia (Hb <13 M / <12 F)', 'Haematology', {'MALE': 13.0, 'FEMALE': 12.0}, None,
     'high', 'WHO anaemia definition, non-pregnant adults'),
    ('Haemoglobin', 'Moderate-severe anaemia (Hb <11)', 'Haematology', 11.0, None, 'critical', 'WHO'),
    ('Mean Corpuscular Volume', 'Microcytosis (MCV <80 fL)', 'Haematology', 80, None, 'moderate',
     'Iron deficiency / thalassaemia trait marker'),
    ('Absolute Eosinophil Count', 'Eosinophilia (AEC >500/uL)', 'Haematology', None, 500, 'moderate',
     'Allergy / atopy / parasitic load marker'),
    ('Platelet Count', 'Thrombocytopenia (<150 k/uL)', 'Haematology', 150, None, 'moderate', 'Lab reference'),
    ('Total Leucocytes Count', 'Leucocytosis (TLC >10 k/uL)', 'Haematology', None, 10.0, 'moderate',
     'Lab reference 4-10 x10^3/uL'),

    ('Alanine Aminotransferase (SGPT)', 'ALT elevated (>40 M / >33 F)', 'Liver', None,
     {'MALE': 40, 'FEMALE': 33}, 'high', 'AASLD 2017 upper limits of normal'),
    ('Alanine Aminotransferase (SGPT)', 'ALT >2x upper limit', 'Liver', None,
     {'MALE': 80, 'FEMALE': 66}, 'critical', 'AASLD - warrants hepatology workup'),
    ('Aspartate Aminotransferase (SGOT)', 'AST elevated (>40)', 'Liver', None, 40, 'moderate', 'Lab reference'),
    ('Gamma Glutamyl Transpeptidase', 'GGT elevated (>55 M / >38 F)', 'Liver', None,
     {'MALE': 55, 'FEMALE': 38}, 'moderate', 'Lab reference; alcohol / fatty-liver marker'),
    ('Bilirubin Total', 'Bilirubin total >1.2 mg/dL', 'Liver', None, 1.2, 'moderate', 'Lab reference'),

    ('Creatinine Estimated Glomerular Filtration Rate', 'eGFR <90 (mildly reduced)', 'Renal', 90, None,
     'moderate', 'KDIGO G2'),
    ('Creatinine Estimated Glomerular Filtration Rate', 'eGFR <60 (CKD stage 3+)', 'Renal', 60, None,
     'critical', 'KDIGO G3a'),
    ('Creatinine', 'Creatinine high (>1.3 M / >1.1 F)', 'Renal', None, {'MALE': 1.3, 'FEMALE': 1.1},
     'high', 'Lab reference'),
]

FAMILY_ORDER = ['Micronutrient', 'Cardiometabolic', 'Lipid', 'Thyroid', 'Liver',
                'Haematology', 'Inflammation', 'Renal']
