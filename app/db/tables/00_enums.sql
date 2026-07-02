-- Enum types: each column that uses one accepts only these values.

CREATE TYPE user_role          AS ENUM ('PATIENT', 'STAFF', 'ADMIN');
CREATE TYPE slot_status        AS ENUM ('AVAILABLE', 'HELD', 'BOOKED', 'BLOCKED');
CREATE TYPE appointment_status AS ENUM ('CONFIRMED', 'CANCELLED', 'RESCHEDULED', 'COMPLETED', 'NO_SHOW');
CREATE TYPE visit_type         AS ENUM ('NEW', 'FOLLOW_UP');
CREATE TYPE document_type      AS ENUM ('ECG', 'BLOOD_TEST', 'LIPID_PROFILE', 'IMAGING', 'DISCHARGE_SUMMARY',
                                        'PRESCRIPTION', 'REFERRAL', 'ID_PROOF', 'INSURANCE', 'OTHER');
CREATE TYPE document_status    AS ENUM ('RECEIVED', 'CLASSIFIED', 'NEEDS_REVIEW', 'ATTACHED', 'REJECTED', 'DUPLICATE');
CREATE TYPE run_status         AS ENUM ('RUNNING', 'WAITING_PATIENT_INPUT', 'WAITING_APPROVAL', 'ESCALATED',
                                        'COMPLETED', 'FAILED', 'CANCELLED');
CREATE TYPE escalation_type    AS ENUM ('EMERGENCY', 'CLINICAL_ADVICE', 'POLICY_APPROVAL', 'DOCUMENT_MISMATCH',
                                        'LOW_CONFIDENCE', 'SYSTEM_FAILURE');
CREATE TYPE escalation_status  AS ENUM ('OPEN', 'APPROVED', 'REJECTED', 'RESOLVED');
CREATE TYPE priority           AS ENUM ('URGENT', 'HIGH', 'NORMAL');
CREATE TYPE reminder_type      AS ENUM ('APPOINTMENT_24H', 'APPOINTMENT_2H', 'UPLOAD_MISSING_DOC', 'FOLLOW_UP');
CREATE TYPE delivery_status    AS ENUM ('SCHEDULED', 'SENT', 'FAILED', 'CANCELLED');
CREATE TYPE channel            AS ENUM ('IN_APP', 'SMS', 'EMAIL');
CREATE TYPE follow_up_status   AS ENUM ('PROPOSED', 'CONFIRMED', 'BOOKED', 'DISMISSED');
