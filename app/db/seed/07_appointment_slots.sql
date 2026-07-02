-- Appointment slots. Times are hospital local time, counted from the day the seed runs.
SET TIME ZONE 'Asia/Kolkata';

-- 1. Slots used by the demo appointments and requests.
--    Fixed ids (from the mockups, e.g. S-87702) so later files can point at them.
INSERT INTO appointment_slots (id, doctor_id, start_time, end_time, status, held_by_run_id, held_until) VALUES
  -- past visits
  (70165, 7, current_date - 205 + time '10:00', current_date - 205 + time '10:30', 'BOOKED',    NULL, NULL),  -- Ananya, cardiology (APT-1650)
  (70410, 4, current_date - 30  + time '10:00', current_date - 30  + time '10:30', 'BOOKED',    NULL, NULL),  -- Rohan, general medicine (APT-1702)
  -- upcoming visits
  (87702, 2, current_date + 1 + time '09:00',   current_date + 1 + time '09:30',   'BOOKED',    NULL, NULL),  -- Leela, physio tomorrow 9 am (APT-1977)
  (87950, 1, current_date + 9 + time '09:30',   current_date + 9 + time '10:00',   'BOOKED',    NULL, NULL),  -- Ananya, dermatology (APT-1999)
  (88003, 3, current_date + 2 + time '10:00',   current_date + 2 + time '10:30',   'AVAILABLE', NULL, NULL),  -- Arjun's old ENT time, freed when he moved it
  (88010, 3, current_date + 4 + time '15:00',   current_date + 4 + time '15:30',   'BOOKED',    NULL, NULL),  -- Arjun's new ENT time (APT-2036)
  (88021, 6, current_date + 3 + time '11:00',   current_date + 3 + time '11:30',   'BOOKED',    NULL, NULL),  -- Sanjay, orthopaedics (APT-2033)
  (88050, 5, current_date + 2 + time '14:00',   current_date + 2 + time '14:30',   'BLOCKED',   NULL, NULL),  -- Dr. Kavita Desai unavailable
  -- held for 15 minutes while Ananya chooses one (run 5521); the app releases them when the hold expires
  (88120, 7, current_date + 8  + time '10:30',  current_date + 8  + time '11:00',  'HELD', 5521, now() + interval '15 minutes'),
  (88131, 7, current_date + 9  + time '11:00',  current_date + 9  + time '11:30',  'HELD', 5521, now() + interval '15 minutes'),
  (88147, 7, current_date + 10 + time '09:30',  current_date + 10 + time '10:00',  'HELD', 5521, now() + interval '15 minutes');

-- 2. Four weeks of open slots: every doctor, Monday to Friday, 09:00 to 17:00, 30 minutes each.
INSERT INTO appointment_slots (doctor_id, start_time, end_time)
SELECT doctors.id, slot_start, slot_start + interval '30 minutes'
FROM doctors,
     generate_series(1, 28) AS day_offset,
     generate_series(current_date + day_offset + time '09:00',
                     current_date + day_offset + time '16:30',
                     interval '30 minutes') AS slot_start
WHERE extract(isodow FROM current_date + day_offset) <= 5   -- 1 = Monday ... 5 = Friday
ON CONFLICT (doctor_id, start_time) DO NOTHING;             -- skip times already added above

SELECT setval(pg_get_serial_sequence('appointment_slots', 'id'), (SELECT max(id) FROM appointment_slots));
