"""OpenAI-powered Company Discovery Agent implementation."""

from __future__ import annotations

from market_mapper.schemas.models import CompanyCandidate
from market_mapper.services import generate_structured_output, render_agent_input
from market_mapper.workflow.contracts import (
    CompanyDiscoveryNodeInput,
    CompanyDiscoveryNodeOutput,
)

DISCOVERY_SYSTEM_PROMPT = """
You are the Company Discovery Agent for Market Mapper.

Identify candidate companies that match the research plan.

Rules:
- Return 3 to 5 candidates unless the requested company count is lower.
- If named_companies is provided, treat discovery as a normalization and enrichment step for those exact companies rather than a broad market search.
- Favor companies that fit the research plan's market query and discovery criteria.
- Include rationale, explicit evidence items, and a relevance score for each candidate.
- Use public information and web knowledge. When web search is available, use it.
- Do not invent exact private metrics.
- Evidence should explain why the company is a strong candidate for this market category or ranking criteria.
"""


def _normalize_ranked_candidates(
    *,
    candidates: list[CompanyCandidate],
    requested_company_count: int,
    named_companies: list[str],
) -> list[CompanyCandidate]:
    """Rank, dedupe, and cap candidate output for downstream research."""

    deduped_by_name: dict[str, CompanyCandidate] = {}
    for candidate in candidates:
        key = candidate.name.strip().lower()
        existing = deduped_by_name.get(key)
        if existing is None or candidate.score > existing.score:
            deduped_by_name[key] = candidate

    ranked = sorted(
        deduped_by_name.values(),
        key=lambda candidate: (
            candidate.name.strip().lower() in {name.strip().lower() for name in named_companies},
            candidate.score,
            len(candidate.evidence),
            candidate.name.lower(),
        ),
        reverse=True,
    )

    cap = len(named_companies) if named_companies else requested_company_count
    cap = max(1, min(5, cap))
    selected = ranked[:cap]

    for index, candidate in enumerate(selected, start=1):
        candidate.score = max(0.0, min(1.0, candidate.score))
        candidate.public_signals.setdefault("discovery_rank", index)
        candidate.public_signals.setdefault("evidence_count", len(candidate.evidence))
        candidate.public_signals.setdefault(
            "requested_company",
            str(candidate.name.strip().lower() in {name.strip().lower() for name in named_companies}).lower(),
        )

    return selected


def run_company_discovery(
    node_input: CompanyDiscoveryNodeInput,
) -> CompanyDiscoveryNodeOutput:
    """Return OpenAI-generated company candidates from the research plan."""

    response = generate_structured_output(
        response_model=CompanyDiscoveryNodeOutput,
        system_prompt=DISCOVERY_SYSTEM_PROMPT,
        user_input=render_agent_input(
            task_description=(
                "Normalize and enrich the explicitly named companies."
                if node_input.research_plan.named_companies
                else "Discover candidate companies for this market research plan."
            ),
            context={
                "run_id": node_input.run_id,
                "research_plan": node_input.research_plan.model_dump(mode="json"),
                "named_companies_mode": bool(node_input.research_plan.named_companies),
                "existing_candidates": [
                    candidate.model_dump(mode="json")
                    for candidate in node_input.existing_candidates
                ],
            },
        ),
        use_web_search=True,
    )
    response.company_candidates = _normalize_ranked_candidates(
        candidates=response.company_candidates,
        requested_company_count=node_input.research_plan.requested_company_count,
        named_companies=node_input.research_plan.named_companies,
    )
    response.summary = (
        (
            f"Company discovery normalized {len(response.company_candidates)} named companies "
            "with rationale and evidence."
            if node_input.research_plan.named_companies
            else f"Company discovery returned {len(response.company_candidates)} ranked candidates "
            "with rationale and evidence."
        )
    )
    response.next_route = "executor"
    return response
