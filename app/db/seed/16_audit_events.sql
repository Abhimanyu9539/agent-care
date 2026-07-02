-- Audit log, oldest first. actor_agent is set when an agent acted for the user.
-- metadata holds ids and codes only, never personal details.

INSERT INTO audit_events (actor_user_id, actor_agent, action, entity_type, entity_id, workflow_run_id, metadata, created_at) VALUES
  (2,  NULL,          'auth.login',             'user',         2,    NULL, '{"ip_prefix": "10.0.0"}',                                                         now() - interval '2 hours'),
  (2,  NULL,          'escalation.decide',      'escalation',   189,  NULL, '{"approved": true}',                                                              now() - interval '80 minutes'),
  (16, 'appointment', 'appointment.book',       'appointment',  2033, 5514, '{"slot_id": 88021}',                                                              now() - interval '61 minutes'),
  (15, NULL,          'workflow.status_change', 'workflow_run', 5515, 5515, '{"from": "RUNNING", "to": "FAILED", "attempt": 1}',                               now() - interval '45 minutes'),
  (14, 'safety',      'safety.blocked_input',   'workflow_run', 5516, 5516, '{"rule_id": "clinical_advice.dose"}',                                             now() - interval '39 minutes'),
  (13, 'documents',   'escalation.open',        'escalation',   191,  5517, '{"type": "DOCUMENT_MISMATCH", "priority": "HIGH"}',                               now() - interval '32 minutes'),
  (12, 'appointment', 'appointment.reschedule', 'appointment',  2036, 5518, '{"slot_id": 88010, "rescheduled_from_id": 2030}',                                 now() - interval '18 minutes'),
  (11, 'appointment', 'escalation.open',        'escalation',   192,  5519, '{"type": "POLICY_APPROVAL", "priority": "HIGH", "policy_code": "cancel_within_24h"}', now() - interval '13 minutes'),
  (17, NULL,          'request.create',         'workflow_run', 5521, 5521, '{}',                                                                              now() - interval '360 seconds'),
  (17, NULL,          'document.upload',        'document',     7731, 5521, '{"mime_type": "application/pdf"}',                                                now() - interval '360 seconds'),
  (17, NULL,          'document.upload',        'document',     7732, 5521, '{"mime_type": "application/pdf"}',                                                now() - interval '360 seconds'),
  (17, NULL,          'document.duplicate',     'document',     7733, 5521, '{"duplicate_of": 7731}',                                                          now() - interval '360 seconds'),
  (17, 'coordinator', 'workflow.start',         'workflow_run', 5521, 5521, '{"attempt": 1}',                                                                  now() - interval '359 seconds'),
  (17, 'appointment', 'slot.hold',              'slot',         NULL, 5521, '{"slot_ids": [88120, 88131, 88147], "hold_minutes": 15}',                         now() - interval '353 seconds'),
  (17, 'follow_up',   'reminder.schedule',      'reminder',     3302, 5521, '{"type": "UPLOAD_MISSING_DOC", "channel": "SMS"}',                                now() - interval '350 seconds'),
  (10, 'safety',      'escalation.open',        'escalation',   193,  5522, '{"type": "EMERGENCY", "priority": "URGENT"}',                                     now() - interval '1 minute');
