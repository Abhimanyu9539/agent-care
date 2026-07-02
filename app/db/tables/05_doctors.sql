-- Doctors, each in one department.

CREATE TABLE doctors (
  id            bigserial PRIMARY KEY,
  department_id bigint NOT NULL REFERENCES departments(id),
  full_name     text NOT NULL,
  active        boolean NOT NULL DEFAULT true
);
