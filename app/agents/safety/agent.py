"""The safety agent: the first step of every request.

The red-flag rules check first. Only when they find nothing does the LLM read the request, with
personal details masked. If the LLM can't answer, the request is marked UNCHECKED and goes to staff.
"""

import logging

from langgraph.runtime import Runtime

from app.agents.safety.prompt import PROMPT_VERSION, SYSTEM_PROMPT
from app.agents.safety.red_flags import check
from app.agents.safety.schema import SafetyVerdict
from app.config import Settings
from app.graph.state import RequestState, WorkflowContext
from app.llm.client import make_model
from app.llm.mask import mask

log = logging.getLogger(__name__)


def safety_intake(state: RequestState, runtime: Runtime[WorkflowContext]) -> dict:
    """Check the request for emergencies and medical-advice questions before anything else happens."""
    flag = check(state["request_text"])
    if flag is not None:
        return {"safety": {"category": flag.category, "rule_id": flag.rule_id, "reason": flag.reason, "source": "rules"}}

    settings = runtime.context.settings
    llm_meta = {"model": settings.llm_model, "prompt_version": PROMPT_VERSION}
    try:
        verdict, tokens = ask_llm(mask(state["request_text"], state["patient_name"]), settings)
    except Exception as error:  # No API key, a timeout, OpenRouter down, or an answer that doesn't fit the form.
        log.exception("The safety LLM failed for run %s", state["run_id"])
        unchecked = {
            "category": "UNCHECKED",
            "rule_id": None,
            "reason": "The safety check could not run, so a person needs to check this request.",
            "source": "llm",
        }
        return {"safety": unchecked, "llm_meta": llm_meta | {"error": type(error).__name__}}

    safety = {"category": verdict.category, "rule_id": None, "reason": verdict.reason, "source": "llm"}
    return {"safety": safety, "llm_meta": llm_meta | tokens}


def ask_llm(masked_text: str, settings: Settings) -> tuple[SafetyVerdict, dict]:
    """The LLM's verdict on an already masked request, and the tokens it used. Raises if it can't answer."""
    model = make_model(settings).with_structured_output(SafetyVerdict, method="function_calling", include_raw=True)
    result = model.invoke([("system", SYSTEM_PROMPT), ("human", masked_text)])
    if result["parsed"] is None:
        raise ValueError("The LLM's answer did not fit the SafetyVerdict form.") from result["parsing_error"]
    usage = result["raw"].usage_metadata or {}
    return result["parsed"], {"tokens_in": usage.get("input_tokens"), "tokens_out": usage.get("output_tokens")}
