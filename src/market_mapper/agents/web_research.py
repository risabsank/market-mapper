"""Web Research Agent placeholder implementation."""

from __future__ import annotations

from market_mapper.schemas.models import SourceDocument
from market_mapper.workflow.contracts import WebResearchNodeInput, WebResearchNodeOutput


def run_web_research(node_input: WebResearchNodeInput) -> WebResearchNodeOutput:
    """Return placeholder source documents for selected companies."""

    documents = list(node_input.existing_documents)
    if not documents:
        for candidate in node_input.company_candidates:
            if candidate.website:
                documents.append(
                    SourceDocument(
                        url=candidate.website,
                        title=f"{candidate.name} homepage",
                        snippet="Placeholder source captured by web research node.",
                    )
                )

    return WebResearchNodeOutput(
        source_documents=documents,
        used_sandbox=bool(documents),
        summary="Web research placeholder collected source documents.",
        next_route="executor",
    )
