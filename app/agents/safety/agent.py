"""The safety agent: the first step of every request. For now it runs the red-flag rules only."""

from app.agents.safety.red_flags import check
from app.graph.state import RequestState


def safety_intake(state: RequestState) -> dict:
    """Check the request for emergencies and medical-advice questions before anything else happens."""
    flag = check(state["request_text"])
    if flag is None:
        return {"safety": {"category": "ADMIN", "rule_id": None, "reason": "No red flags found."}}
    return {"safety": {"category": flag.category, "rule_id": flag.rule_id, "reason": flag.reason}}
