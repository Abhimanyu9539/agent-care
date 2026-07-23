"""What the workflow carries from step to step: the shared notebook every node reads and adds to."""

from typing import NotRequired, TypedDict


class RequestState(TypedDict):
    run_id: int
    request_text: str
    # Set by the safety step: {"category": "EMERGENCY" | "CLINICAL_ADVICE" | "ADMIN", "rule_id", "reason"}.
    safety: NotRequired[dict]
