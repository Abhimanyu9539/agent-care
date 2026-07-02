-- Reminders. Ids follow the mockups (REM-3302 = reminder 3302).
-- Times are hospital local time, counted from the day the seed runs.
SET TIME ZONE 'Asia/Kolkata';

INSERT INTO reminders (id, patient_id, appointment_id, document_type, reminder_type, channel, scheduled_at, status, attempts, idempotency_key) VALUES
  -- Leela's physio tomorrow at 9 am (APT-1977): the 24-hour reminder went out this morning
  (3288, 388, 1977, NULL, 'APPOINTMENT_24H', 'SMS', current_date + time '09:00',     'SENT',      1, NULL),
  (3289, 388, 1977, NULL, 'APPOINTMENT_2H',  'SMS', current_date + 1 + time '07:00', 'SCHEDULED', 0, NULL),

  -- Ananya's dermatology visit (APT-1999)
  (3290, 412, 1999, NULL, 'APPOINTMENT_24H', 'SMS', current_date + 8 + time '09:30', 'SCHEDULED', 0, NULL),
  (3291, 412, 1999, NULL, 'APPOINTMENT_2H',  'SMS', current_date + 9 + time '07:30', 'SCHEDULED', 0, NULL),

  -- Arjun's old ENT time (APT-2030): cancelled when he moved the visit
  (3295, 291, 2030, NULL, 'APPOINTMENT_24H', 'SMS', current_date + 1 + time '10:00', 'CANCELLED', 0, NULL),

  -- Arjun's new ENT time (APT-2036), set by run 5518
  (3296, 291, 2036, NULL, 'APPOINTMENT_24H', 'SMS', current_date + 3 + time '15:00', 'SCHEDULED', 0, '5518:follow_up:remind_24h:2036'),
  (3297, 291, 2036, NULL, 'APPOINTMENT_2H',  'SMS', current_date + 4 + time '13:00', 'SCHEDULED', 0, '5518:follow_up:remind_2h:2036'),

  -- Sanjay's orthopaedics visit (APT-2033), set by run 5514
  (3298, 618, 2033, NULL, 'APPOINTMENT_24H', 'SMS', current_date + 2 + time '11:00', 'SCHEDULED', 0, '5514:follow_up:remind_24h:2033'),
  (3299, 618, 2033, NULL, 'APPOINTMENT_2H',  'SMS', current_date + 3 + time '09:00', 'SCHEDULED', 0, '5514:follow_up:remind_2h:2033'),

  -- Ananya: upload the missing lipid profile, set by run 5521
  (3302, 412, NULL, 'LIPID_PROFILE', 'UPLOAD_MISSING_DOC', 'SMS', current_date + 7 + time '18:00', 'SCHEDULED', 0, '5521:follow_up:missing_doc:LIPID_PROFILE');

SELECT setval(pg_get_serial_sequence('reminders', 'id'), (SELECT max(id) FROM reminders));
