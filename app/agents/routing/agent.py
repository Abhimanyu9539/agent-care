"""The routing agent: picks the department and the visit type for an ordinary request.

The LLM looks things up with tools, then answers with a RoutingVerdict. Code then checks that answer:
the department must exist and the confidence be high enough, or a person routes it instead.
A follow-up for a department the patient has never visited becomes a new visit.
"""

import json
import logging
import time

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool
from langgraph.runtime import Runtime

from app.agents.routing.prompt import PROMPT_VERSION, SYSTEM_PROMPT
from app.agents.routing.schema import RoutingVerdict
from app.config import Settings
from app.graph.state import RequestState, WorkflowContext
from app.llm.client import make_model
from app.llm.mask import mask
from app.services import appointment, department
from app.tools.routing import make_routing_tools

log = logging.getLogger(__name__)

MAX_ROUNDS = 5  # LLM replies per request: enough for both tools and the answer, with room to spare


def route_request(state: RequestState, runtime: Runtime[WorkflowContext]) -> dict:
    """Ask the LLM where the request goes, then check its answer against the database."""
    db, settings = runtime.context.db, runtime.context.settings
    llm_meta = {"model": settings.llm_model, "prompt_version": PROMPT_VERSION}
    tools = make_routing_tools(db, state["patient_id"])
    try:
        verdict, tool_calls, tokens = ask_llm(mask(state["request_text"], state["patient_name"]), tools, settings)
    except Exception as error:  # No API key, a timeout, OpenRouter down, or an answer that doesn't fit the form.
        log.exception("The routing LLM failed for run %s", state["run_id"])
        routing = {"result": "FAILED", "reason": "The routing agent could not run, so a person needs to route this request."}
        return {"routing": routing, "llm_meta": llm_meta | {"error": type(error).__name__}}

    routing = check_verdict(
        verdict,
        department.list_departments(db),
        appointment.list_patient_visits(db, state["patient_id"]),
        settings.routing_confidence_threshold,
    )
    return {"routing": routing, "tool_calls": tool_calls, "llm_meta": llm_meta | tokens}


def check_verdict(verdict: RoutingVerdict, departments, visits, threshold: float) -> dict:
    """Never trust the LLM blindly: check its answer against the departments and the patient's visits."""
    routing = verdict.model_dump()
    found = next((d for d in departments if d["code"] == verdict.department), None)
    if found is None or verdict.confidence < threshold:
        return routing | {"result": "LOW_CONFIDENCE"}

    visited = any(v["department"] == found["code"] and v["status"] == "COMPLETED" for v in visits)
    changed_to_new = verdict.visit_type == "FOLLOW_UP" and not visited
    return routing | {
        "result": "ROUTED",
        "department_id": found["id"],
        "department_name": found["name"],
        "visit_type": "NEW" if changed_to_new else verdict.visit_type,
        "changed_to_new": changed_to_new,
    }


def ask_llm(masked_text: str, tools: list[BaseTool], settings: Settings) -> tuple[RoutingVerdict, list[dict], dict]:
    """The LLM's verdict on an already masked request, the tools it called, and the tokens it used."""
    # tool_choice="any": every reply must call a tool, and RoutingVerdict counts as one.
    model = make_model(settings).bind_tools([*tools, RoutingVerdict], tool_choice="any")
    return call_with_tools(model, masked_text, tools)


def call_with_tools(model, masked_text: str, tools: list[BaseTool]) -> tuple[RoutingVerdict, list[dict], dict]:
    """The tool loop: the LLM asks for a tool, we run it and hand back the result, until it calls RoutingVerdict."""
    by_name = {t.name: t for t in tools}
    messages = [SystemMessage(SYSTEM_PROMPT), HumanMessage(masked_text)]
    tool_calls = []
    tokens = {"tokens_in": 0, "tokens_out": 0}

    for _ in range(MAX_ROUNDS):
        reply = model.invoke(messages)
        usage = reply.usage_metadata or {}
        tokens["tokens_in"] += usage.get("input_tokens", 0)
        tokens["tokens_out"] += usage.get("output_tokens", 0)
        if not reply.tool_calls:
            raise ValueError("The LLM replied without calling a tool.")
        messages.append(reply)

        for call in reply.tool_calls:
            if call["name"] == "RoutingVerdict":
                return RoutingVerdict(**call["args"]), tool_calls, tokens
            started = time.perf_counter()
            result = by_name[call["name"]].invoke(call["args"])
            tool_calls.append({
                "tool": call["name"],
                "args": call["args"],
                "ok": True,
                "ms": round((time.perf_counter() - started) * 1000),
                "result_ref": f"{len(result)} found",
            })
            messages.append(ToolMessage(json.dumps(result), tool_call_id=call["id"]))

    raise ValueError(f"The LLM gave no RoutingVerdict in {MAX_ROUNDS} replies.")
