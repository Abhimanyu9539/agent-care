"""Runs a request through the workflow graph, saves each step, then saves the outcome."""

import time

from sqlalchemy import RowMapping
from sqlalchemy.orm import Session, sessionmaker

from app.graph.builder import GRAPH
from app.services import audit, escalation, workflow

# Which agent each graph node belongs to, for the timeline.
AGENTS = {"safety_intake": "safety"}


def run_request(session_factory: sessionmaker[Session], run_id: int) -> None:
    """Run the workflow for one saved request.

    Runs as a background task after the patient's request is saved, so it opens its own database session.
    """
    with session_factory() as db:
        run = workflow.get_run(db, run_id)
        state = {"run_id": run_id, "request_text": run["request_text"]}
        input_summary = {"text_chars": len(run["request_text"])}  # counts only, never the text

        started = time.perf_counter()
        # "updates" yields {node: what it returned} as each node finishes.
        for seq, update in enumerate(GRAPH.stream(state, stream_mode="updates"), start=1):
            [(node, output)] = update.items()
            latency_ms = round((time.perf_counter() - started) * 1000)
            workflow.add_step(
                db, run_id, seq=seq, agent=AGENTS[node], node=node,
                input_summary=input_summary, output=output, latency_ms=latency_ms,
            )
            state |= output
            started = time.perf_counter()

        _save_outcome(db, run, state["safety"])


def _save_outcome(db: Session, run: RowMapping, safety: dict) -> None:
    """Emergency: hand to staff. Clinical question: decline. Anything else: done, for now."""
    category = safety["category"]
    if category == "EMERGENCY":
        escalation_id = escalation.open_escalation(
            db, run, escalation_type="EMERGENCY", priority="URGENT", reason=safety["reason"], agent="safety"
        )
        workflow.set_status(
            db, run, "ESCALATED", current_step="escalate", agent="safety",
            snapshot={"safety": category, "escalation_id": escalation_id},
        )
    elif category == "CLINICAL_ADVICE":
        # Declined: the patient is asked to book a visit instead. Nobody needs to follow up.
        audit.record(
            db,
            actor_user_id=run["created_by"],
            actor_agent="safety",
            action="safety.blocked_input",
            entity_type="workflow_run",
            entity_id=run["id"],
            workflow_run_id=run["id"],
            metadata={"rule_id": safety["rule_id"]},
        )
        workflow.set_status(
            db, run, "COMPLETED", current_step="declined", agent="safety",
            snapshot={"safety": category, "rule_id": safety["rule_id"]},
        )
    else:
        workflow.set_status(db, run, "COMPLETED", current_step="finish", agent="safety", snapshot={"safety": category})
    db.commit()
