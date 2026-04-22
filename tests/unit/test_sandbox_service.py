from pathlib import Path

from market_mapper.schemas.models import AgentTask, ResearchSession, WorkflowRun, SandboxTask
from market_mapper.sandbox import SandboxService
from market_mapper.workflow.state import ResearchWorkflowState


def test_sandbox_service_executes_pending_route_tasks(tmp_path: Path) -> None:
    session = ResearchSession(user_prompt="Analyze AI support tools.")
    run = WorkflowRun(session_id=session.id)
    route_task = AgentTask(
        run_id=run.id,
        agent_name="web_research",
        task_type="collect_sources",
    )
    route_task.mark_running()
    run.add_task(route_task)

    sandbox_task = SandboxTask(
        run_id=run.id,
        route_name="web_research",
        purpose="Collect and snapshot public web pages for source-backed research.",
        agent_task_id=route_task.id,
    )
    state = ResearchWorkflowState(
        session=session,
        run=run,
        sandbox_tasks=[sandbox_task],
    )

    service = SandboxService(root_dir=str(tmp_path / "state"))
    artifacts = service.execute_route_tasks(
        state=state,
        route_name="web_research",
        payload={"sources": ["https://example.com"]},
        target_agent_task_id=route_task.id,
    )

    assert len(artifacts) >= 1
    assert state.sandbox_tasks[0].status.value == "completed"
    assert state.sandbox_tasks[0].input_manifest_path is not None
    assert state.sandbox_tasks[0].output_manifest_path is not None
    assert state.sandbox_tasks[0].validation_result is not None
    assert state.sandbox_tasks[0].validation_result.valid is True
    assert len(state.sandbox_tasks[0].lifecycle_events) >= 3
    assert any(Path(artifact.path).exists() for artifact in artifacts if artifact.path)
