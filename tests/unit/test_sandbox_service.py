from pathlib import Path

from market_mapper.research.fetchers import PageCapture
from market_mapper.schemas.models import AgentTask, ResearchSession, WorkflowRun, SandboxTask
from market_mapper.sandbox import SandboxService
from market_mapper.workflow.state import ResearchWorkflowState


def test_sandbox_service_executes_pending_route_tasks(tmp_path: Path, monkeypatch) -> None:
    def fake_capture_page_snapshot(*, target, output_dir, timeout_ms=30000):
        output_dir.mkdir(parents=True, exist_ok=True)
        html_path = output_dir / "example.html"
        screenshot_path = output_dir / "example.png"
        html_path.write_text(
            "<html><head><title>Example</title></head><body><p>Captured text.</p></body></html>",
            encoding="utf-8",
        )
        screenshot_path.write_bytes(b"fake-image")
        return PageCapture(
            requested_url=target.url,
            final_url=target.url,
            title="Example",
            html_path=str(html_path),
            screenshot_path=str(screenshot_path),
            status_code=200,
        )

    monkeypatch.setattr(
        "market_mapper.sandbox.runners.sandbox_runtime.capture_page_snapshot",
        fake_capture_page_snapshot,
    )

    session = ResearchSession(user_id="demo-user", user_prompt="Analyze AI support tools.")
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
        payload={
            "research_plan": {
                "market_query": "AI support tools",
                "requested_company_count": 1,
                "comparison_dimensions": ["pricing", "features"],
            },
            "company_candidates": [
                {
                    "name": "ExampleCo",
                    "website": "https://example.com",
                    "rationale": "Relevant",
                    "score": 0.9,
                }
            ],
            "source_documents": [],
            "existing_documents": [],
        },
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
