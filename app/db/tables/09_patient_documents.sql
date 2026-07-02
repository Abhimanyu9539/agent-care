-- Uploaded files. The file itself lives in storage; this row holds its metadata.
-- name_matches stores only yes/no, not the name printed on the file, so no extra PII is saved.

CREATE TABLE patient_documents (
  id                bigserial PRIMARY KEY,
  patient_id        bigint NOT NULL REFERENCES patient_profiles(id),
  uploaded_by       bigint NOT NULL REFERENCES users(id),
  original_filename text NOT NULL,
  storage_key       text UNIQUE,               -- uuid file name; NULL once discarded as a DUPLICATE
  mime_type         text NOT NULL,
  size_bytes        int NOT NULL,
  checksum_sha256   char(64) NOT NULL,
  document_type     document_type,             -- NULL until classified
  type_confidence   numeric(3,2),
  document_date     date,
  name_matches      boolean,                   -- identity check result, computed in code
  status            document_status NOT NULL DEFAULT 'RECEIVED',
  duplicate_of_id   bigint REFERENCES patient_documents(id),
  appointment_id    bigint REFERENCES appointments(id),
  workflow_run_id   bigint REFERENCES workflow_runs(id),
  created_at        timestamptz NOT NULL DEFAULT now()
);

-- No duplicate file per patient (DUPLICATE rows only record that one was rejected).
CREATE UNIQUE INDEX no_duplicate_file ON patient_documents (patient_id, checksum_sha256) WHERE status <> 'DUPLICATE';
CREATE INDEX docs_lookup_idx ON patient_documents (patient_id, document_type, document_date);
