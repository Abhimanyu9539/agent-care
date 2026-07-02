-- A patient's details. Walk-ins registered by staff have no user account.

CREATE TABLE patient_profiles (
  id                      bigserial PRIMARY KEY,
  user_id                 bigint UNIQUE REFERENCES users(id),  -- NULL for walk-ins registered by staff
  full_name               text NOT NULL,
  date_of_birth           date NOT NULL,
  phone                   text NOT NULL,
  preferred_language      text NOT NULL DEFAULT 'en',
  emergency_contact_name  text,
  emergency_contact_phone text,
  created_at              timestamptz NOT NULL DEFAULT now(),
  updated_at              timestamptz NOT NULL DEFAULT now()
);

-- Find a patient by name and date of birth.
CREATE INDEX patient_identity_idx ON patient_profiles (lower(full_name), date_of_birth);
