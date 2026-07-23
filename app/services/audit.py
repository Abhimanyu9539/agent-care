"""The audit log: one row for every change, never holding personal details."""

import json

from sqlalchemy import text
from sqlalchemy.orm import Session


def record(
    db: Session,
    *,
    actor_user_id: int,
    action: str,
    entity_type: str,
    entity_id: int,
    workflow_run_id: int | None,
    actor_agent: str | None = None,
    metadata: dict | None = None,
) -> None:
    """Add an audit event without committing, so it is saved together with the change it describes.

    `actor_agent` is set when an agent acted for the user. `metadata` holds ids and codes only.
    """
    db.execute(
        text(
            "INSERT INTO audit_events "
            "  (actor_user_id, actor_agent, action, entity_type, entity_id, workflow_run_id, metadata) "
            "VALUES (:actor_user_id, :actor_agent, :action, :entity_type, :entity_id, :workflow_run_id, "
            "        CAST(:metadata AS jsonb))"
        ),
        {
            "actor_user_id": actor_user_id,
            "actor_agent": actor_agent,
            "action": action,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "workflow_run_id": workflow_run_id,
            "metadata": json.dumps(metadata or {}),
        },
    )
