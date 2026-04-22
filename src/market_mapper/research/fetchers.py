"""Fetch helpers for browser-backed site and source retrieval."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse, urlunparse

from market_mapper.schemas.models import CompanyCandidate, ResearchPlan, SourceDocument


@dataclass(slots=True)
class ResearchTarget:
    """One page target to capture during sandbox-backed web research."""

    company_name: str
    url: str
    source_type: str = "web"
    rationale: str | None = None
    priority: int = 0


@dataclass(slots=True)
class PageCapture:
    """Filesystem-backed result of loading one page in Playwright."""

    requested_url: str
    final_url: str
    title: str | None
    html_path: str
    screenshot_path: str | None
    status_code: int | None


def normalize_url(url: str | None) -> str | None:
    """Normalize URLs for dedupe and stable capture."""

    if not url:
        return None
    candidate = url.strip()
    if not candidate:
        return None
    if "://" not in candidate:
        candidate = f"https://{candidate}"
    parsed = urlparse(candidate)
    if not parsed.netloc:
        return None
    normalized = parsed._replace(fragment="", query=parsed.query.strip(), path=parsed.path or "/")
    return urlunparse(normalized)


def build_research_targets(
    *,
    research_plan: ResearchPlan,
    company_candidates: list[CompanyCandidate],
    suggested_documents: list[SourceDocument],
    existing_documents: list[SourceDocument],
    max_targets_per_company: int = 4,
) -> list[ResearchTarget]:
    """Build a deduped set of official and public-source targets to capture."""

    existing_urls = {
        normalized
        for normalized in (normalize_url(document.url) for document in existing_documents)
        if normalized
    }
    suggestions_by_company: dict[str, list[SourceDocument]] = {}
    for document in suggested_documents:
        company_name = str(document.metadata.get("company_name", "")).strip().lower()
        if company_name:
            suggestions_by_company.setdefault(company_name, []).append(document)

    targets: list[ResearchTarget] = []
    seen_urls: set[str] = set()
    for candidate in company_candidates:
        company_key = candidate.name.strip().lower()
        candidate_targets = list(
            _iter_candidate_seed_targets(
                candidate=candidate,
                research_plan=research_plan,
                suggested_documents=suggestions_by_company.get(company_key, []),
            )
        )
        selected_for_company = 0
        for target in sorted(candidate_targets, key=lambda item: item.priority, reverse=True):
            normalized = normalize_url(target.url)
            if not normalized or normalized in seen_urls or normalized in existing_urls:
                continue
            target.url = normalized
            targets.append(target)
            seen_urls.add(normalized)
            selected_for_company += 1
            if selected_for_company >= max_targets_per_company:
                break
    return targets


def capture_page_snapshot(
    *,
    target: ResearchTarget,
    output_dir: Path,
    timeout_ms: int = 30000,
) -> PageCapture:
    """Use Playwright to load a page and persist HTML plus a screenshot."""

    from playwright.sync_api import Error as PlaywrightError
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
    from playwright.sync_api import sync_playwright

    slug = _slugify(f"{target.company_name}_{target.url}")
    html_path = output_dir / f"{slug}.html"
    screenshot_path = output_dir / f"{slug}.png"
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={"width": 1440, "height": 1024},
                ignore_https_errors=True,
            )
            page = context.new_page()
            response = page.goto(
                target.url,
                wait_until="domcontentloaded",
                timeout=timeout_ms,
            )
            page.wait_for_timeout(1200)
            html_path.write_text(page.content(), encoding="utf-8")
            page.screenshot(path=str(screenshot_path), full_page=True)
            final_url = page.url
            title = page.title()
            status_code = response.status if response is not None else None
            context.close()
            browser.close()
    except (PlaywrightTimeoutError, PlaywrightError) as exc:
        raise RuntimeError(f"Failed to capture {target.url}: {exc}") from exc

    return PageCapture(
        requested_url=target.url,
        final_url=final_url,
        title=title or None,
        html_path=str(html_path),
        screenshot_path=str(screenshot_path) if screenshot_path.exists() else None,
        status_code=status_code,
    )


def _iter_candidate_seed_targets(
    *,
    candidate: CompanyCandidate,
    research_plan: ResearchPlan,
    suggested_documents: list[SourceDocument],
) -> Iterable[ResearchTarget]:
    official_url = normalize_url(candidate.website)
    if official_url:
        yield ResearchTarget(
            company_name=candidate.name,
            url=official_url,
            source_type="official_site",
            rationale=f"Official homepage for {candidate.name}.",
            priority=100,
        )
        for suffix, label, priority in (
            ("/pricing", "pricing", 80),
            ("/features", "features", 75),
            ("/platform", "platform", 70),
            ("/integrations", "integrations", 70),
            ("/ai", "ai", 65),
        ):
            yield ResearchTarget(
                company_name=candidate.name,
                url=official_url.rstrip("/") + suffix,
                source_type="official_site",
                rationale=f"Official {label} page for {candidate.name}.",
                priority=priority,
            )

    for evidence in candidate.evidence:
        normalized = normalize_url(evidence.source_url)
        if normalized:
            yield ResearchTarget(
                company_name=candidate.name,
                url=normalized,
                source_type="public_source",
                rationale=evidence.detail,
                priority=60,
            )

    for document in suggested_documents:
        normalized = normalize_url(document.url)
        if normalized:
            yield ResearchTarget(
                company_name=candidate.name,
                url=normalized,
                source_type=document.source_type,
                rationale=document.snippet or f"Suggested source for {candidate.name}.",
                priority=90 if document.source_type.startswith("official") else 55,
            )

    for keyword in research_plan.comparison_dimensions[:2]:
        if official_url:
            yield ResearchTarget(
                company_name=candidate.name,
                url=official_url.rstrip("/") + f"/search?q={keyword}",
                source_type="official_site",
                rationale=f"Official site search seed for {keyword}.",
                priority=20,
            )


def _slugify(value: str) -> str:
    cleaned = [
        character.lower() if character.isalnum() else "_"
        for character in value
    ]
    slug = "".join(cleaned).strip("_")
    while "__" in slug:
        slug = slug.replace("__", "_")
    return slug[:120] or "page"
