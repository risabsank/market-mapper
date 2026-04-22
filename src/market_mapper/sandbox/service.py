"""Trusted-harness service for sandbox-backed execution."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from market_mapper.config.settings import get_settings
from market_mapper.schemas.models import SandboxArtifact, SandboxTask
from market_mapper.sandbox.contracts import SandboxExecutionRequest
from market_mapper.sandbox.runners.sandbox_runtime import LocalSandboxRuntime, SandboxRuntime
from market_mapper.workflow.state import ResearchWorkflowState


class SandboxService:
    """Coordinate sandbox execution while keeping orchestration in the trusted harness."""

    def __init__(self, runtime: SandboxRuntime | None = None, root_dir: str | None = None) -> None:
        settings = get_settings()
        self.root_dir = Path(root_dir or settings.workflow_state_dir) / "sandbox_runs"
        self.runtime = runtime or LocalSandboxRuntime()

    def execute_route_tasks(
        self,
        *,
        state: ResearchWorkflowState,
        route_name: str,
        payload: dict[str, Any],
        target_agent_task_id: str,
    ) -> list[SandboxArtifact]:
        """Execute pending or resumable sandbox tasks for a route and persist artifacts in state."""

        artifacts: list[SandboxArtifact] = []
        for sandbox_task in self._pending_tasks_for_route(state, route_name):
            sandbox_task.agent_task_id = target_agent_task_id
            sandbox_task.mark_running()
            request = SandboxExecutionRequest(
                route_name=route_name,
                run_id=state.run.id,
                sandbox_task_id=sandbox_task.id,
                working_directory=str(self._working_directory(state.run.id, sandbox_task.id)),
                payload=payload,
            )
            result = self.runtime.execute(request)
            for file_artifact in result.artifacts:
                artifact = SandboxArtifact(
                    run_id=state.run.id,
                    kind=file_artifact.kind,
                    label=file_artifact.label,
                    path=file_artifact.path,
                    content_type=file_artifact.content_type,
                    source_task_id=target_agent_task_id,
                    metadata={k: str(v) for k, v in file_artifact.metadata.items()},
                )
                sandbox_task.add_artifact(artifact.id)
                state.run.add_artifact(artifact.id)
                artifacts.append(artifact)
                state.sandbox_artifacts.append(artifact)

            sandbox_task.mark_completed()
            state.touch()
        return artifacts

    def _pending_tasks_for_route(
        self, state: ResearchWorkflowState, route_name: str
    ) -> list[SandboxTask]:
        return [
            sandbox_task
            for sandbox_task in state.sandbox_tasks
            if sandbox_task.route_name == route_name
            and sandbox_task.status.value in {"pending", "resumable"}
        ]

    def _working_directory(self, run_id: str, sandbox_task_id: str) -> Path:
        return self.root_dir / run_id / sandbox_task_id

