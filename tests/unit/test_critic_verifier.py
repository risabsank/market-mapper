from market_mapper.agents.critic_verifier import run_critic_verifier
from market_mapper.schemas.models import (
    ComparisonFinding,
    ComparisonResult,
    CompanyProfile,
    ExtractedClaim,
    ResearchPlan,
    VerificationResult,
)
from market_mapper.workflow.contracts import CriticVerifierNodeInput, CriticVerifierNodeOutput


def test_critic_verifier_routes_retry_to_relevant_stage(monkeypatch) -> None:
    profile = CompanyProfile(
        id="company_1",
        name="Alpha",
        confidence=0.2,
        explicit_missing_fields=[
            "product_summary",
            "core_features",
            "integrations",
            "pricing_model",
            "positioning_statement",
        ],
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
    comparison_result = ComparisonResult(
        run_id="run_test",
        company_ids=["company_1"],
        dimensions=["pricing", "features"],
        findings=[
            ComparisonFinding(
                dimension="pricing",
                summary="Pricing is partly understood.",
                winner_company_id="company_1",
                evidence_claim_ids=["claim_1"],
            )
        ],
        tradeoffs=[],
    )

    def fake_generate_structured_output(**kwargs):
        return CriticVerifierNodeOutput(
            next_route="executor",
            summary="raw verification output",
            verification_result=VerificationResult(
                run_id="placeholder",
                approved=True,
                requires_retry=False,
                issues=[],
                next_actions=[],
            ),
        )

    monkeypatch.setattr(
        "market_mapper.agents.critic_verifier.generate_structured_output",
        fake_generate_structured_output,
    )

    output = run_critic_verifier(
        CriticVerifierNodeInput(
            run_id="run_test",
            research_plan=ResearchPlan(
                market_query="AI support",
                requested_company_count=1,
                comparison_dimensions=["pricing", "features"],
            ),
            company_profiles=[profile],
            comparison_result=comparison_result,
        )
    )

    result = output.verification_result
    assert result.approved is False
    assert result.requires_retry is True
    assert any(issue.fix_target == "structured_extraction" for issue in result.issues)
    assert any(issue.fix_target == "comparison" for issue in result.issues)
    assert result.next_actions[0].startswith("Retry structured extraction") or result.next_actions[0].startswith("Retry web research")
    assert output.next_route == "executor"
