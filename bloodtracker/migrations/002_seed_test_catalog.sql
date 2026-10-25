-- Catalog of known tests, grouped into categories, with each test's usual unit.
-- Seeded as a migration so every database - including a fresh install - starts
-- with the same list the add-result form offers. Units are left empty for tests
-- that have never been recorded.

INSERT INTO tests (name, category, default_unit) VALUES
    -- Blood count: red cells
    ('Erythrocytes (RBC)', 'Blood count', 'M/μl'),
    ('Hemoglobin (HGB)', 'Blood count', 'g/dl'),
    ('Hematocrit (HCT)', 'Blood count', '%'),
    ('Mean Corpuscular Volume (MCV)', 'Blood count', 'fl'),
    ('Mean Corpuscular Hemoglobin (MCH)', 'Blood count', 'pg'),
    ('Mean Corpuscular Hemoglobin Concentration (MCHC)', 'Blood count', 'g/dl'),
    ('Red Cell Distribution Width (RDW-CV)', 'Blood count', '%'),
    -- Blood count: white cells
    ('Leukocytes (WBC)', 'Blood count', 'K/μl'),
    ('Neutrophils %', 'Blood count', '%'),
    ('Neutrophils (absolute)', 'Blood count', 'K/μl'),
    ('Lymphocytes %', 'Blood count', '%'),
    ('Lymphocytes (absolute)', 'Blood count', 'K/μl'),
    ('Monocytes %', 'Blood count', '%'),
    ('Monocytes (absolute)', 'Blood count', 'K/μl'),
    ('Eosinophils %', 'Blood count', '%'),
    ('Eosinophils (absolute)', 'Blood count', 'K/μl'),
    ('Basophils %', 'Blood count', '%'),
    ('Basophils (absolute)', 'Blood count', 'K/μl'),
    ('Immature Granulocytes %', 'Blood count', '%'),
    ('Immature Granulocytes (absolute)', 'Blood count', 'K/μl'),
    ('AS-LYMP%', 'Blood count', '%'),
    ('AS-LYMP#', 'Blood count', 'cells/l'),
    ('RE-LYMP%', 'Blood count', '%'),
    ('RE-LYMP#', 'Blood count', '10^9/l'),
    -- Blood count: platelets
    ('Platelets (PLT)', 'Blood count', 'K/μl'),
    ('Mean Platelet Volume (MPV)', 'Blood count', 'fl'),
    ('Platelet Distribution Width (PDW)', 'Blood count', 'fl'),
    ('Platelet Large Cell Ratio (P-LCR)', 'Blood count', '%'),
    ('Plateletcrit (PCT)', 'Blood count', '%'),
    -- Coagulation
    ('Activated Partial Thromboplastin Time (APTT)', 'Coagulation', 'sec'),
    ('APTT Ratio', 'Coagulation', NULL),
    ('Prothrombin Time (PT)', 'Coagulation', NULL),
    ('Prothrombin Index', 'Coagulation', '%'),
    -- Iron
    ('Iron (Fe)', 'Iron', 'μg/dl'),
    ('Ferritin', 'Iron', 'ng/ml'),
    ('Total Iron-Binding Capacity (TIBC)', 'Iron', 'μg/dl'),
    ('Unsaturated Iron-Binding Capacity (UIBC)', 'Iron', 'μg/dl'),
    -- Lipids
    ('Total Cholesterol', 'Lipids', 'mg/dl'),
    ('HDL Cholesterol', 'Lipids', 'mg/dl'),
    ('Calculated LDL Cholesterol', 'Lipids', 'mg/dl'),
    ('Non-HDL Cholesterol', 'Lipids', NULL),
    ('Triglycerides', 'Lipids', 'mg/dl'),
    -- Glucose & insulin
    ('Fasting Glucose', 'Glucose & insulin', 'mg/dl'),
    ('Glucose (1-hour post-load)', 'Glucose & insulin', 'mg/dl'),
    ('Glucose (2-hour post-load)', 'Glucose & insulin', 'mg/dl'),
    ('Fasting Insulin', 'Glucose & insulin', 'μIU/ml'),
    ('Insulin (post-load, point 1)', 'Glucose & insulin', 'μIU/ml'),
    ('Insulin (post-load, point 2)', 'Glucose & insulin', 'μIU/ml'),
    -- Thyroid
    ('Thyroid-Stimulating Hormone (TSH)', 'Thyroid', 'μIU/ml'),
    ('Free Thyroxine (FT4)', 'Thyroid', 'ng/dl'),
    ('Free Triiodothyronine (FT3)', 'Thyroid', 'pg/ml'),
    ('Anti-TPO Antibodies', 'Thyroid', 'IU/ml'),
    ('Anti-TG Antibodies', 'Thyroid', 'IU/ml'),
    -- Hormones
    ('Luteinizing Hormone (LH)', 'Hormones', 'mIU/ml'),
    ('Follicle Stimulating Hormone (FSH)', 'Hormones', NULL),
    ('Prolactin', 'Hormones', 'ng/ml'),
    ('Testosterone', 'Hormones', 'ng/dl'),
    ('DHEA-SO4', 'Hormones', 'μg/dl'),
    ('17-Hydroxyprogesterone', 'Hormones', 'ng/ml'),
    -- Kidney & electrolytes
    ('Serum Creatinine', 'Kidney & electrolytes', 'mg/dl'),
    ('Estimated Glomerular Filtration Rate (eGFR)', 'Kidney & electrolytes', 'ml/min/1,73 m2'),
    ('Uric Acid', 'Kidney & electrolytes', 'mg/dl'),
    ('Serum Sodium (Na+)', 'Kidney & electrolytes', 'mmol/l'),
    ('Serum Potassium (K+)', 'Kidney & electrolytes', 'mmol/l'),
    ('Calcium (Ca)', 'Kidney & electrolytes', 'mmol/l'),
    -- Vitamins
    ('Vitamin D3 (25-OH)', 'Vitamins', 'ng/ml'),
    ('Vitamin B12', 'Vitamins', 'pg/ml'),
    ('Vitamin B3', 'Vitamins', 'pg/ml'),
    -- Inflammation & immunity
    ('C-Reactive Protein (CRP)', 'Inflammation & immunity', 'mg/l'),
    ('Erythrocyte Sedimentation Rate (ESR)', 'Inflammation & immunity', NULL),
    ('Immunoglobulin IgA', 'Inflammation & immunity', 'g/l'),
    -- Tumor markers
    ('CA-125', 'Tumor markers', 'U/ml'),
    ('HE4', 'Tumor markers', 'pmol/l');
