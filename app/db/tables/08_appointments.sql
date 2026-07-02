-- Booked appointments. A reschedule creates a new row pointing back via rescheduled_from_id.

CREATE TABLE appointments (
  id                  bigserial PRIMARY KEY,
  patient_id          bigint NOT NULL REFERENCES patient_profiles(id),
  department_id       bigint NOT NULL REFERENCES departments(id),
  doctor_id           bigint NOT NULL REFERENCES doctors(id),
  slot_id             bigint NOT NULL REFERENCES appointment_slots(id),
  status              appointment_status NOT NULL DEFAULT 'CONFIRMED',
  visit_type          visit_type NOT NULL,
  reason              text NOT NULL,           -- administrative wording only
  rescheduled_from_id bigint REFERENCES appointments(id),
  workflow_run_id     bigint REFERENCES workflow_runs(id),
  idempotency_key     text UNIQUE,             -- a retried booking finds the same row
  cancel_reason       text,
  created_at          timestamptz NOT NULL DEFAULT now(),
  updated_at          timestamptz NOT NULL DEFAULT now()
);

-- No double booking: at most one CONFIRMED appointment per slot.
CREATE UNIQUE INDEX one_booking_per_slot ON appointments (slot_id) WHERE status = 'CONFIRMED';
CREATE INDEX appts_patient_idx ON appointments (patient_id, status);
