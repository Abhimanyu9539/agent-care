"""Runs a request through the workflow graph, saves each step, then saves the outcome.

If anything unexpected goes wrong, the run is marked FAILED, so it never stays RUNNING; staff can retry it.
"""

import logging
import time

from sqlalchemy import RowMapping
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings
from app.graph.builder import GRAPH
from app.graph.state import WorkflowContext
from app.services import audit, escalation, workflow

log = logging.getLogger(__name__)

# Which agent each graph node belongs to, for the timeline.
AGENTS = {"safety_intake": "safety", "coordinator": "coordinator", "route_request": "routing"}


def run_request(session_factory: sessionmaker[Session], settings: Settings, run_id: int) -> None:
    """Run the workflow for one saved request, from the start.

    Runs as a background task after the patient's request is saved, or after staff press Retry,
    so it opens its own database session.
    """
    with session_factory() as db:
        steps_done = []
        try:
            _run(db, settings, run_id, steps_done)
        except Exception as error:  # a bug, the database dropping out, anything the agents did not handle
            log.exception("Run %s failed", run_id)
            db.rollback()
            # Only the error's type and the last step that finished: an error's text can hold patient data.
            after = steps_done[-1] if steps_done else "the start"
            failure = {"code": type(error).__name__, "message": f"Stopped unexpectedly after {after}."}
            workflow.mark_failed(db, workflow.get_run(db, run_id), failure)
            db.commit()


def _run(db: Session, settings: Settings, run_id: int, steps_done: list[str]) -> None:
    """Run the graph, saving each step as it finishes and adding its node to `steps_done`, then save the outcome."""
    run = workflow.get_run(db, run_id)
    state = {
        "run_id": run_id,
        "request_text": run["request_text"],
        "patient_id": run["patient_id"],
        "patient_name": run["patient"],
    }
    # Counts only, never the text. The attempt tells a retry's steps apart from earlier ones.
    input_summary = {"text_chars": len(run["request_text"]), "attempt": run["attempt"]}
    context = WorkflowContext(settings=settings, db=db)
    first_seq = workflow.next_seq(db, run_id)  # a retry carries on after the earlier attempts' steps
    # How the run shows up in LangSmith: one trace per attempt, found by the run id the staff console shows.
    config = {"run_name": "workflow", "metadata": {"run_id": run_id, "attempt": run["attempt"]}}

    started = time.perf_counter()
    # "updates" yields {node: what it returned} as each node finishes.
    for seq, update in enumerate(GRAPH.stream(state, config, context=context, stream_mode="updates"), start=first_seq):
        [(node, output)] = update.items()
        latency_ms = round((time.perf_counter() - started) * 1000)
        # The LLM details and tool calls have their own columns; the rest is the step's output.
        step_output = {key: value for key, value in output.items() if key not in ("llm_meta", "tool_calls")}
        llm_meta = output.get("llm_meta")
        workflow.add_step(
            db, run_id, seq=seq, agent=AGENTS[node], node=node,
            outcome="FAILED" if llm_meta and "error" in llm_meta else "OK",
            input_summary=input_summary, output=step_output,
            tool_calls=output.get("tool_calls", []), llm_meta=llm_meta, latency_ms=latency_ms,
        )
        steps_done.append(node)
        state |= output
        started = time.perf_counter()

    _save_outcome(db, run, state)


def _save_outcome(db: Session, run: RowMapping, state: dict) -> None:
    """Emergency or not checked: hand to staff. Clinical question: decline. Ordinary request: save the plan's results."""
    safety = state["safety"]
    category = safety["category"]
    if category in ("EMERGENCY", "UNCHECKED"):
        # An unchecked request might be an emergency too, so a person looks at it soon.
        escalation_type, priority = ("EMERGENCY", "URGENT") if category == "EMERGENCY" else ("SYSTEM_FAILURE", "HIGH")
        _escalate(db, run, escalation_type, priority, safety["reason"], agent="safety", snapshot={"safety": category})
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
            metadata={"source": safety["source"], "rule_id": safety["rule_id"]},
        )
        workflow.set_status(
            db, run, "COMPLETED", current_step="declined", agent="safety",
            snapshot={"safety": category, "rule_id": safety["rule_id"]},
        )
    elif state["coordinator"]["result"] == "FAILED":
        reason = state["coordinator"]["reason"]
        _escalate(db, run, "SYSTEM_FAILURE", "NORMAL", reason, agent="coordinator", snapshot={"safety": "ADMIN"})
    else:
        workflow.set_intent(db, run["id"], state["coordinator"]["intent"])
        _save_routing(db, run, state["routing"])
    db.commit()


def _save_routing(db: Session, run: RowMapping, routing: dict) -> None:
    """Routed: save the department and finish. Unsure or failed: a person routes it by hand."""
    if routing["result"] == "ROUTED":
        workflow.set_department(db, run["id"], routing["department_id"])
        workflow.set_status(
            db, run, "COMPLETED", current_step="routed", agent="routing",
            snapshot={
                "safety": "ADMIN",
                "department": routing["department_name"],
                "visit_type": routing["visit_type"],
                "changed_to_new": routing["changed_to_new"],
            },
        )
    elif routing["result"] == "LOW_CONFIDENCE":
        reason = f"Not sure which department. Best guess: {routing['department']} ({routing['confidence']:.0%})."
        _escalate(db, run, "LOW_CONFIDENCE", "NORMAL", reason, agent="routing", snapshot={"safety": "ADMIN"})
    else:
        _escalate(db, run, "SYSTEM_FAILURE", "NORMAL", routing["reason"], agent="routing", snapshot={"safety": "ADMIN"})


def _escalate(
    db: Session, run: RowMapping, escalation_type: str, priority: str, reason: str, *, agent: str, snapshot: dict
) -> None:
    """Hand the run to staff: open a case and mark the run ESCALATED."""
    escalation_id = escalation.open_escalation(
        db, run, escalation_type=escalation_type, priority=priority, reason=reason, agent=agent
    )
    workflow.set_status(
        db, run, "ESCALATED", current_step="escalate", agent=agent, snapshot=snapshot | {"escalation_id": escalation_id}
    )
