"""What the workflow carries from step to step: the shared notebook every node reads and adds to.

Also what each run is given (its context): the settings and a database session.
"""

from dataclasses import dataclass
from typing import NotRequired, TypedDict

from sqlalchemy.orm import Session

from app.config import Settings


class RequestState(TypedDict):
    run_id: int
    request_text: str
    patient_id: int  # for the tools; never sent to the LLM
    patient_name: str  # only so it can be masked before the text goes to the LLM
    # Set by the safety step: {"category", "rule_id", "reason", "source": "rules" | "llm"}.
    # category is EMERGENCY, CLINICAL_ADVICE or ADMIN, or UNCHECKED when the LLM could not answer.
    safety: NotRequired[dict]
    # Set by the routing step: {"result": "ROUTED" | "LOW_CONFIDENCE" | "FAILED", "reason", ...}.
    # When ROUTED: "department_id", "department_name", "visit_type", and "changed_to_new" when the patient
    # asked for a follow-up but has never visited that department, so it became a new visit.
    routing: NotRequired[dict]
    # Set by a step that called the LLM: {"model", "prompt_version", "tokens_in", "tokens_out"}, or "error".
    llm_meta: NotRequired[dict]
    # Set by a step whose LLM called tools: [{"tool", "args", "ok", "ms", "result_ref"}].
    tool_calls: NotRequired[list]


@dataclass
class WorkflowContext:
    settings: Settings
    db: Session
