"""Ask the LLM to fill in a form (a Pydantic model) instead of writing free text."""

from pydantic import BaseModel

from app.config import Settings
from app.llm.client import make_model


def ask_structured(settings: Settings, schema: type[BaseModel], system_prompt: str, text: str) -> tuple[BaseModel, dict]:
    """The LLM's answer as `schema`, and the tokens it used. Raises if the LLM fails or the answer doesn't fit."""
    model = make_model(settings).with_structured_output(schema, method="function_calling", include_raw=True)
    result = model.invoke([("system", system_prompt), ("human", text)])
    if result["parsed"] is None:
        raise ValueError(f"The LLM's answer did not fit the {schema.__name__} form.") from result["parsing_error"]
    usage = result["raw"].usage_metadata or {}
    return result["parsed"], {"tokens_in": usage.get("input_tokens"), "tokens_out": usage.get("output_tokens")}
