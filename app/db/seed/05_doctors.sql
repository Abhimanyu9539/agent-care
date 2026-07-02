-- Doctors. Dr. Meera Iyer is doctor 7, as in the mockups (D-07).

INSERT INTO doctors (id, department_id, full_name) VALUES
  (1, 2, 'Dr. Kabir Shah'),       -- Dermatology
  (2, 3, 'Dr. Anil Kapoor'),      -- Physiotherapy
  (3, 4, 'Dr. Pooja Bhatt'),      -- ENT
  (4, 5, 'Dr. Farhan Ali'),       -- General Medicine
  (5, 5, 'Dr. Kavita Desai'),     -- General Medicine
  (6, 6, 'Dr. Vivek Kulkarni'),   -- Orthopaedics
  (7, 1, 'Dr. Meera Iyer'),       -- Cardiology
  (8, 1, 'Dr. Rajesh Nair');      -- Cardiology

SELECT setval(pg_get_serial_sequence('doctors', 'id'), (SELECT max(id) FROM doctors));
