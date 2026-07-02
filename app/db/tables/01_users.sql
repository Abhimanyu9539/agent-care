-- Everyone who can sign in: patients, staff and admins.
-- Timestamps are stored in UTC; the hospital time zone is used only for display.

CREATE TABLE users (
  id            bigserial PRIMARY KEY,
  email         text NOT NULL,
  full_name     text NOT NULL,
  password_hash text NOT NULL,
  role          user_role NOT NULL,
  is_active     boolean NOT NULL DEFAULT true,
  created_at    timestamptz NOT NULL DEFAULT now()
);

-- One account per email, ignoring case.
CREATE UNIQUE INDEX users_email_uq ON users (lower(email));
