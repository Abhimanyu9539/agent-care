-- Outbox: one row per message sent or attempted.

CREATE TABLE notifications (
  id          bigserial PRIMARY KEY,
  patient_id  bigint NOT NULL REFERENCES patient_profiles(id),
  reminder_id bigint REFERENCES reminders(id),
  channel     channel NOT NULL,
  body        text NOT NULL,
  status      delivery_status NOT NULL,
  sent_at     timestamptz,
  error       text,
  created_at  timestamptz NOT NULL DEFAULT now()
);
