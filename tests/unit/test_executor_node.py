from market_mapper.schemas.models import (
    AgentTask,
    ComparisonResult,
    CompanyCandidate,
    CompanyProfile,
    ResearchPlan,
    ResearchSession,
    VerificationResult,
    WorkflowRun,
)
from market_mapper.workflow.nodes.executor import executor_node
from market_mapper.workflow.state import ResearchWorkflowState


def test_executor_node_creates_sandbox_task_when_requested(monkeypatch) -> None:
    def fake_run_workflow_executor(_):
        from market_mapper.workflow.contracts import ExecutorNodeOutput

        return ExecutorNodeOutput(
            next_route="web_research",
            summary="Route to web research with sandbox execution.",
            current_node="planner",
            needs_sandbox=True,
            sandbox_purpose="Collect and snapshot public web pages for source-backed research.",
            checkpoint_payload={"next_route": "web_research", "needs_sandbox": True},
        )

    monkeypatch.setattr(
        "market_mapper.workflow.nodes.executor.run_workflow_executor",
        fake_run_workflow_executor,
    )

    session = ResearchSession(
        user_prompt="Analyze AI support tools.",
        research_plan=ResearchPlan(market_query="AI support tools"),
    )
    run = WorkflowRun(session_id=session.id)
    state = ResearchWorkflowState(session=session, run=run)

    updated = executor_node(state)

    assert updated.executor_route == "web_research"
    assert len(updated.sandbox_tasks) == 1
    assert updated.sandbox_tasks[0].route_name == "web_research"
    assert updated.run.checkpoints[-1].payload["needs_sandbox"] is True


def test_executor_node_tracks_retries_for_target_stage(monkeypatch) -> None:
    def fake_run_workflow_executor(_):
        from market_mapper.workflow.contracts import ExecutorNodeOutput

        return ExecutorNodeOutput(
            next_route="structured_extraction",
            summary="Retry structured extraction.",
            current_node="critic_verifier",
            retry_requested=True,
            retry_reason="Profiles are incomplete.",
            retry_target_route="structured_extraction",
            checkpoint_payload={
                "next_route": "structured_extraction",
                "retry_requested": True,
            },
        )

    monkeypatch.setattr(
        "market_mapper.workflow.nodes.executor.run_workflow_executor",
        fake_run_workflow_executor,
    )

    session = ResearchSession(
        user_prompt="Analyze AI support tools.",
        research_plan=ResearchPlan(market_query="AI support tools"),
    )
    run = WorkflowRun(session_id=session.id)
    prior_task = AgentTask(
        run_id=run.id,
        agent_name="structured_extraction",
        task_type="extract_company_profiles",
    )
    prior_task.mark_completed(outputs={"company_profile_ids": []}, output_summary="Initial extraction")
    run.add_task(prior_task)

    state = ResearchWorkflowState(
        session=session,
        run=run,
        company_candidates=[CompanyCandidate(name="Example", rationale="Example rationale")],
        company_profiles=[CompanyProfile(name="Example")],
        comparison_result=ComparisonResult(run_id=run.id),
        verification_result=VerificationResult(
            run_id=run.id,
            approved=False,
            requires_retry=True,
            next_actions=["Retry structured extraction."],
        ),
    )

    updated = executor_node(state)
    retried_task = updated.run.get_task(prior_task.id)

    assert updated.run.retry_count == 1
    assert retried_task.retry_count == 1
    assert updated.executor_route == "structured_extraction"


def test_executor_caps_research_retries_and_moves_forward(monkeypatch) -> None:
    def fake_run_workflow_executor(_):
        from market_mapper.workflow.contracts import ExecutorNodeOutput

        return ExecutorNodeOutput(
            next_route="web_research",
            summary="Verifier requested more sources.",
            current_node="critic_verifier",
            retry_requested=False,
            checkpoint_payload={"next_route": "web_research"},
        )

    monkeypatch.setattr(
        "market_mapper.workflow.nodes.executor.run_workflow_executor",
        fake_run_workflow_executor,
    )
    monkeypatch.setenv("MARKET_MAPPER_MAX_RESEARCH_RETRIES", "2")

    from market_mapper.config.settings import get_settings

    get_settings.cache_clear()

    session = ResearchSession(
        user_prompt="Analyze AI support tools.",
        research_plan=ResearchPlan(market_query="AI support tools"),
    )
    run = WorkflowRun(session_id=session.id)
    for index in range(3):
        prior_task = AgentTask(
            run_id=run.id,
            agent_name="web_research",
            task_type=f"collect_sources_{index}",
        )
        prior_task.mark_completed(
            outputs={"source_document_ids": []},
            output_summary=f"Web research pass {index + 1}",
        )
        run.add_task(prior_task)

    state = ResearchWorkflowState(
        session=session,
        run=run,
        company_candidates=[CompanyCandidate(name="Example", rationale="Example rationale")],
        source_documents=[],
        company_profiles=[CompanyProfile(name="Example")],
        comparison_result=ComparisonResult(run_id=run.id),
        verification_result=VerificationResult(
            run_id=run.id,
            approved=False,
            requires_retry=True,
            next_actions=["Retry web research to gather stronger evidence."],
        ),
    )

    updated = executor_node(state)

    assert updated.executor_route == "report_generation"
    assert updated.run.retry_count == 0
    assert updated.run.checkpoints[-1].payload["retry_cap_reached"] is True
    assert "Retry cap reached for web research" in updated.executor_summary
