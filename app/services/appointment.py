"""Plain-SQL queries for slots and appointments."""

from collections.abc import Sequence

from sqlalchemy import RowMapping, text
from sqlalchemy.orm import Session


def list_upcoming_slots(db: Session, time_zone: str, limit: int = 200) -> Sequence[RowMapping]:
    """Slots that have not started yet, soonest first, with start times in the hospital time zone."""
    return db.execute(
        text(
            "SELECT s.id, s.status, s.start_time AT TIME ZONE :tz AS starts_at, "
            "       d.full_name AS doctor, dep.name AS department "
            "FROM appointment_slots s "
            "JOIN doctors d ON d.id = s.doctor_id "
            "JOIN departments dep ON dep.id = d.department_id "
            "WHERE s.start_time >= now() "
            "ORDER BY s.start_time, s.id LIMIT :limit"
        ),
        {"tz": time_zone, "limit": limit},
    ).mappings().all()


def list_patient_visits(db: Session, patient_id: int) -> Sequence[RowMapping]:
    """One patient's appointments, oldest first: department, visit type, status and date. No free text."""
    return db.execute(
        text(
            "SELECT dep.code AS department, a.visit_type, a.status, s.start_time::date AS date "
            "FROM appointments a "
            "JOIN departments dep ON dep.id = a.department_id "
            "JOIN appointment_slots s ON s.id = a.slot_id "
            "WHERE a.patient_id = :patient_id "
            "ORDER BY s.start_time, a.id"
        ),
        {"patient_id": patient_id},
    ).mappings().all()
