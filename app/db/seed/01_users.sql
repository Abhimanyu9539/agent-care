-- Demo users. All people and contact details in the seed data are made up.
-- Every user's password is: password123 (password_hash is its bcrypt hash).
-- Ids follow the UI design mockups where they show one (user 17 = Ananya Rao).

INSERT INTO users (id, email, full_name, role, password_hash) VALUES
  (1,  'admin@example.com',         'Kiran Bose',    'ADMIN',   '$2b$12$/UM6mwtFOTpl4GkiqqzPv.EjrmflgYH7Gy2sixmXbve8mdyBSQbCK'),
  (2,  'rhea.menon@example.com',    'Rhea Menon',    'STAFF',   '$2b$12$/UM6mwtFOTpl4GkiqqzPv.EjrmflgYH7Gy2sixmXbve8mdyBSQbCK'),
  (10, 'vikram.singh@example.com',  'Vikram Singh',  'PATIENT', '$2b$12$/UM6mwtFOTpl4GkiqqzPv.EjrmflgYH7Gy2sixmXbve8mdyBSQbCK'),
  (11, 'leela.pillai@example.com',  'Leela Pillai',  'PATIENT', '$2b$12$/UM6mwtFOTpl4GkiqqzPv.EjrmflgYH7Gy2sixmXbve8mdyBSQbCK'),
  (12, 'arjun.mehta@example.com',   'Arjun Mehta',   'PATIENT', '$2b$12$/UM6mwtFOTpl4GkiqqzPv.EjrmflgYH7Gy2sixmXbve8mdyBSQbCK'),
  (13, 'fatima.khan@example.com',   'Fatima Khan',   'PATIENT', '$2b$12$/UM6mwtFOTpl4GkiqqzPv.EjrmflgYH7Gy2sixmXbve8mdyBSQbCK'),
  (14, 'rohan.das@example.com',     'Rohan Das',     'PATIENT', '$2b$12$/UM6mwtFOTpl4GkiqqzPv.EjrmflgYH7Gy2sixmXbve8mdyBSQbCK'),
  (15, 'neha.joshi@example.com',    'Neha Joshi',    'PATIENT', '$2b$12$/UM6mwtFOTpl4GkiqqzPv.EjrmflgYH7Gy2sixmXbve8mdyBSQbCK'),
  (16, 'sanjay.tiwari@example.com', 'Sanjay Tiwari', 'PATIENT', '$2b$12$/UM6mwtFOTpl4GkiqqzPv.EjrmflgYH7Gy2sixmXbve8mdyBSQbCK'),
  (17, 'ananya.rao@example.com',    'Ananya Rao',    'PATIENT', '$2b$12$/UM6mwtFOTpl4GkiqqzPv.EjrmflgYH7Gy2sixmXbve8mdyBSQbCK');

-- Move the id counter past the rows above, so new rows get fresh ids.
SELECT setval(pg_get_serial_sequence('users', 'id'), (SELECT max(id) FROM users));
