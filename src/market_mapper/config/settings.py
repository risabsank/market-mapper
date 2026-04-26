"""Application settings for Market Mapper."""

from __future__ import annotations

import os
import json
from pathlib import Path
from functools import lru_cache

from market_mapper.schemas.models.common import MarketMapperModel


class Settings(MarketMapperModel):
    """Environment-backed application settings."""

    openai_api_key: str | None = None
    openai_model: str = "gpt-5-mini"
    openai_reasoning_effort: str = "low"
    openai_enable_web_search: bool = True
    max_research_retries: int = 2
    auth_tokens: dict[str, str] = {}
    workflow_state_dir: str = str(Path("/tmp/market_mapper/state"))


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Load settings from environment variables."""

    raw_tokens = os.getenv("MARKET_MAPPER_AUTH_TOKENS", "")
    token_map = {"dev-token": "demo-user"}
    if raw_tokens.strip():
        token_map = json.loads(raw_tokens)
    return Settings(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-5-mini"),
        openai_reasoning_effort=os.getenv("OPENAI_REASONING_EFFORT", "low"),
        openai_enable_web_search=(
            os.getenv("OPENAI_ENABLE_WEB_SEARCH", "true").lower() in {"1", "true", "yes"}
        ),
        max_research_retries=max(0, int(os.getenv("MARKET_MAPPER_MAX_RESEARCH_RETRIES", "2"))),
        auth_tokens={str(token): str(user_id) for token, user_id in token_map.items()},
        workflow_state_dir=os.getenv("MARKET_MAPPER_STATE_DIR", str(Path("/tmp/market_mapper/state"))),
    )
