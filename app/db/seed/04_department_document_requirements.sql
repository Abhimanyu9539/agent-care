-- Documents each department needs before a visit. max_age_days NULL means any age.

INSERT INTO department_document_requirements (department_id, visit_type, document_type, max_age_days, mandatory) VALUES
  (1, 'FOLLOW_UP', 'ECG',           365,  true),   -- Cardiology follow-up
  (1, 'FOLLOW_UP', 'BLOOD_TEST',    365,  true),
  (1, 'FOLLOW_UP', 'LIPID_PROFILE', 180,  true),   -- one from the last 6 months
  (3, 'NEW',       'REFERRAL',      NULL, true),   -- Physiotherapy needs a referral
  (5, 'NEW',       'ID_PROOF',      NULL, true),   -- General Medicine first visit
  (6, 'NEW',       'IMAGING',       90,   true),   -- Orthopaedics: a recent X-ray or scan
  (6, 'NEW',       'REFERRAL',      NULL, false);  -- optional
