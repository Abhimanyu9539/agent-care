-- Hospital departments the Routing agent can send a request to.

CREATE TABLE departments (
  id            bigserial PRIMARY KEY,
  code          text NOT NULL UNIQUE,          -- 'cardiology'
  name          text NOT NULL,
  description   text NOT NULL,                 -- shown to the Routing agent
  routing_hints text NOT NULL DEFAULT '',      -- e.g. 'heart, ECG, BP follow-up'
  active        boolean NOT NULL DEFAULT true
);
