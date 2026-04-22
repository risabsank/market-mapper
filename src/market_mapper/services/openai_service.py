"""Shared OpenAI Responses API helpers for structured agent execution."""

from __future__ import annotations

import json
from typing import Any, TypeVar

from openai import OpenAI
from pydantic import BaseModel

from market_mapper.config.settings import get_settings

StructuredModel = TypeVar("StructuredModel", bound=BaseModel)


class OpenAIConfigurationError(RuntimeError):
    """Raised when OpenAI settings are missing or invalid."""


def get_openai_client() -> OpenAI:
    """Create an OpenAI client from environment-backed settings."""

    settings = get_settings()
    if not settings.openai_api_key:
        raise OpenAIConfigurationError(
            "OPENAI_API_KEY is not set. Export it before running Market Mapper."
        )
    return OpenAI(api_key=settings.openai_api_key)


def render_agent_input(*, task_description: str, context: dict[str, Any]) -> str:
    """Render a stable JSON payload for an agent call."""

    return json.dumps(
        {
            "task": task_description,
            "context": context,
        },
        indent=2,
        sort_keys=True,
        default=str,
    )


def generate_structured_output(
    *,
    response_model: type[StructuredModel],
    system_prompt: str,
    user_input: str,
    model: str | None = None,
    use_web_search: bool = False,
) -> StructuredModel:
    """Call the OpenAI Responses API and validate the structured result."""

    settings = get_settings()
    client = get_openai_client()

    request: dict[str, Any] = {
        "model": model or settings.openai_model,
        "instructions": system_prompt,
        "input": user_input,
        "reasoning": {"effort": settings.openai_reasoning_effort},
        "text": {
            "format": {
                "type": "json_schema",
                "name": response_model.__name__,
                "schema": response_model.model_json_schema(),
                "strict": True,
            }
        },
    }

    if use_web_search and settings.openai_enable_web_search:
        request["tools"] = [{"type": "web_search_preview"}]
        request["include"] = ["web_search_call.action.sources"]

    response = client.responses.create(**request)
    if not getattr(response, "output_text", None):
        raise RuntimeError("OpenAI response did not include structured output text.")
    return response_model.model_validate_json(response.output_text)

