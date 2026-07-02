-- Appointments. Ids follow the mockups (APT-1977 = appointment 1977).
SET TIME ZONE 'Asia/Kolkata';

INSERT INTO appointments (id, patient_id, department_id, doctor_id, slot_id, status, visit_type, reason, rescheduled_from_id, workflow_run_id, idempotency_key, created_at) VALUES
  -- past visits
  (1650, 412, 1, 7, 70165, 'COMPLETED',   'NEW',       'Cardiology review',        NULL, NULL, NULL, current_date - 212 + time '18:00'),  -- Ananya
  (1702, 503, 5, 4, 70410, 'COMPLETED',   'NEW',       'Blood pressure check',     NULL, NULL, NULL, current_date - 35  + time '12:00'),  -- Rohan
  -- upcoming visits
  (1977, 388, 3, 2, 87702, 'CONFIRMED',   'FOLLOW_UP', 'Physiotherapy session',    NULL, NULL, NULL, current_date - 6   + time '16:20'),  -- Leela, tomorrow 9 am
  (1999, 412, 2, 1, 87950, 'CONFIRMED',   'NEW',       'Skin checkup',             NULL, NULL, NULL, current_date - 7   + time '18:06'),  -- Ananya
  (2030, 291, 4, 3, 88003, 'RESCHEDULED', 'FOLLOW_UP', 'ENT follow-up',            NULL, NULL, NULL, current_date - 10  + time '11:00'),  -- Arjun, old time
  (2033, 618, 6, 6, 88021, 'CONFIRMED',   'NEW',       'Orthopaedics first visit', NULL, 5514, '5514:appointment:book:88021',       now() - interval '61 minutes'),  -- Sanjay
  (2036, 291, 4, 3, 88010, 'CONFIRMED',   'FOLLOW_UP', 'ENT follow-up',            2030, 5518, '5518:appointment:reschedule:88010', now() - interval '18 minutes');  -- Arjun, new time

SELECT setval(pg_get_serial_sequence('appointments', 'id'), (SELECT max(id) FROM appointments));
