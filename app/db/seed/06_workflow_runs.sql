-- Patient requests handled by the agents: the staff "Requests" screen from the mockups.
-- Ids follow the mockups (WR-5521 = run 5521). Times are relative to when the seed runs.

INSERT INTO workflow_runs (id, patient_id, created_by, request_text, intent, department_id, status, current_step, snapshot, error, created_at, updated_at, completed_at) VALUES
  -- Sanjay: new patient, booked and done
  (5514, 618, 16, 'New patient, need an orthopaedics appointment',
   'BOOK', 6, 'COMPLETED', 'finalize',
   '{"appointment_id": 2033}', NULL,
   now() - interval '63 minutes', now() - interval '60 minutes', now() - interval '60 minutes'),

  -- Neha: the LLM timed out, so the run failed and staff can retry it
  (5515, 612, 15, 'Dermatology, any evening next week',
   'BOOK', NULL, 'FAILED', 'coordinator',
   '{}', '{"code": "LLM_UNAVAILABLE", "message": "LLM timeout after 3 attempts"}',
   now() - interval '46 minutes', now() - interval '45 minutes', NULL),

  -- Rohan: dosage question declined, offered a visit instead
  (5516, 503, 14, 'What dose of my BP tablets should I take?',
   'BOOK', 5, 'WAITING_PATIENT_INPUT', 'await_patient_input',
   '{"declined": "dosage question", "offered": "general medicine visit"}', NULL,
   now() - interval '39 minutes', now() - interval '38 minutes', NULL),

  -- Fatima: uploaded a document whose name does not match her profile
  (5517, 450, 13, 'Uploading my father''s discharge summary for his visit',
   'DOCUMENTS_ONLY', 5, 'WAITING_APPROVAL', 'await_approval',
   '{"needs_review": [7710], "escalation_id": 191}', NULL,
   now() - interval '32 minutes', now() - interval '32 minutes', NULL),

  -- Arjun: moved his ENT visit
  (5518, 291, 12, 'Move my ENT visit to Friday afternoon',
   'RESCHEDULE', 4, 'COMPLETED', 'finalize',
   '{"appointment_id": 2036, "rescheduled_from_id": 2030}', NULL,
   now() - interval '19 minutes', now() - interval '18 minutes', now() - interval '18 minutes'),

  -- Leela: late cancellation, paused until staff approve
  (5519, 388, 11, 'Cancel tomorrow''s 9 am physio, something came up',
   'CANCEL', 3, 'WAITING_APPROVAL', 'await_approval',
   '{"appointment_id": 1977, "escalation_id": 192}', NULL,
   now() - interval '13 minutes', now() - interval '13 minutes', NULL),

  -- Ananya: cardiology follow-up, waiting for her to pick one of 3 held slots
  (5521, 412, 17, 'I need a cardiology follow-up next week. I also want to attach my previous ECG and blood reports.',
   'BOOK', 1, 'WAITING_PATIENT_INPUT', 'await_patient_input',
   '{"department": "cardiology", "is_follow_up": true, "offered_slots": [88120, 88131, 88147], "documents": {"received": [7731, 7732], "missing": ["LIPID_PROFILE"]}, "reminders": [3302], "escalations": []}', NULL,
   now() - interval '6 minutes', now() - interval '6 minutes', NULL),

  -- Vikram: emergency, stopped by the safety agent and sent to staff
  (5522, 577, 10, 'I have crushing chest pain right now and want to see a cardiologist.',
   NULL, NULL, 'ESCALATED', 'escalate',
   '{"escalation_id": 193}', NULL,
   now() - interval '1 minute', now() - interval '1 minute', NULL);

SELECT setval(pg_get_serial_sequence('workflow_runs', 'id'), (SELECT max(id) FROM workflow_runs));
