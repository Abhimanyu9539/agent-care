-- Uploaded documents. Ids follow the mockups (DOC-7731 = document 7731).
-- No real files are stored for seed rows; storage_key is only a name.
-- checksum_sha256 is the SHA-256 of a short label, so each file gets a real 64-character value.
SET TIME ZONE 'Asia/Kolkata';

INSERT INTO patient_documents (id, patient_id, uploaded_by, original_filename, storage_key, mime_type, size_bytes, checksum_sha256, document_type, type_confidence, document_date, name_matches, status, duplicate_of_id, appointment_id, workflow_run_id) VALUES
  -- Ananya: ECG and blood panel sent with her cardiology request (run 5521)
  (7731, 412, 17, 'ECG_report.pdf',  'sample/doc-7731.pdf', 'application/pdf', 421888,  encode(sha256('DOC-7731'), 'hex'), 'ECG',        0.97, current_date - 205, true, 'CLASSIFIED', NULL, NULL, 5521),
  (7732, 412, 17, 'Blood_panel.pdf', 'sample/doc-7732.pdf', 'application/pdf', 1153434, encode(sha256('DOC-7732'), 'hex'), 'BLOOD_TEST', 0.91, current_date - 217, true, 'CLASSIFIED', NULL, NULL, 5521),

  -- Ananya: the same ECG uploaded again. Same checksum as 7731, so it is only recorded as a DUPLICATE and the file is dropped.
  (7733, 412, 17, 'ECG_copy.pdf', NULL, 'application/pdf', 421888, encode(sha256('DOC-7731'), 'hex'), NULL, NULL, NULL, NULL, 'DUPLICATE', 7731, NULL, 5521),

  -- Fatima: her father's discharge summary. The name does not match her profile, so it waits for staff review.
  (7710, 450, 13, 'discharge_summary.pdf', 'sample/doc-7710.pdf', 'application/pdf', 230400, encode(sha256('DOC-7710'), 'hex'), 'DISCHARGE_SUMMARY', 0.88, current_date - 3, false, 'NEEDS_REVIEW', NULL, NULL, 5517),

  -- Sanjay: knee X-ray, attached to his orthopaedics visit
  (7690, 618, 16, 'knee_xray.jpg', 'sample/doc-7690.jpg', 'image/jpeg', 845000, encode(sha256('DOC-7690'), 'hex'), 'IMAGING', 0.95, current_date - 10, true, 'ATTACHED', NULL, 2033, 5514);

SELECT setval(pg_get_serial_sequence('patient_documents', 'id'), (SELECT max(id) FROM patient_documents));
