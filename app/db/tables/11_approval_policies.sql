-- Rules for actions that need staff approval, e.g. cancelling within 24 hours.

CREATE TABLE approval_policies (
  code        text PRIMARY KEY,                -- 'cancel_within_24h'
  description text NOT NULL,
  guards      text NOT NULL,                   -- the action it guards: 'appointment.cancel'
  params      jsonb NOT NULL,                  -- {"hours_before": 24}
  active      boolean NOT NULL DEFAULT true
);
