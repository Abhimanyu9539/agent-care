-- A proposed follow-up visit after an appointment; staff confirm the timing.

CREATE TABLE follow_up_tasks (
  id                   bigserial PRIMARY KEY,
  patient_id           bigint NOT NULL REFERENCES patient_profiles(id),
  appointment_id       bigint NOT NULL REFERENCES appointments(id),
  suggested_after_days int,                    -- department default; staff confirm the timing
  status               follow_up_status NOT NULL DEFAULT 'PROPOSED',
  confirmed_by         bigint REFERENCES users(id),
  confirmed_at         timestamptz,
  created_at           timestamptz NOT NULL DEFAULT now()
);
