"""The audit log: one row for every change, never holding personal details."""

from sqlalchemy import text
from sqlalchemy.orm import Session


def record(
    db: Session, *, actor_user_id: int, action: str, entity_type: str, entity_id: int, workflow_run_id: int | None
) -> None:
    """Add an audit event without committing, so it is saved together with the change it describes."""
    db.execute(
        text(
            "INSERT INTO audit_events (actor_user_id, action, entity_type, entity_id, workflow_run_id) "
            "VALUES (:actor_user_id, :action, :entity_type, :entity_id, :workflow_run_id)"
        ),
        {
            "actor_user_id": actor_user_id,
            "action": action,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "workflow_run_id": workflow_run_id,
        },
    )
