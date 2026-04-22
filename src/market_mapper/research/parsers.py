"""Parser helpers for extracted content cleanup and normalization."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from bs4 import BeautifulSoup
import trafilatura


@dataclass(slots=True)
class ParsedPageContent:
    """Normalized content extracted from captured page HTML."""

    title: str | None
    snippet: str | None
    extracted_text: str
    word_count: int
    headings: list[str]


def extract_page_content(*, html: str, url: str, title: str | None = None) -> ParsedPageContent:
    """Extract readable page text plus a short snippet from raw HTML."""

    extracted_text = (
        trafilatura.extract(
            html,
            url=url,
            include_comments=False,
            include_tables=True,
            favor_recall=True,
        )
        or ""
    ).strip()
    soup = BeautifulSoup(html, "html.parser")
    resolved_title = title or _extract_title(soup)
    headings = [
        heading.get_text(" ", strip=True)
        for heading in soup.find_all(["h1", "h2"])[:8]
        if heading.get_text(" ", strip=True)
    ]
    if not extracted_text:
        extracted_text = _fallback_text(soup)
    snippet = build_snippet(extracted_text)
    return ParsedPageContent(
        title=resolved_title,
        snippet=snippet,
        extracted_text=extracted_text,
        word_count=len(extracted_text.split()),
        headings=headings,
    )


def extract_page_content_from_file(
    *,
    html_path: str | Path,
    url: str,
    title: str | None = None,
) -> ParsedPageContent:
    """Read a captured HTML file and normalize it into extracted content."""

    html = Path(html_path).read_text(encoding="utf-8")
    return extract_page_content(html=html, url=url, title=title)


def build_snippet(text: str, max_chars: int = 320) -> str | None:
    """Build a compact snippet from extracted page text."""

    normalized = " ".join(text.split())
    if not normalized:
        return None
    if len(normalized) <= max_chars:
        return normalized
    truncated = normalized[: max_chars - 1].rsplit(" ", 1)[0].strip()
    return f"{truncated}..."


def _extract_title(soup: BeautifulSoup) -> str | None:
    title_tag = soup.find("title")
    if title_tag is None:
        return None
    title = title_tag.get_text(" ", strip=True)
    return title or None


def _fallback_text(soup: BeautifulSoup) -> str:
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    return soup.get_text(" ", strip=True)
