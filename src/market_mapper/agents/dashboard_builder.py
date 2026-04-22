"""Dashboard Builder placeholder implementation."""

from __future__ import annotations

from market_mapper.schemas.models import DashboardSection, DashboardState
from market_mapper.workflow.contracts import (
    DashboardBuilderNodeInput,
    DashboardBuilderNodeOutput,
)


def run_dashboard_builder(
    node_input: DashboardBuilderNodeInput,
) -> DashboardBuilderNodeOutput:
    """Create a placeholder dashboard state from completed outputs."""

    dashboard_state = DashboardState(
        session_id=node_input.session_id,
        run_id=node_input.run_id,
        executive_summary=node_input.report.executive_summary,
        selected_company_ids=[profile.id for profile in node_input.company_profiles],
        comparison_result_id=node_input.comparison_result.id,
        report_id=node_input.report.id,
        chart_ids=[chart.id for chart in node_input.chart_specs],
        source_document_ids=[document.id for document in node_input.source_documents],
        sections=[
            DashboardSection(
                key="executive_summary",
                title="Executive Summary",
                summary=node_input.report.executive_summary,
            ),
            DashboardSection(
                key="comparison",
                title="Comparison",
                summary="Placeholder dashboard section for comparison output.",
            ),
        ],
    )
    return DashboardBuilderNodeOutput(
        dashboard_state=dashboard_state,
        summary="Dashboard builder placeholder created dashboard state.",
        next_route="executor",
    )
