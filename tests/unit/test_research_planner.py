from market_mapper.agents.planner import run_research_planner
from market_mapper.schemas.models import ResearchPlan
from market_mapper.workflow.contracts import PlannerNodeInput


def test_research_planner_uses_openai_structured_plan(monkeypatch) -> None:
    structured_plan = ResearchPlan(
        market_query="AI customer support",
        requested_company_count=4,
        discovery_criteria=["largest public market presence", "market relevance"],
        comparison_dimensions=["pricing", "features", "positioning"],
        assumptions=["Use public web sources only."],
    )

    def fake_generate_structured_output(**kwargs):
        assert kwargs["response_model"] is ResearchPlan
        return structured_plan

    monkeypatch.setattr(
        "market_mapper.agents.planner.generate_structured_output",
        fake_generate_structured_output,
    )

    output = run_research_planner(
        PlannerNodeInput(
            session_id="session_test",
            user_prompt="Analyze 4 of the largest companies in AI customer support and create a comparison report.",
        )
    )

    plan = output.research_plan
    assert plan.requested_company_count == 4
    assert plan.market_query == "AI customer support"
    assert "largest public market presence" in plan.discovery_criteria
    assert "pricing" in plan.comparison_dimensions
    assert output.next_route == "executor"
    assert output.assumptions == structured_plan.assumptions
