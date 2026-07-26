"""The coordinator: the hub that hands an ordinary request to the agents it needs, one at a time.

On its first turn it asks the LLM for the patient's intent and a plan (which agents, in order).
Every agent reports back here; on later turns plain code hands the request to the next agent in the
plan, and finishes when none are left. The LLM is asked once, and each agent runs at most once,
so the request can't loop.
"""

import logging

from langgraph.runtime import Runtime

from app.agents.coordinator.prompt import PROMPT_VERSION, SYSTEM_PROMPT
from app.agents.coordinator.schema import CoordinatorPlan
from app.config import Settings
from app.graph.state import RequestState, WorkflowContext
from app.llm.mask import mask
from app.llm.structured import ask_structured

log = logging.getLogger(__name__)


def coordinate(state: RequestState, runtime: Runtime[WorkflowContext]) -> dict:
    """First turn: plan with the LLM. Later turns: follow the plan, then finish."""
    if "coordinator" in state:
        return next_agent(state["plan"])

    settings = runtime.context.settings
    llm_meta = {"model": settings.llm_model, "prompt_version": PROMPT_VERSION}
    try:
        answer, tokens = ask_llm(mask(state["request_text"], state["patient_name"]), settings)
    except Exception as error:  # No API key, a timeout, OpenRouter down, or an answer that doesn't fit the form.
        log.exception("The coordinator LLM failed for run %s", state["run_id"])
        coordinator = {"result": "FAILED", "reason": "The coordinator could not run, so a person needs to handle this request."}
        return {"coordinator": coordinator, "next_agent": "finish", "plan": [], "llm_meta": llm_meta | {"error": type(error).__name__}}

    plan = list(dict.fromkeys(answer.plan))  # each agent once, in the order given
    coordinator = {"result": "PLANNED", "intent": answer.intent, "plan": plan, "reason": answer.reason}
    return {"coordinator": coordinator, **next_agent(plan), "llm_meta": llm_meta | tokens}


def next_agent(plan: list[str]) -> dict:
    """Hand the request to the next agent in the plan, or finish when none are left."""
    if plan:
        return {"next_agent": plan[0], "plan": plan[1:]}
    return {"next_agent": "finish", "plan": []}


def ask_llm(masked_text: str, settings: Settings) -> tuple[CoordinatorPlan, dict]:
    """The LLM's plan for an already masked request, and the tokens it used. Raises if it can't answer."""
    return ask_structured(settings, CoordinatorPlan, SYSTEM_PROMPT, masked_text)
