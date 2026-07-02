-- Follow-up visits suggested after an appointment. Staff confirm the timing.

INSERT INTO follow_up_tasks (patient_id, appointment_id, suggested_after_days, status, confirmed_by, confirmed_at) VALUES
  (412, 1650, 180, 'CONFIRMED', 2,    now() - interval '200 days'),  -- Ananya: cardiology follow-up; her current request (run 5521) books it
  (503, 1702, 90,  'PROPOSED',  NULL, NULL);                         -- Rohan: blood pressure follow-up, waiting for staff
