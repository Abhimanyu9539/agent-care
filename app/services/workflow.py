"""Plain-SQL queries for workflow runs and their steps: the agent timeline."""

import json
from collections.abc import Sequence

from sqlalchemy import RowMapping, text
from sqlalchemy.orm import Session

from app.services import audit

# A run is stuck when it is RUNNING but has made no progress for 10 minutes, such as when the server
# restarted mid-run and its background job was lost. Staff can retry it, like a FAILED run.
STUCK = "(r.status = 'RUNNING' AND r.updated_at < now() - interval '10 minutes')"
RETRYABLE = f"(r.status = 'FAILED' OR {STUCK})"


def get_run(db: Session, run_id: int) -> RowMapping | None:
    """The run with the patient's name, or None."""
    return db.execute(
        text(
            "SELECT r.id, r.patient_id, r.created_by, r.request_text, r.status, r.current_step, r.snapshot, "
            f"      r.error, r.attempt, r.created_at, r.updated_at, p.full_name AS patient, {STUCK} AS stuck "
            "FROM workflow_runs r JOIN patient_profiles p ON p.id = r.patient_id "
            "WHERE r.id = :id"
        ),
        {"id": run_id},
    ).mappings().one_or_none()


def list_runs(db: Session, limit: int = 100) -> Sequence[RowMapping]:
    """The newest runs, with how each was decided.

    `safety` is the category, `safety_source` "rules" or "llm" (from the safety step), and `routing`
    the routing step's decision, or None when the request never reached routing. A retried run has
    these steps once per attempt, so the latest one counts.
    """
    latest = "(SELECT output FROM workflow_steps s WHERE s.run_id = r.id AND s.node = '{}' ORDER BY s.seq DESC LIMIT 1)"
    return db.execute(
        text(
            "SELECT r.id, r.request_text, r.status, r.created_at, r.intent, p.full_name AS patient, "
            f"      dep.name AS department, {STUCK} AS stuck, "
            "       r.snapshot->>'safety' AS safety, "
            f"      {latest.format('safety_intake')}->'safety'->>'source' AS safety_source, "
            f"      {latest.format('route_request')}->'routing' AS routing "
            "FROM workflow_runs r "
            "JOIN patient_profiles p ON p.id = r.patient_id "
            "LEFT JOIN departments dep ON dep.id = r.department_id "
            "ORDER BY r.created_at DESC, r.id DESC LIMIT :limit"
        ),
        {"limit": limit},
    ).mappings().all()


def list_steps(db: Session, run_id: int) -> Sequence[RowMapping]:
    """The steps the workflow ran for this run, in order. A retried run lists every attempt's steps."""
    return db.execute(
        text(
            "SELECT seq, agent, node, outcome, output, tool_calls, llm_meta, latency_ms, created_at, "
            "       (input_summary->>'attempt')::int AS attempt "
            "FROM workflow_steps WHERE run_id = :id ORDER BY seq"
        ),
        {"id": run_id},
    ).mappings().all()


def next_seq(db: Session, run_id: int) -> int:
    """The number for the run's next step: 1, or one more than the last step of an earlier attempt."""
    return db.execute(
        text("SELECT coalesce(max(seq), 0) + 1 FROM workflow_steps WHERE run_id = :id"), {"id": run_id}
    ).scalar_one()


def add_step(
    db: Session,
    run_id: int,
    *,
    seq: int,
    agent: str,
    node: str,
    outcome: str,
    input_summary: dict,
    output: dict,
    tool_calls: list[dict],
    llm_meta: dict | None,
    latency_ms: int,
) -> None:
    """Save one finished step. Committed at once, so the timeline shows each step as it happens.

    `llm_meta` is set when the step called the LLM: model, prompt version and tokens, never the text.
    `tool_calls` lists the tools its LLM called, with counts of what they returned, never the rows.
    """
    db.execute(
        text(
            "INSERT INTO workflow_steps "
            "  (run_id, seq, agent, node, outcome, input_summary, output, tool_calls, llm_meta, latency_ms) "
            "VALUES (:run_id, :seq, :agent, :node, :outcome, CAST(:input_summary AS jsonb), CAST(:output AS jsonb), "
            "        CAST(:tool_calls AS jsonb), CAST(:llm_meta AS jsonb), :latency_ms)"
        ),
        {
            "run_id": run_id,
            "seq": seq,
            "agent": agent,
            "node": node,
            "outcome": outcome,
            "input_summary": json.dumps(input_summary),
            "output": json.dumps(output),
            "tool_calls": json.dumps(tool_calls),
            "llm_meta": json.dumps(llm_meta) if llm_meta is not None else None,
            "latency_ms": latency_ms,
        },
    )
    # Progress: a run whose updated_at moves on is not stuck.
    db.execute(text("UPDATE workflow_runs SET updated_at = now() WHERE id = :id"), {"id": run_id})
    db.commit()


def set_intent(db: Session, run_id: int, intent: str) -> None:
    """Save what the patient wants (BOOK, RESCHEDULE, CANCEL, DOCUMENTS_ONLY, STATUS). Does not commit."""
    db.execute(text("UPDATE workflow_runs SET intent = :intent WHERE id = :id"), {"id": run_id, "intent": intent})


def set_department(db: Session, run_id: int, department_id: int) -> None:
    """Save which department the run was routed to. Does not commit."""
    db.execute(
        text("UPDATE workflow_runs SET department_id = :department_id WHERE id = :id"),
        {"id": run_id, "department_id": department_id},
    )


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


def mark_failed(db: Session, run: RowMapping, error: dict) -> None:
    """Mark the run FAILED with what went wrong ({"code", "message"}, never patient text). Does not commit."""
    db.execute(
        text("UPDATE workflow_runs SET status = 'FAILED', error = CAST(:error AS jsonb), updated_at = now() WHERE id = :id"),
        {"id": run["id"], "error": json.dumps(error)},
    )
    audit.record(
        db,
        actor_user_id=run["created_by"],
        actor_agent="workflow",
        action="workflow.status_change",
        entity_type="workflow_run",
        entity_id=run["id"],
        workflow_run_id=run["id"],
        metadata={"from": run["status"], "to": "FAILED", "error": error["code"]},
    )


def start_retry(db: Session, run: RowMapping, staff_user_id: int) -> int | None:
    """Reset a failed or stuck run so it can run again from the start, with its audit event.

    Returns the new attempt number, or None when the run is neither failed nor stuck. The earlier
    attempts' steps stay, as history.
    """
    attempt = db.execute(
        text(
            "UPDATE workflow_runs r SET status = 'RUNNING', attempt = r.attempt + 1, error = NULL, "
            "  current_step = 'safety_intake', snapshot = '{}', intent = NULL, department_id = NULL, "
            "  completed_at = NULL, updated_at = now() "
            f"WHERE r.id = :id AND {RETRYABLE} "
            "RETURNING r.attempt"
        ),
        {"id": run["id"]},
    ).scalar_one_or_none()
    if attempt is None:
        return None
    audit.record(
        db,
        actor_user_id=staff_user_id,
        action="workflow.retry",
        entity_type="workflow_run",
        entity_id=run["id"],
        workflow_run_id=run["id"],
        metadata={"from": run["status"], "attempt": attempt},
    )
    db.commit()
    return attempt
