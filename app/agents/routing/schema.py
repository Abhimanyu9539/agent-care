"""The routing agent's final answer. The LLM gives it by calling RoutingVerdict as if it were a tool."""

from typing import Literal

from pydantic import BaseModel, Field


class RoutingVerdict(BaseModel):
    """Your final answer: which department should handle the request, and what the patient asks for."""

    department: str = Field(description="The code of one department from list_departments, such as cardiology.")
    visit_type: Literal["NEW", "FOLLOW_UP"] = Field(
        description="FOLLOW_UP if the patient asks for a follow-up or review after an earlier visit, otherwise NEW."
    )
    confidence: float = Field(ge=0, le=1, description="How sure you are about the department, from 0 to 1.")
    reason: str = Field(description="One short sentence saying why, without any personal details.")
