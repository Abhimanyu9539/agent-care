"""The form the LLM must fill in. Its answer is checked against it, so nothing else gets through."""

from typing import Literal

from pydantic import BaseModel, Field


class SafetyVerdict(BaseModel):
    """Sort a patient's request into one safety category."""

    category: Literal["EMERGENCY", "CLINICAL_ADVICE", "ADMIN"]
    reason: str = Field(description="One short sentence saying why, without any personal details.")
