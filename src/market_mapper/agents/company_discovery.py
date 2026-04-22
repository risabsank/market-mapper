"""Company Discovery Agent placeholder implementation."""

from __future__ import annotations

from market_mapper.schemas.models import CompanyCandidate
from market_mapper.workflow.contracts import (
    CompanyDiscoveryNodeInput,
    CompanyDiscoveryNodeOutput,
)


def run_company_discovery(
    node_input: CompanyDiscoveryNodeInput,
) -> CompanyDiscoveryNodeOutput:
    """Return placeholder company candidates from the research plan."""

    query = node_input.research_plan.market_query
    candidates = node_input.existing_candidates or [
        CompanyCandidate(
            name="Placeholder AI Support Co.",
            website="https://example.com",
            market_category=query,
            rationale="Placeholder candidate chosen to exercise discovery flow.",
            score=1.0,
        )
    ]
    return CompanyDiscoveryNodeOutput(
        company_candidates=candidates,
        summary="Company discovery placeholder produced candidates.",
        next_route="executor",
    )
