from market_mapper.agents.comparison import run_comparison
from market_mapper.schemas.models import (
    CompanyProfile,
    ComparisonFinding,
    ComparisonResult,
    ExtractedClaim,
    ResearchPlan,
)
from market_mapper.workflow.contracts import ComparisonNodeInput, ComparisonNodeOutput


def test_comparison_agent_validates_dimensions_and_evidence(monkeypatch) -> None:
    profile_one = CompanyProfile(
        id="company_1",
        name="Alpha",
        pricing_model="Contact sales",
        core_features=["AI agent", "Routing"],
        positioning_statement="Enterprise AI support",
        target_customers=["Enterprise"],
        integrations=["Salesforce"],
        differentiators=["Workflow depth"],
        strengths=["Enterprise fit"],
        weaknesses_or_gaps=["Opaque pricing"],
        claims=[
            ExtractedClaim(
                id="claim_1",
                label="Pricing",
                value="Contact sales",
                source_document_ids=["source_1"],
                confidence=0.8,
            )
        ],
        source_document_ids=["source_1"],
    )
    profile_two = CompanyProfile(
        id="company_2",
        name="Beta",
        pricing_model="Seat-based",
        core_features=["Inbox", "Bots"],
        positioning_statement="Mid-market support",
        target_customers=["Mid-market"],
        integrations=["HubSpot"],
        differentiators=["Ease of use"],
        strengths=["Faster onboarding"],
        weaknesses_or_gaps=["Fewer enterprise controls"],
        claims=[
            ExtractedClaim(
                id="claim_2",
                label="Features",
                value="Inbox and bots",
                source_document_ids=["source_2"],
                confidence=0.7,
            )
        ],
        source_document_ids=["source_2"],
    )

    def fake_generate_structured_output(**kwargs):
        assert "requested_dimensions" in kwargs["user_input"]
        return ComparisonNodeOutput(
            next_route="executor",
            summary="raw comparison output",
            comparison_result=ComparisonResult(
                run_id="placeholder",
                company_ids=[],
                dimensions=["pricing"],
                findings=[
                    ComparisonFinding(
                        dimension="pricing",
                        summary="Alpha has stronger enterprise pricing alignment.",
                        winner_company_id="company_1",
                        evidence_claim_ids=["claim_1", "missing_claim"],
                    )
                ],
                similarities=["Both offer AI-assisted support.", "Both offer AI-assisted support."],
                differences=["Alpha skews enterprise while Beta skews mid-market."],
                tradeoffs=["Alpha is deeper but less transparent on pricing."],
                ideal_customer_notes=["Alpha fits large support teams."],
            ),
        )

    monkeypatch.setattr(
        "market_mapper.agents.comparison.generate_structured_output",
        fake_generate_structured_output,
    )

    output = run_comparison(
        ComparisonNodeInput(
            run_id="run_test",
            research_plan=ResearchPlan(
                market_query="AI support",
                requested_company_count=2,
                comparison_dimensions=["pricing", "features"],
            ),
            company_profiles=[profile_one, profile_two],
        )
    )

    result = output.comparison_result
    assert result.run_id == "run_test"
    assert result.company_ids == ["company_1", "company_2"]
    assert result.dimensions[:2] == ["pricing", "features"]
    assert result.findings[0].evidence_claim_ids == ["claim_1"]
    assert any(finding.dimension == "features" for finding in result.findings)
    assert result.similarities == ["Both offer AI-assisted support."]
    assert output.next_route == "executor"
