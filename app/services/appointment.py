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
