-- The agent timeline for three runs: the staff "Workflow run" screen.
-- Run 5521 (Ananya) is the full example from the mockup, including one retried step.
-- tool_calls entries are {tool, args, ok, ms, result_ref}; llm_meta holds model details.

INSERT INTO workflow_steps (run_id, seq, agent, node, outcome, input_summary, output, tool_calls, llm_meta, latency_ms, created_at) VALUES
  -- Run 5521: Ananya, cardiology follow-up
  (5521, 1, 'safety', 'safety_intake', 'OK',
   '{"text_chars": 104, "attachments": 2}',
   '{"category": "ADMIN", "reason": "Booking and document request, nothing urgent"}',
   '[{"tool": "red_flag_rules", "args": {}, "ok": true, "ms": 4, "result_ref": "0 matches"}]',
   '{"model": "sample-model", "prompt_version": "safety/v1", "tokens_in": 412, "tokens_out": 38, "attempts": 1}',
   600, now() - interval '360 seconds'),

  (5521, 2, 'coordinator', 'coordinator', 'OK',
   '{"patient_id": 412}',
   '{"intent": "BOOK", "steps": ["ROUTE", "DOCUMENTS", "APPOINTMENT", "FOLLOW_UP"]}',
   '[{"tool": "get_or_create_patient", "args": {}, "ok": true, "ms": 18, "result_ref": "patient:412"},
     {"tool": "get_patient_context", "args": {}, "ok": true, "ms": 22, "result_ref": "patient:412"}]',
   '{"model": "sample-model", "prompt_version": "coordinator/v1", "tokens_in": 880, "tokens_out": 64, "attempts": 1}',
   1400, now() - interval '359 seconds'),

  (5521, 3, 'routing', 'routing', 'OK',
   '{"patient_id": 412}',
   '{"department_code": "cardiology", "visit_type": "FOLLOW_UP", "confidence": 0.94, "rationale": "Follow-up to an earlier cardiology visit"}',
   '[{"tool": "list_departments", "args": {}, "ok": true, "ms": 9, "result_ref": "6 active"},
     {"tool": "get_patient_history", "args": {"department_code": "cardiology"}, "ok": true, "ms": 14, "result_ref": "appointment:1650"}]',
   '{"model": "sample-model", "prompt_version": "routing/v1", "tokens_in": 1210, "tokens_out": 52, "attempts": 1}',
   1100, now() - interval '357 seconds'),

  (5521, 4, 'documents', 'documents', 'OK',
   '{"attachments": [7731, 7732]}',
   '{"classified": [7731, 7732], "duplicates": [], "missing": ["LIPID_PROFILE"], "needs_review": []}',
   '[{"tool": "classify_document", "args": {"document_id": 7731, "type": "ECG", "confidence": 0.97}, "ok": true, "ms": 31, "result_ref": "document:7731"},
     {"tool": "classify_document", "args": {"document_id": 7732, "type": "BLOOD_TEST", "confidence": 0.91}, "ok": true, "ms": 29, "result_ref": "document:7732"},
     {"tool": "find_duplicates", "args": {"document_id": 7731}, "ok": true, "ms": 11, "result_ref": "none"},
     {"tool": "get_required_documents", "args": {"department_code": "cardiology", "visit_type": "FOLLOW_UP"}, "ok": true, "ms": 12, "result_ref": "missing: LIPID_PROFILE"}]',
   '{"model": "sample-model", "prompt_version": "documents/v1", "tokens_in": 2140, "tokens_out": 96, "attempts": 1}',
   3200, now() - interval '356 seconds'),

  -- The first answer proposed a date outside the requested week; it was retried with the error and passed
  (5521, 5, 'appointment', 'appointment', 'RETRIED',
   '{"department_id": 1, "doctor_id": 7}',
   '{"action": "OFFER", "offered_slot_ids": [88120, 88131, 88147], "appointment_id": null, "status": "WAITING_PATIENT_INPUT"}',
   '[{"tool": "search_slots", "args": {"department_code": "cardiology", "part_of_day": "morning"}, "ok": true, "ms": 21, "result_ref": "4 open"},
     {"tool": "check_conflicts", "args": {"slot_ids": [88120, 88131, 88147]}, "ok": true, "ms": 15, "result_ref": "1 excluded: clashes with appointment:1999"},
     {"tool": "hold_slots", "args": {"slot_ids": [88120, 88131, 88147]}, "ok": true, "ms": 25, "result_ref": "3 held for 15 min"}]',
   '{"model": "sample-model", "prompt_version": "appointment/v1", "tokens_in": 1630, "tokens_out": 140, "attempts": 2}',
   2400, now() - interval '353 seconds'),

  (5521, 6, 'follow_up', 'follow_up', 'OK',
   '{"missing": ["LIPID_PROFILE"]}',
   '{"reminders": [3302], "propose_follow_up": false}',
   '[{"tool": "create_missing_doc_reminder", "args": {"document_type": "LIPID_PROFILE"}, "ok": true, "ms": 17, "result_ref": "reminder:3302"}]',
   '{"model": "sample-model", "prompt_version": "follow_up/v1", "tokens_in": 540, "tokens_out": 70, "attempts": 1}',
   300, now() - interval '350 seconds'),

  (5521, 7, 'safety', 'safety_output', 'OK',
   '{"messages": 1}',
   '{"has_clinical_claim": false, "spans": []}',
   '[{"tool": "output_guard", "args": {}, "ok": true, "ms": 6, "result_ref": "0 clinical claims"}]',
   '{"model": "sample-model", "prompt_version": "output_guard/v1", "tokens_in": 310, "tokens_out": 12, "attempts": 1}',
   400, now() - interval '349 seconds'),

  -- Run 5515: Neha, the coordinator's LLM call timed out 3 times
  (5515, 1, 'safety', 'safety_intake', 'OK',
   '{"text_chars": 34, "attachments": 0}',
   '{"category": "ADMIN", "reason": "Booking request"}',
   '[{"tool": "red_flag_rules", "args": {}, "ok": true, "ms": 3, "result_ref": "0 matches"}]',
   '{"model": "sample-model", "prompt_version": "safety/v1", "tokens_in": 298, "tokens_out": 30, "attempts": 1}',
   500, now() - interval '46 minutes'),

  (5515, 2, 'coordinator', 'coordinator', 'FAILED',
   '{"patient_id": 612}',
   NULL,
   '[]',
   '{"model": "sample-model", "prompt_version": "coordinator/v1", "attempts": 3, "error": "timeout"}',
   60000, now() - interval '45 minutes'),

  -- Run 5522: Vikram, a red-flag rule matched, so no LLM call and straight to staff
  (5522, 1, 'safety', 'safety_intake', 'OK',
   '{"text_chars": 70, "attachments": 0}',
   '{"category": "EMERGENCY", "reason": "Red-flag rule: chest pain right now"}',
   '[{"tool": "red_flag_rules", "args": {}, "ok": true, "ms": 3, "result_ref": "EMERGENCY"},
     {"tool": "open_escalation", "args": {"type": "EMERGENCY"}, "ok": true, "ms": 20, "result_ref": "escalation:193"}]',
   NULL,
   50, now() - interval '1 minute');
