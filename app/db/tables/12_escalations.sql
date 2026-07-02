-- Cases handed to staff: emergencies, clinical questions, approvals, mismatches, failures.

CREATE TABLE escalations (
  id              bigserial PRIMARY KEY,
  workflow_run_id bigint REFERENCES workflow_runs(id),
  patient_id      bigint NOT NULL REFERENCES patient_profiles(id),
  type            escalation_type NOT NULL,
  priority        priority NOT NULL,
  reason          text NOT NULL,
  policy_code     text REFERENCES approval_policies(code),
  proposed_action jsonb,                       -- {"action": "appointment.cancel", "appointment_id": 1977}
  status          escalation_status NOT NULL DEFAULT 'OPEN',
  reviewed_by     bigint REFERENCES users(id),
  reviewed_at     timestamptz,
  review_note     text,
  created_at      timestamptz NOT NULL DEFAULT now()
);

-- At most one OPEN escalation per run.
CREATE UNIQUE INDEX one_open_escalation_per_run ON escalations (workflow_run_id) WHERE status = 'OPEN';
CREATE INDEX escalations_inbox_idx ON escalations (status, priority, created_at);
