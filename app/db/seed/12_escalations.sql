-- Cases handed to staff: the "Escalations" screen. Ids follow the mockups (ESC-0192 = escalation 192).

INSERT INTO escalations (id, workflow_run_id, patient_id, type, priority, reason, policy_code, proposed_action, status, reviewed_by, reviewed_at, review_note, created_at) VALUES
  -- Arjun: already approved by Rhea Menon earlier today
  (189, NULL, 291, 'POLICY_APPROVAL', 'NORMAL', 'Booking for a parent',
   NULL, NULL,
   'APPROVED', 2, now() - interval '80 minutes', 'Confirmed by phone with the patient.', now() - interval '84 minutes'),

  -- Fatima: name on the document does not match her profile; the file is held, not attached
  (191, 5517, 450, 'DOCUMENT_MISMATCH', 'HIGH', 'Name on document doesn''t match the patient profile.',
   NULL, '{"action": "document.attach", "document_id": 7710}',
   'OPEN', NULL, NULL, NULL, now() - interval '32 minutes'),

  -- Leela: cancelling tomorrow's visit needs approval (policy cancel_within_24h)
  (192, 5519, 388, 'POLICY_APPROVAL', 'HIGH', 'Cancellation within 24 hours of the visit.',
   'cancel_within_24h', '{"action": "appointment.cancel", "appointment_id": 1977}',
   'OPEN', NULL, NULL, NULL, now() - interval '13 minutes'),

  -- Vikram: urgent symptoms, nothing booked
  (193, 5522, 577, 'EMERGENCY', 'URGENT', 'Urgent symptoms described: chest pain right now.',
   NULL, NULL,
   'OPEN', NULL, NULL, NULL, now() - interval '1 minute');

SELECT setval(pg_get_serial_sequence('escalations', 'id'), (SELECT max(id) FROM escalations));
