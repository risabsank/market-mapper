"""Application settings for Market Mapper."""

from __future__ import annotations

import os
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
    workflow_state_dir: str = str(Path("/tmp/market_mapper/state"))


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Load settings from environment variables."""

    return Settings(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-5-mini"),
        openai_reasoning_effort=os.getenv("OPENAI_REASONING_EFFORT", "low"),
        openai_enable_web_search=(
            os.getenv("OPENAI_ENABLE_WEB_SEARCH", "true").lower() in {"1", "true", "yes"}
        ),
        max_research_retries=max(0, int(os.getenv("MARKET_MAPPER_MAX_RESEARCH_RETRIES", "2"))),
        workflow_state_dir=os.getenv("MARKET_MAPPER_STATE_DIR", str(Path("/tmp/market_mapper/state"))),
    )
