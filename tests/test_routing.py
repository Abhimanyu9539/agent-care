"""The routing agent's tool loop, with a scripted model in place of the LLM. No database or LLM needed."""

import json

import pytest
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import tool

from app.agents.routing.agent import call_with_tools


@tool
def list_departments() -> list[dict]:
    """Departments."""
    return [{"code": "cardiology"}, {"code": "ent"}]


@tool
def get_patient_history() -> list[dict]:
    """Visits."""
    return [{"department": "cardiology", "status": "COMPLETED"}]


class ScriptedModel:
    """Replies with the given messages in turn, and keeps what it was sent each time."""

    def __init__(self, *replies: AIMessage) -> None:
        self.replies = list(replies)
        self.sent: list[list] = []

    def invoke(self, messages: list) -> AIMessage:
        self.sent.append(list(messages))
        return self.replies.pop(0)


def _calls(*names_and_args) -> AIMessage:
    calls = [{"name": name, "args": args, "id": f"call-{name}"} for name, args in names_and_args]
    return AIMessage(content="", tool_calls=calls, usage_metadata={"input_tokens": 100, "output_tokens": 10, "total_tokens": 110})


def test_runs_the_tools_the_llm_asks_for_until_it_answers() -> None:
    verdict_args = {"department": "cardiology", "visit_type": "FOLLOW_UP", "confidence": 0.9, "reason": "Seen before."}
    model = ScriptedModel(
        _calls(("list_departments", {}), ("get_patient_history", {})),  # both tools in one reply
        _calls(("RoutingVerdict", verdict_args)),
    )

    verdict, tool_calls, tokens = call_with_tools(model, "Book my follow-up", [list_departments, get_patient_history])

    assert verdict.model_dump() == verdict_args
    assert [(c["tool"], c["result_ref"], c["ok"]) for c in tool_calls] == [
        ("list_departments", "2 found", True), ("get_patient_history", "1 found", True)
    ]
    assert tokens == {"tokens_in": 200, "tokens_out": 20}
    # The second time, the LLM was handed both tool results.
    results = [m for m in model.sent[1] if isinstance(m, ToolMessage)]
    assert [json.loads(m.content) for m in results] == [list_departments.invoke({}), get_patient_history.invoke({})]


def test_a_reply_without_a_tool_call_is_an_error() -> None:
    model = ScriptedModel(AIMessage(content="I think cardiology."))

    with pytest.raises(ValueError, match="without calling a tool"):
        call_with_tools(model, "Book my follow-up", [list_departments])
