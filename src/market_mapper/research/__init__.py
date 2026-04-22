"""Research utilities for fetching, parsing, and normalization."""

from market_mapper.research.fetchers import (
    PageCapture,
    ResearchTarget,
    build_research_targets,
    capture_page_snapshot,
    normalize_url,
)
from market_mapper.research.parsers import (
    ParsedPageContent,
    build_snippet,
    extract_page_content,
    extract_page_content_from_file,
)

__all__ = [
    "PageCapture",
    "ParsedPageContent",
    "ResearchTarget",
    "build_research_targets",
    "build_snippet",
    "capture_page_snapshot",
    "extract_page_content",
    "extract_page_content_from_file",
    "normalize_url",
]
