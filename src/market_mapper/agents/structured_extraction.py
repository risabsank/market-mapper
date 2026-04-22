"""Structured Extraction Agent placeholder implementation."""

from __future__ import annotations

from market_mapper.schemas.models import CompanyProfile, ExtractedClaim
from market_mapper.workflow.contracts import (
    StructuredExtractionNodeInput,
    StructuredExtractionNodeOutput,
)


def run_structured_extraction(
    node_input: StructuredExtractionNodeInput,
) -> StructuredExtractionNodeOutput:
    """Create placeholder company profiles from candidates and sources."""

    profiles = list(node_input.existing_profiles)
    if not profiles:
        source_ids = [document.id for document in node_input.source_documents]
        for candidate in node_input.company_candidates:
            profiles.append(
                CompanyProfile(
                    name=candidate.name,
                    website=candidate.website,
                    market_category=candidate.market_category,
                    product_summary="Placeholder profile generated from discovery data.",
                    target_customers=["support teams"],
                    core_features=["ai_agent", "ticket_triage"],
                    source_document_ids=source_ids,
                    claims=[
                        ExtractedClaim(
                            label="placeholder_summary",
                            value="Structured extraction placeholder output.",
                            source_document_ids=source_ids,
                        )
                    ],
                )
            )

    return StructuredExtractionNodeOutput(
        company_profiles=profiles,
        summary="Structured extraction placeholder generated company profiles.",
        next_route="executor",
    )
