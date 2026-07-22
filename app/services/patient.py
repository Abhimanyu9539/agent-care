"""Plain-SQL queries for a patient's requests. Each request is one row in workflow_runs."""

from sqlalchemy import RowMapping, text
from sqlalchemy.orm import Session

from app.services import audit


def create_request(db: Session, user_id: int, request_text: str) -> int:
    """Save a request from this patient user, with its audit event. Returns the run id.

    The run starts as RUNNING (the column default).
    """
    run_id = db.execute(
        text(
            "INSERT INTO workflow_runs (patient_id, created_by, request_text) "
            "SELECT id, :user_id, :request_text FROM patient_profiles WHERE user_id = :user_id "
            "RETURNING id"
        ),
        {"user_id": user_id, "request_text": request_text},
    ).scalar_one()
    audit.record(
        db,
        actor_user_id=user_id,
        action="request.create",
        entity_type="workflow_run",
        entity_id=run_id,
        workflow_run_id=run_id,
    )
    db.commit()
    return run_id


def get_request(db: Session, run_id: int, user_id: int) -> RowMapping | None:
    """The request, or None when it does not exist or belongs to another patient."""
    return db.execute(
        text(
            "SELECT r.id, r.request_text, r.status, r.created_at "
            "FROM workflow_runs r JOIN patient_profiles p ON p.id = r.patient_id "
            "WHERE r.id = :run_id AND p.user_id = :user_id"
        ),
        {"run_id": run_id, "user_id": user_id},
    ).mappings().one_or_none()
