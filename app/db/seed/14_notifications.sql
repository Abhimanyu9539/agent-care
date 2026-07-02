-- Messages already sent to patients (the outbox).
SET TIME ZONE 'Asia/Kolkata';

INSERT INTO notifications (patient_id, reminder_id, channel, body, status, sent_at) VALUES
  -- Leela's 24-hour reminder (reminder 3288)
  (388, 3288, 'SMS',
   'Reminder: Physiotherapy with Dr. Anil Kapoor tomorrow at 9:00 am. Ref APT-1977.',
   'SENT', current_date + time '09:00:02'),

  -- Booking confirmation for Sanjay (run 5514)
  (618, NULL, 'IN_APP',
   'You are booked: Orthopaedics with Dr. Vivek Kulkarni. Ref APT-2033. Please bring your X-ray and a photo ID.',
   'SENT', now() - interval '60 minutes'),

  -- Reschedule confirmation for Arjun (run 5518)
  (291, NULL, 'IN_APP',
   'Your ENT visit with Dr. Pooja Bhatt has moved to the new time you chose. Ref APT-2036.',
   'SENT', now() - interval '18 minutes');
