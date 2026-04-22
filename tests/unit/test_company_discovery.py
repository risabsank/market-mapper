from market_mapper.agents.company_discovery import run_company_discovery
from market_mapper.schemas.models import CompanyCandidate, CompanyDiscoveryEvidence, ResearchPlan
from market_mapper.workflow.contracts import (
    CompanyDiscoveryNodeInput,
    CompanyDiscoveryNodeOutput,
)


def test_company_discovery_ranks_dedupes_and_caps_candidates(monkeypatch) -> None:
    def fake_generate_structured_output(**kwargs):
        return CompanyDiscoveryNodeOutput(
            next_route="executor",
            summary="raw discovery output",
            company_candidates=[
                CompanyCandidate(
                    name="Zendesk",
                    website="https://www.zendesk.com",
                    market_category="AI customer support",
                    rationale="Strong enterprise presence.",
                    score=0.92,
                    evidence=[
                        CompanyDiscoveryEvidence(
                            label="Market presence",
                            detail="Widely recognized in customer support software.",
                            source_url="https://www.zendesk.com",
                        )
                    ],
                ),
                CompanyCandidate(
                    name="Intercom",
                    website="https://www.intercom.com",
                    market_category="AI customer support",
                    rationale="Strong AI support positioning.",
                    score=0.88,
                    evidence=[
                        CompanyDiscoveryEvidence(
                            label="AI positioning",
                            detail="Promotes AI-first customer support workflows.",
                            source_url="https://www.intercom.com",
                        )
                    ],
                ),
                CompanyCandidate(
                    name="Zendesk",
                    website="https://www.zendesk.com",
                    market_category="AI customer support",
                    rationale="Duplicate lower-ranked entry.",
                    score=0.51,
                ),
            ],
        )

    monkeypatch.setattr(
        "market_mapper.agents.company_discovery.generate_structured_output",
        fake_generate_structured_output,
    )

    output = run_company_discovery(
        CompanyDiscoveryNodeInput(
            run_id="run_test",
            research_plan=ResearchPlan(
                market_query="AI customer support",
                requested_company_count=2,
                named_companies=[],
            ),
        )
    )

    assert [candidate.name for candidate in output.company_candidates] == ["Zendesk", "Intercom"]
    assert output.company_candidates[0].public_signals["discovery_rank"] == 1
    assert output.company_candidates[1].public_signals["discovery_rank"] == 2
    assert output.company_candidates[0].evidence[0].label == "Market presence"
    assert output.next_route == "executor"


def test_company_discovery_honors_named_companies(monkeypatch) -> None:
    def fake_generate_structured_output(**kwargs):
        assert kwargs["user_input"]
        return CompanyDiscoveryNodeOutput(
            next_route="executor",
            summary="raw named company output",
            company_candidates=[
                CompanyCandidate(
                    name="Intercom",
                    website="https://www.intercom.com",
                    market_category="customer support",
                    rationale="Explicitly requested by the user.",
                    score=0.61,
                    evidence=[
                        CompanyDiscoveryEvidence(
                            label="Requested company",
                            detail="The user explicitly named Intercom.",
                        )
                    ],
                ),
                CompanyCandidate(
                    name="Zendesk",
                    website="https://www.zendesk.com",
                    market_category="customer support",
                    rationale="Explicitly requested by the user.",
                    score=0.84,
                    evidence=[
                        CompanyDiscoveryEvidence(
                            label="Requested company",
                            detail="The user explicitly named Zendesk.",
                        )
                    ],
                ),
                CompanyCandidate(
                    name="HubSpot",
                    website="https://www.hubspot.com",
                    market_category="customer support",
                    rationale="Not explicitly requested.",
                    score=0.95,
                ),
            ],
        )

    monkeypatch.setattr(
        "market_mapper.agents.company_discovery.generate_structured_output",
        fake_generate_structured_output,
    )

    output = run_company_discovery(
        CompanyDiscoveryNodeInput(
            run_id="run_test",
            research_plan=ResearchPlan(
                market_query="Zendesk and Intercom",
                requested_company_count=2,
                named_companies=["Zendesk", "Intercom"],
            ),
        )
    )

    assert [candidate.name for candidate in output.company_candidates] == ["Zendesk", "Intercom"]
    assert output.company_candidates[0].public_signals["requested_company"] == "true"
    assert output.company_candidates[1].public_signals["requested_company"] == "true"
