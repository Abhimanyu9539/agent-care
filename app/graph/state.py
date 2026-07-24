"""What the workflow carries from step to step: the shared notebook every node reads and adds to."""

from typing import NotRequired, TypedDict


class RequestState(TypedDict):
    run_id: int
    request_text: str
    patient_name: str  # only so it can be masked before the text goes to the LLM
    # Set by the safety step: {"category", "rule_id", "reason", "source": "rules" | "llm"}.
    # category is EMERGENCY, CLINICAL_ADVICE or ADMIN, or UNCHECKED when the LLM could not answer.
    safety: NotRequired[dict]
    # Set by a step that called the LLM: {"model", "prompt_version", "tokens_in", "tokens_out"}, or "error".
    llm_meta: NotRequired[dict]
