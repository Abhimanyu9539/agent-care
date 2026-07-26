"""The coordinator's plan: what the patient wants, and which agents should handle it."""

from typing import Literal

from pydantic import BaseModel, Field


class CoordinatorPlan(BaseModel):
    """Your plan for this request: what the patient wants, and which agents should handle it, in order."""

    intent: Literal["BOOK", "RESCHEDULE", "CANCEL", "DOCUMENTS_ONLY", "STATUS"]
    # Only agents that exist can be named. More join this list as they are built.
    plan: list[Literal["routing"]] = Field(min_length=1, description="The agents to run, in order.")
    reason: str = Field(description="One short sentence saying why, without any personal details.")
