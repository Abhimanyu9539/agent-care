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


def list_runs(db: Session, limit: int = 100) -> Sequence[RowMapping]:
    """The newest runs, with how each was decided.

    `safety` is the category, `safety_source` "rules" or "llm" (from the safety step), and `routing`
    the routing step's decision, or None when the request never reached routing.
    """
    return db.execute(
        text(
            "SELECT r.id, r.request_text, r.status, r.created_at, r.intent, p.full_name AS patient, "
            "       dep.name AS department, "
            "       r.snapshot->>'safety' AS safety, "
            "       safety_step.output->'safety'->>'source' AS safety_source, "
            "       routing_step.output->'routing' AS routing "
            "FROM workflow_runs r "
            "JOIN patient_profiles p ON p.id = r.patient_id "
            "LEFT JOIN departments dep ON dep.id = r.department_id "
            "LEFT JOIN workflow_steps safety_step ON safety_step.run_id = r.id AND safety_step.node = 'safety_intake' "
            "LEFT JOIN workflow_steps routing_step ON routing_step.run_id = r.id AND routing_step.node = 'route_request' "
            "ORDER BY r.created_at DESC, r.id DESC LIMIT :limit"
        ),
        {"limit": limit},
    ).mappings().all()


def list_steps(db: Session, run_id: int) -> Sequence[RowMapping]:
    """The steps the workflow ran for this run, in order."""
    return db.execute(
        text(
            "SELECT seq, agent, node, outcome, output, tool_calls, llm_meta, latency_ms, created_at "
            "FROM workflow_steps WHERE run_id = :id ORDER BY seq"
        ),
        {"id": run_id},
    ).mappings().all()


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
