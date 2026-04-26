from pathlib import Path

from market_mapper.schemas.models import (
    AgentTask,
    ApprovalRecord,
    ApprovalStatus,
    ArtifactKind,
    CompanyWorkspaceStatus,
    DashboardState,
    ResearchPlan,
    ResearchSession,
    SandboxArtifact,
    SandboxTask,
    WorkspaceSnapshot,
    WorkflowRun,
)
from market_mapper.storage import FileWorkflowStateStore


def test_file_workflow_state_store_persists_runs_tasks_and_artifacts(tmp_path: Path) -> None:
    store = FileWorkflowStateStore(tmp_path / "state")

    session = ResearchSession(
        user_id="demo-user",
        user_prompt="Analyze 4 of the largest companies in AI customer support.",
        research_plan=ResearchPlan(
            market_query="AI customer support",
            comparison_dimensions=["pricing", "features", "positioning"],
        ),
    )
    store.save_session(session)

    run = WorkflowRun(session_id=session.id)
    run.mark_running(current_node="planner")
    store.save_run(run)

    task = AgentTask(
        run_id=run.id,
        agent_name="research_planner",
        task_type="plan_prompt",
        inputs={"prompt": session.user_prompt},
    )
    task.mark_running()
    task.mark_completed(outputs={"plan_id": session.research_plan.id}, output_summary="Plan ready")
    store.add_agent_task(run.id, task)

    sandbox_task = SandboxTask(
        run_id=run.id,
        agent_task_id=task.id,
        purpose="Capture company source pages",
    )
    sandbox_task.mark_running()
    sandbox_task.mark_completed()
    store.add_sandbox_task(run.id, sandbox_task)
    store.save_sandbox_task(sandbox_task)

    artifact = SandboxArtifact(
        run_id=run.id,
        kind=ArtifactKind.PAGE_SNAPSHOT,
        label="homepage snapshot",
        source_task_id=task.id,
        path="/tmp/example.html",
    )
    store.add_artifact(run.id, artifact)

    approval = ApprovalRecord(
        target_kind="run",
        target_id=run.id,
        label="critic verification",
    )
    approval.decide(approved=True, approved_by="verifier")
    store.approve_run(run.id, approval)

    dashboard = DashboardState(session_id=session.id, run_id=run.id)
    store.save_dashboard_state(dashboard)

    loaded_session = store.load_session(session.id)
    loaded_run = store.load_run(run.id)
    loaded_dashboard = store.load_dashboard_state(dashboard.id)
    loaded_artifact = store.load_artifact(run.id, artifact.id)

    assert loaded_session.research_plan is not None
    assert loaded_run.current_node == "planner"
    assert loaded_run.agent_tasks[0].output_summary == "Plan ready"
    assert loaded_run.agent_tasks[0].sandbox_task_ids == [sandbox_task.id]
    assert loaded_run.agent_tasks[0].artifact_ids == [artifact.id]
    assert loaded_run.approval_records[0].status == ApprovalStatus.APPROVED
    assert loaded_dashboard.run_id == run.id
    assert loaded_artifact.kind == ArtifactKind.PAGE_SNAPSHOT


def test_file_workflow_state_store_persists_workspace_snapshots(tmp_path: Path) -> None:
    store = FileWorkflowStateStore(tmp_path / "state")
    snapshot = WorkspaceSnapshot(
        session_id="session_1",
        user_id="demo-user",
        run_id="run_1",
        prompt="Compare AI support tools.",
        company_statuses=[
            CompanyWorkspaceStatus(
                name="Example Co",
                status="running",
                source_document_ids=["source_1"],
            )
        ],
    )

    store.save_workspace_snapshot(snapshot)
    loaded = store.load_workspace_snapshot("session_1")

    assert loaded.run_id == "run_1"
    assert loaded.company_statuses[0].name == "Example Co"
