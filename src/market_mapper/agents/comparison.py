"""Comparison Agent placeholder implementation."""

from __future__ import annotations

from market_mapper.schemas.models import ComparisonFinding, ComparisonResult
from market_mapper.workflow.contracts import ComparisonNodeInput, ComparisonNodeOutput


def run_comparison(node_input: ComparisonNodeInput) -> ComparisonNodeOutput:
    """Generate a placeholder comparison result from company profiles."""

    dimensions = node_input.research_plan.comparison_dimensions or [
        "pricing",
        "features",
        "positioning",
    ]
    findings = [
        ComparisonFinding(
            dimension=dimension,
            summary=f"Placeholder comparison for {dimension}.",
        )
        for dimension in dimensions
    ]
    comparison_result = ComparisonResult(
        run_id=node_input.run_id,
        company_ids=[profile.id for profile in node_input.company_profiles],
        dimensions=dimensions,
        findings=findings,
        similarities=["Placeholder similarity across selected companies."],
        differences=["Placeholder difference across selected companies."],
        tradeoffs=["Placeholder tradeoff summary."],
    )

    return ComparisonNodeOutput(
        comparison_result=comparison_result,
        summary="Comparison placeholder generated a structured result.",
        next_route="executor",
    )
