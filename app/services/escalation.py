"""Plain-SQL queries for escalations: the cases handed to staff."""

from collections.abc import Sequence

from sqlalchemy import RowMapping, text
from sqlalchemy.orm import Session

from app.services import audit


def list_open_escalations(db: Session) -> Sequence[RowMapping]:
    """Open cases, most urgent first, then the longest waiting.

    `priority` is a Postgres enum declared as URGENT, HIGH, NORMAL, so ORDER BY sorts it in that order.
    """
    return db.execute(
        text(
            "SELECT e.id, e.type, e.priority, e.reason, e.workflow_run_id, p.full_name AS patient, "
            "       floor(extract(epoch FROM now() - e.created_at) / 60)::int AS waiting_minutes "
            "FROM escalations e JOIN patient_profiles p ON p.id = e.patient_id "
            "WHERE e.status = 'OPEN' "
            "ORDER BY e.priority, e.created_at, e.id"
        )
    ).mappings().all()


def open_escalation(
    db: Session,
    run: RowMapping,
    *,
    escalation_type: str,
    priority: str,
    reason: str,
    agent: str,
) -> int:
    """Hand a run to staff: add an OPEN case with its audit event. Does not commit. Returns the case id."""
    escalation_id = db.execute(
        text(
            "INSERT INTO escalations (workflow_run_id, patient_id, type, priority, reason) "
            "VALUES (:run_id, :patient_id, :type, :priority, :reason) "
            "RETURNING id"
        ),
        {
            "run_id": run["id"],
            "patient_id": run["patient_id"],
            "type": escalation_type,
            "priority": priority,
            "reason": reason,
        },
    ).scalar_one()
    audit.record(
        db,
        actor_user_id=run["created_by"],
        actor_agent=agent,
        action="escalation.open",
        entity_type="escalation",
        entity_id=escalation_id,
        workflow_run_id=run["id"],
        metadata={"type": escalation_type, "priority": priority},
    )
    return escalation_id


def resolve_escalation(db: Session, escalation_id: int, staff_user_id: int) -> bool:
    """Mark an open case resolved by this staff member, with its audit event.

    Returns False when there is no open case with that id. Only one of two staff clicking
    Resolve at the same moment can win, because the update only touches an OPEN row.
    """
    row = db.execute(
        text(
            "UPDATE escalations SET status = 'RESOLVED', reviewed_by = :staff_user_id, reviewed_at = now() "
            "WHERE id = :id AND status = 'OPEN' "
            "RETURNING workflow_run_id"
        ),
        {"id": escalation_id, "staff_user_id": staff_user_id},
    ).one_or_none()
    if row is None:
        return False
    audit.record(
        db,
        actor_user_id=staff_user_id,
        action="escalation.resolve",
        entity_type="escalation",
        entity_id=escalation_id,
        workflow_run_id=row.workflow_run_id,
    )
    db.commit()
    return True
