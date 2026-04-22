"""Approved session state persistence and session-chat orchestration."""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import NamedTemporaryFile

from pydantic import Field

from market_mapper.config.settings import get_settings
from market_mapper.schemas.models import (
    ChartSpec,
    CompanyProfile,
    ComparisonResult,
    DashboardState,
    Report,
    ResearchPlan,
    ResearchSession,
    SourceDocument,
    WorkflowRun,
)
from market_mapper.schemas.models.common import MarketMapperModel, make_id, utc_now


class ApprovedSessionSnapshot(MarketMapperModel):
    """Durable approved session bundle used by the sidebar chatbot."""

    id: str = Field(default_factory=lambda: make_id("approved_session"))
    session_id: str
    run_id: str
    user_prompt: str
    research_plan: ResearchPlan | None = None
    dashboard_state: DashboardState
    executive_summary: str | None = None
    company_profiles: list[CompanyProfile] = Field(default_factory=list)
    comparison_result: ComparisonResult
    report: Report
    chart_specs: list[ChartSpec] = Field(default_factory=list)
    source_documents: list[SourceDocument] = Field(default_factory=list)
    approved_at: str = Field(default_factory=lambda: utc_now().isoformat())


class SessionChatReference(MarketMapperModel):
    """One validated evidence reference attached to a chat answer."""

    reference_type: str
    reference_id: str
    label: str
    url: str | None = None
    snippet: str | None = None


class SessionChatAnswer(MarketMapperModel):
    """One constrained session-chat answer."""

    answer: str
    references: list[SessionChatReference] = Field(default_factory=list)
    citation_ids: list[str] = Field(default_factory=list)
    uncertainty_note: str | None = None


class SessionChatRequest(MarketMapperModel):
    """API payload for one session-chat question."""

    session_id: str
    question: str
    approved_state: ApprovedSessionSnapshot | None = None


class SessionStateService:
    """Persist and load approved session snapshots for session-bound chat."""

    def __init__(self, root_dir: str | Path | None = None) -> None:
        settings = get_settings()
        self.root_dir = Path(root_dir or settings.workflow_state_dir)
        self.snapshots_dir = self.root_dir / "approved_sessions"
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)

    def save_approved_snapshot(
        self,
        *,
        session: ResearchSession,
        run: WorkflowRun,
        dashboard_state: DashboardState,
        company_profiles: list[CompanyProfile],
        comparison_result: ComparisonResult,
        report: Report,
        chart_specs: list[ChartSpec],
        source_documents: list[SourceDocument],
    ) -> ApprovedSessionSnapshot:
        snapshot = ApprovedSessionSnapshot(
            session_id=session.id,
            run_id=run.id,
            user_prompt=session.user_prompt,
            research_plan=session.research_plan,
            dashboard_state=dashboard_state,
            executive_summary=dashboard_state.executive_summary or report.executive_summary,
            company_profiles=company_profiles,
            comparison_result=comparison_result,
            report=report,
            chart_specs=chart_specs,
            source_documents=source_documents,
        )
        path = self.snapshots_dir / f"{session.id}.json"
        self._write_model(path, snapshot)
        return snapshot

    def load_approved_snapshot(self, session_id: str) -> ApprovedSessionSnapshot:
        return self._read_model(
            self.snapshots_dir / f"{session_id}.json",
            ApprovedSessionSnapshot,
        )

    def resolve_chat_request(self, request: SessionChatRequest) -> ApprovedSessionSnapshot:
        if request.approved_state is not None:
            if request.approved_state.session_id != request.session_id:
                raise ValueError("approved_state.session_id must match session_id")
            return request.approved_state
        return self.load_approved_snapshot(request.session_id)

    def _write_model(self, path: Path, model: MarketMapperModel) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            delete=False,
        ) as handle:
            json.dump(model.model_dump(mode="json"), handle, indent=2, sort_keys=True)
            temp_path = Path(handle.name)
        temp_path.replace(path)

    def _read_model(self, path: Path, model_type: type[ApprovedSessionSnapshot]) -> ApprovedSessionSnapshot:
        if not path.exists():
            raise FileNotFoundError(path)
        return model_type.model_validate_json(path.read_text(encoding="utf-8"))
