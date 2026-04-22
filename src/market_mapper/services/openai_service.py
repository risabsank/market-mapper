"""Shared OpenAI Responses API helpers for structured agent execution."""

from __future__ import annotations

import json
import logging
from typing import Any, TypeVar

from openai import OpenAI
from pydantic import BaseModel, ValidationError

from market_mapper.config.settings import get_settings

StructuredModel = TypeVar("StructuredModel", bound=BaseModel)
logger = logging.getLogger("market_mapper.openai")


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
    """Call the OpenAI Responses API and validate JSON locally.

    We intentionally avoid OpenAI's strict response_format schema path here.
    The Market Mapper domain models contain flexible fields that are valid
    Pydantic but are brittle under strict OpenAI JSON Schema validation.
    For product reliability, we ask the model for JSON only and validate the
    result locally against the same Pydantic model.
    """

    settings = get_settings()
    client = get_openai_client()
    return _generate_with_json_validation(
        client=client,
        response_model=response_model,
        system_prompt=system_prompt,
        user_input=user_input,
        model=model or settings.openai_model,
        reasoning_effort=settings.openai_reasoning_effort,
        use_web_search=use_web_search and settings.openai_enable_web_search,
    )


def _generate_with_json_validation(
    *,
    client: OpenAI,
    response_model: type[StructuredModel],
    system_prompt: str,
    user_input: str,
    model: str,
    reasoning_effort: str,
    use_web_search: bool,
) -> StructuredModel:
    """Request JSON text from OpenAI, then validate with Pydantic locally."""

    request: dict[str, Any] = {
        "model": model,
        "instructions": (
            f"{system_prompt}\n\n"
            "Return only valid JSON. Do not include markdown fences, commentary, or prose outside the JSON object."
        ),
        "input": (
            f"{user_input}\n\n"
            "Target JSON schema for local validation:\n"
            f"{json.dumps(response_model.model_json_schema(), indent=2, sort_keys=True, default=str)}"
        ),
        "reasoning": {"effort": reasoning_effort},
    }
    if use_web_search:
        request["tools"] = [{"type": "web_search_preview"}]
        request["include"] = ["web_search_call.action.sources"]

    logger.info(
        "OpenAI JSON call starting: model=%s schema=%s web_search=%s",
        model,
        response_model.__name__,
        bool(use_web_search),
    )
    try:
        response = client.responses.create(**request)
    except Exception:
        logger.exception(
            "OpenAI JSON call failed: model=%s schema=%s",
            model,
            response_model.__name__,
        )
        raise
    if not getattr(response, "output_text", None):
        raise RuntimeError("OpenAI JSON response did not include output_text.")
    logger.info(
        "OpenAI JSON call completed: model=%s schema=%s",
        model,
        response_model.__name__,
    )
    try:
        return response_model.model_validate_json(response.output_text)
    except ValidationError as exc:
        if _only_has_extra_field_errors(exc):
            logger.warning(
                "OpenAI JSON for %s included unsupported extra fields; retrying validation with extras ignored.",
                response_model.__name__,
            )
            return response_model.model_validate_json(response.output_text, extra="ignore")
        raise


def _only_has_extra_field_errors(exc: ValidationError) -> bool:
    """Return true when every validation error is only about forbidden extra fields."""

    errors = exc.errors()
    return bool(errors) and all(error.get("type") == "extra_forbidden" for error in errors)
