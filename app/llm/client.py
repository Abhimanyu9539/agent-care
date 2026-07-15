"""The chat model every agent uses. All calls go through OpenRouter."""

from langchain_openai import ChatOpenAI

from app.config import Settings

OPEN_ROUTER_URL = "https://openrouter.ai/api/v1"


class LLMNotConfigured(Exception):
    """OPEN_ROUTER_API_KEY is not set, so no LLM call can be made."""


def make_model(settings: Settings) -> ChatOpenAI:
    """A chat model for `settings.llm_model`, reached through OpenRouter's OpenAI-compatible API."""
    if settings.open_router_api_key is None:
        raise LLMNotConfigured("OPEN_ROUTER_API_KEY is not set")
    return ChatOpenAI(
        model=settings.llm_model,
        api_key=settings.open_router_api_key,
        base_url=OPEN_ROUTER_URL,
        timeout=settings.llm_timeout_seconds,
        max_retries=settings.llm_max_retries,
    )
