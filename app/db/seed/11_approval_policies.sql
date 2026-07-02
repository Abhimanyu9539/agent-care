-- Actions that need a staff member to approve them first.

INSERT INTO approval_policies (code, description, guards, params) VALUES
  ('cancel_within_24h', 'Cancelling a visit that starts within 24 hours needs staff approval.',            'appointment.cancel', '{"hours_before": 24}'),
  ('identity_change',   'Changing name or date of birth after registration needs staff approval.',      'patient.update',     '{"fields": ["full_name", "date_of_birth"]}');
