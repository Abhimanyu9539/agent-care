-- One profile per patient user. Ids follow the mockups (PT-0412 = patient 412).

INSERT INTO patient_profiles (id, user_id, full_name, date_of_birth, phone, preferred_language, emergency_contact_name, emergency_contact_phone) VALUES
  (291, 12, 'Arjun Mehta',   '1979-11-02', '+91 90000 00291', 'en', 'Kavya Mehta',  '+91 90000 10291'),
  (388, 11, 'Leela Pillai',  '1985-06-21', '+91 98000 00210', 'en', 'Suresh Pillai', '+91 90000 10388'),
  (412, 17, 'Ananya Rao',    '1991-03-08', '+91 90000 00412', 'en', 'Vikas Rao',    '+91 90000 10412'),
  (450, 13, 'Fatima Khan',   '1988-09-14', '+91 90000 00450', 'hi', 'Imran Khan',   '+91 90000 10450'),
  (503, 14, 'Rohan Das',     '1962-01-30', '+91 90000 00503', 'en', NULL,           NULL),
  (577, 10, 'Vikram Singh',  '1970-04-12', '+91 90000 00577', 'hi', 'Preeti Singh', '+91 90000 10577'),
  (612, 15, 'Neha Joshi',    '1996-12-05', '+91 90000 00612', 'en', NULL,           NULL),
  (618, 16, 'Sanjay Tiwari', '1983-07-19', '+91 90000 00618', 'en', 'Meena Tiwari', '+91 90000 10618');

SELECT setval(pg_get_serial_sequence('patient_profiles', 'id'), (SELECT max(id) FROM patient_profiles));
