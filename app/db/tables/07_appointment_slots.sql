-- Bookable time slots for each doctor.
-- A HELD slot is reserved for one run until held_until (offered to the patient, 15 minutes).

CREATE TABLE appointment_slots (
  id             bigserial PRIMARY KEY,
  doctor_id      bigint NOT NULL REFERENCES doctors(id),
  start_time     timestamptz NOT NULL,
  end_time       timestamptz NOT NULL,
  status         slot_status NOT NULL DEFAULT 'AVAILABLE',
  held_by_run_id bigint REFERENCES workflow_runs(id),
  held_until     timestamptz,
  CHECK (end_time > start_time),
  -- held_by_run_id and held_until are set exactly when the slot is HELD.
  CHECK ((status = 'HELD') = (held_by_run_id IS NOT NULL AND held_until IS NOT NULL)),
  UNIQUE (doctor_id, start_time)
);

-- Fast search for free slots.
CREATE INDEX slots_open_idx ON appointment_slots (doctor_id, start_time) WHERE status = 'AVAILABLE';
