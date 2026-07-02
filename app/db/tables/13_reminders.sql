-- Reminders to send later: before an appointment, for a missing document, or for a follow-up.

CREATE TABLE reminders (
  id              bigserial PRIMARY KEY,
  patient_id      bigint NOT NULL REFERENCES patient_profiles(id),
  appointment_id  bigint REFERENCES appointments(id),
  document_type   document_type,               -- set for UPLOAD_MISSING_DOC
  reminder_type   reminder_type NOT NULL,
  channel         channel NOT NULL,
  scheduled_at    timestamptz NOT NULL,
  status          delivery_status NOT NULL DEFAULT 'SCHEDULED',
  attempts        int NOT NULL DEFAULT 0,
  last_error      text,
  idempotency_key text UNIQUE,
  created_at      timestamptz NOT NULL DEFAULT now()
);

-- The scheduler's lookup for reminders that are due.
CREATE INDEX reminders_due_idx ON reminders (scheduled_at) WHERE status = 'SCHEDULED';
