"""Durable file-backed repositories for workflow state."""

from __future__ import annotations

import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

from market_mapper.schemas.models import (
    AgentTask,
    ApprovalRecord,
    DashboardState,
    ResearchSession,
    SandboxArtifact,
    SandboxTask,
    WorkflowRun,
)


class FileWorkflowStateStore:
    """Small durable store for sessions, runs, dashboards, and workflow state."""

    def __init__(self, root_dir: str | Path) -> None:
        self.root_dir = Path(root_dir)
        self.sessions_dir = self.root_dir / "sessions"
        self.runs_dir = self.root_dir / "runs"
        self.dashboards_dir = self.root_dir / "dashboards"
        self.sandbox_tasks_dir = self.root_dir / "sandbox_tasks"
        self.artifacts_dir = self.root_dir / "artifacts"
        self.initialize()

    def initialize(self) -> None:
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        self.dashboards_dir.mkdir(parents=True, exist_ok=True)
        self.sandbox_tasks_dir.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

    def save_session(self, session: ResearchSession) -> None:
        session.touch()
        self._write_model(self.sessions_dir / f"{session.id}.json", session)

    def load_session(self, session_id: str) -> ResearchSession:
        return self._read_model(self.sessions_dir / f"{session_id}.json", ResearchSession)

    def list_sessions(self) -> list[ResearchSession]:
        return sorted(
            (
                self._read_model(path, ResearchSession)
                for path in self.sessions_dir.glob("*.json")
            ),
            key=lambda session: session.created_at,
        )

    def save_run(self, run: WorkflowRun) -> None:
        run.touch()
        self._write_model(self.runs_dir / f"{run.id}.json", run)

    def load_run(self, run_id: str) -> WorkflowRun:
        return self._read_model(self.runs_dir / f"{run_id}.json", WorkflowRun)

    def list_runs_for_session(self, session_id: str) -> list[WorkflowRun]:
        runs = [
            self._read_model(path, WorkflowRun)
            for path in self.runs_dir.glob("*.json")
        ]
        return sorted(
            (run for run in runs if run.session_id == session_id),
            key=lambda run: run.created_at,
        )

    def save_dashboard_state(self, dashboard_state: DashboardState) -> None:
        dashboard_state.touch()
        self._write_model(
            self.dashboards_dir / f"{dashboard_state.id}.json",
            dashboard_state,
        )

    def load_dashboard_state(self, dashboard_state_id: str) -> DashboardState:
        return self._read_model(
            self.dashboards_dir / f"{dashboard_state_id}.json",
            DashboardState,
        )

    def add_agent_task(self, run_id: str, task: AgentTask) -> WorkflowRun:
        run = self.load_run(run_id)
        run.add_task(task)
        self.save_run(run)
        return run

    def update_agent_task(self, run_id: str, task: AgentTask) -> WorkflowRun:
        return self.add_agent_task(run_id, task)

    def add_sandbox_task(self, run_id: str, sandbox_task: SandboxTask) -> WorkflowRun:
        run = self.load_run(run_id)
        run.add_sandbox_task(sandbox_task.id)
        if sandbox_task.agent_task_id:
            task = run.get_task(sandbox_task.agent_task_id)
            task.add_sandbox_task(sandbox_task.id)
        self.save_run(run)
        self._write_model(
            self.sandbox_tasks_dir / f"{sandbox_task.id}.json",
            sandbox_task,
        )
        return run

    def load_sandbox_task(self, run_id: str, sandbox_task_id: str) -> SandboxTask:
        del run_id
        return self._read_model(
            self.sandbox_tasks_dir / f"{sandbox_task_id}.json",
            SandboxTask,
        )

    def save_sandbox_task(self, sandbox_task: SandboxTask) -> None:
        self._write_model(
            self.sandbox_tasks_dir / f"{sandbox_task.id}.json",
            sandbox_task,
        )

    def add_artifact(self, run_id: str, artifact: SandboxArtifact) -> WorkflowRun:
        run = self.load_run(run_id)
        run.add_artifact(artifact.id)
        if artifact.source_task_id:
            try:
                task = run.get_task(artifact.source_task_id)
                task.add_artifact(artifact.id)
            except KeyError:
                pass
        self.save_run(run)
        self._write_model(
            self.artifacts_dir / f"{artifact.id}.json",
            artifact,
        )
        return run

    def load_artifact(self, run_id: str, artifact_id: str) -> SandboxArtifact:
        del run_id
        return self._read_model(
            self.artifacts_dir / f"{artifact_id}.json",
            SandboxArtifact,
        )

    def approve_run(self, run_id: str, approval: ApprovalRecord) -> WorkflowRun:
        run = self.load_run(run_id)
        run.add_approval(approval)
        self.save_run(run)
        return run

    def checkpoint_run(
        self,
        run_id: str,
        *,
        node_name: str,
        summary: str,
        payload: dict | None = None,
    ) -> WorkflowRun:
        run = self.load_run(run_id)
        run.add_checkpoint(node_name=node_name, summary=summary, payload=payload)
        self.save_run(run)
        return run

    def resume_run(self, run_id: str, *, current_node: str | None = None) -> WorkflowRun:
        run = self.load_run(run_id)
        run.mark_running(current_node=current_node or run.current_node)
        self.save_run(run)
        return run

    def _write_model(self, path: Path, model: object) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            delete=False,
        ) as handle:
            json.dump(
                model.model_dump(mode="json"),
                handle,
                indent=2,
                sort_keys=True,
            )
            handle.flush()
            os.fsync(handle.fileno())
            temp_path = Path(handle.name)
        temp_path.replace(path)

    def _read_model(self, path: Path, model_type: type):
        if not path.exists():
            raise FileNotFoundError(path)
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        return model_type.model_validate(payload)
