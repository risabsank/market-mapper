from market_mapper.agents.report_generation import run_report_generation
from market_mapper.schemas.models import (
    CompanyProfile,
    ComparisonResult,
    Report,
    ReportSection,
    ResearchPlan,
    SourceDocument,
)
from market_mapper.workflow.contracts import (
    ReportGenerationNodeInput,
    ReportGenerationNodeOutput,
)


def test_report_generation_builds_markdown_and_validates_citations(monkeypatch) -> None:
    source_one = SourceDocument(
        id="source_1",
        url="https://example.com/pricing",
        title="Pricing",
    )
    source_two = SourceDocument(
        id="source_2",
        url="https://example.com/features",
        title="Features",
    )
    company_profile = CompanyProfile(
        id="company_1",
        name="ExampleCo",
        product_summary="AI customer support platform.",
        positioning_statement="Enterprise support automation.",
        target_customers=["Enterprise"],
        core_features=["AI agent", "Routing"],
        differentiators=["Workflow depth"],
        strengths=["Enterprise fit"],
        source_document_ids=["source_1", "source_2"],
    )

    def fake_generate_structured_output(**kwargs):
        return ReportGenerationNodeOutput(
            next_route="executor",
            summary="raw report output",
            report=Report(
                run_id="placeholder",
                title="AI Support Landscape",
                executive_summary="ExampleCo stands out for enterprise use cases.",
                sections=[
                    ReportSection(
                        heading="Company Summaries",
                        body="Custom company summary.",
                        citation_ids=["source_1", "missing_source"],
                    )
                ],
                markdown_body="placeholder",
                source_document_ids=[],
            ),
        )

    monkeypatch.setattr(
        "market_mapper.agents.report_generation.generate_structured_output",
        fake_generate_structured_output,
    )

    output = run_report_generation(
        ReportGenerationNodeInput(
            run_id="run_test",
            research_plan=ResearchPlan(
                market_query="AI support",
                requested_company_count=1,
                comparison_dimensions=["pricing", "features"],
            ),
            company_profiles=[company_profile],
            comparison_result=ComparisonResult(run_id="run_test"),
            source_documents=[source_one, source_two],
        )
    )

    report = output.report
    assert report.run_id == "run_test"
    assert "## Executive Summary" in report.markdown_body
    assert "## Company Summaries" in report.markdown_body
    assert "## Structured Comparison" in report.markdown_body
    assert "## Key Takeaways" in report.markdown_body
    assert "## Source References" in report.markdown_body
    assert report.sections[0].citation_ids == ["source_1"]
    assert report.source_document_ids == ["source_1", "source_2"]
    assert output.next_route == "executor"
