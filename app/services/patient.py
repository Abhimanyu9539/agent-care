"""Plain-SQL queries for a patient's requests. Each request is one row in workflow_runs."""

from sqlalchemy import RowMapping, text
from sqlalchemy.orm import Session

from app.services import audit
from app.services.workflow import STUCK


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
    """The request, or None when it does not exist or belongs to another patient.

    `safety` is what the safety step found (EMERGENCY, CLINICAL_ADVICE or ADMIN), or None before it has run.
    When the request was routed: `department` (its name), `visit_type`, and `changed_to_new` when the
    patient asked for a follow-up but had never visited that department. `stuck` when it has been
    RUNNING with no progress for 10 minutes.
    """
    return db.execute(
        text(
            f"SELECT r.id, r.request_text, r.status, r.created_at, {STUCK} AS stuck, r.snapshot->>'safety' AS safety, "
            "       r.snapshot->>'department' AS department, r.snapshot->>'visit_type' AS visit_type, "
            "       (r.snapshot->>'changed_to_new')::boolean AS changed_to_new "
            "FROM workflow_runs r JOIN patient_profiles p ON p.id = r.patient_id "
            "WHERE r.id = :run_id AND p.user_id = :user_id"
        ),
        {"run_id": run_id, "user_id": user_id},
    ).mappings().one_or_none()
