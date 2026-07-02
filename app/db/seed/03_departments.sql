-- Hospital departments. description and routing_hints are what the Routing agent reads.

INSERT INTO departments (id, code, name, description, routing_hints) VALUES
  (1, 'cardiology',       'Cardiology',       'Heart and blood-vessel visits: checkups, ECG reviews, blood pressure follow-ups.', 'heart, ECG, BP, cholesterol, palpitations, cardiologist'),
  (2, 'dermatology',      'Dermatology',      'Skin, hair and nail visits.',                                                     'skin, rash, acne, hair, nails, mole'),
  (3, 'physiotherapy',    'Physiotherapy',    'Rehabilitation and exercise therapy sessions.',                                   'physio, rehab, back pain sessions, exercise therapy'),
  (4, 'ent',              'ENT',              'Ear, nose and throat visits.',                                                    'ear, nose, throat, sinus, hearing'),
  (5, 'general_medicine', 'General Medicine', 'First visits, general checkups and anything not yet routed.',                     'general checkup, fever, BP, diabetes, not sure'),
  (6, 'orthopaedics',     'Orthopaedics',     'Bone and joint visits, including fractures.',                                     'bone, joint, fracture, knee, spine, orthopaedic');

SELECT setval(pg_get_serial_sequence('departments', 'id'), (SELECT max(id) FROM departments));
