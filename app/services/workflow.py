"""Plain-SQL queries for workflow runs and their steps: the agent timeline."""

import json
from collections.abc import Sequence

from sqlalchemy import RowMapping, text
from sqlalchemy.orm import Session

from app.services import audit


def get_run(db: Session, run_id: int) -> RowMapping | None:
    """The run with the patient's name, or None."""
    return db.execute(
        text(
            "SELECT r.id, r.patient_id, r.created_by, r.request_text, r.status, r.current_step, r.snapshot, "
            "       r.error, r.created_at, r.updated_at, p.full_name AS patient "
            "FROM workflow_runs r JOIN patient_profiles p ON p.id = r.patient_id "
            "WHERE r.id = :id"
        ),
        {"id": run_id},
    ).mappings().one_or_none()


def list_steps(db: Session, run_id: int) -> Sequence[RowMapping]:
    """The steps the workflow ran for this run, in order."""
    return db.execute(
        text(
            "SELECT seq, agent, node, outcome, output, tool_calls, latency_ms, created_at "
            "FROM workflow_steps WHERE run_id = :id ORDER BY seq"
        ),
        {"id": run_id},
    ).mappings().all()


def add_step(
    db: Session, run_id: int, *, seq: int, agent: str, node: str, input_summary: dict, output: dict, latency_ms: int
) -> None:
    """Save one finished step. Committed at once, so the timeline shows each step as it happens."""
    db.execute(
        text(
            "INSERT INTO workflow_steps (run_id, seq, agent, node, outcome, input_summary, output, latency_ms) "
            "VALUES (:run_id, :seq, :agent, :node, 'OK', CAST(:input_summary AS jsonb), CAST(:output AS jsonb), "
            "        :latency_ms)"
        ),
        {
            "run_id": run_id,
            "seq": seq,
            "agent": agent,
            "node": node,
            "input_summary": json.dumps(input_summary),
            "output": json.dumps(output),
            "latency_ms": latency_ms,
        },
    )
    db.commit()


def set_status(db: Session, run: RowMapping, status: str, *, current_step: str, snapshot: dict, agent: str) -> None:
    """Move the run to a new status, with its audit event. Does not commit."""
    db.execute(
        text(
            "UPDATE workflow_runs SET status = :status, current_step = :current_step, "
            "  snapshot = CAST(:snapshot AS jsonb), updated_at = now(), "
            "  completed_at = CASE WHEN :completed THEN now() END "
            "WHERE id = :id"
        ),
        {
            "id": run["id"],
            "status": status,
            "current_step": current_step,
            "snapshot": json.dumps(snapshot),
            "completed": status == "COMPLETED",
        },
    )
    audit.record(
        db,
        actor_user_id=run["created_by"],
        actor_agent=agent,
        action="workflow.status_change",
        entity_type="workflow_run",
        entity_id=run["id"],
        workflow_run_id=run["id"],
        metadata={"from": run["status"], "to": status},
    )
