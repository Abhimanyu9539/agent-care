-- One row per patient request handled by the agents.
-- snapshot is a small summary for staff; LangGraph keeps the full state in its own tables.

CREATE TABLE workflow_runs (
  id            bigserial PRIMARY KEY,
  patient_id    bigint NOT NULL REFERENCES patient_profiles(id),
  created_by    bigint NOT NULL REFERENCES users(id),
  request_text  text NOT NULL,
  intent        text,                          -- BOOK, RESCHEDULE, CANCEL, DOCUMENTS_ONLY, STATUS
  department_id bigint REFERENCES departments(id),
  status        run_status NOT NULL DEFAULT 'RUNNING',
  current_step  text NOT NULL DEFAULT 'safety_intake',
  snapshot      jsonb NOT NULL DEFAULT '{}',   -- business view for staff
  error         jsonb,
  attempt       int NOT NULL DEFAULT 1,
  created_at    timestamptz NOT NULL DEFAULT now(),
  updated_at    timestamptz NOT NULL DEFAULT now(),
  completed_at  timestamptz
);

CREATE INDEX runs_status_idx  ON workflow_runs (status, updated_at);
CREATE INDEX runs_patient_idx ON workflow_runs (patient_id, created_at DESC);
