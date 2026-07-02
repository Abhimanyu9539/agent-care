-- Append-only log of every change: who did what, to which row, in which run.

CREATE TABLE audit_events (
  id              bigserial PRIMARY KEY,
  actor_user_id   bigint REFERENCES users(id), -- the person acted for: patient or staff
  actor_agent     text,                        -- 'appointment' when an agent acted; NULL for direct actions
  action          text NOT NULL,               -- 'appointment.book'
  entity_type     text NOT NULL,
  entity_id       bigint,
  workflow_run_id bigint REFERENCES workflow_runs(id),
  metadata        jsonb NOT NULL DEFAULT '{}', -- ids and codes only, never PII
  request_id      text,
  created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX audit_entity_idx ON audit_events (entity_type, entity_id, created_at);
CREATE INDEX audit_run_idx    ON audit_events (workflow_run_id, created_at);
