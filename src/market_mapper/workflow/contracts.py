"""Typed workflow node inputs and outputs."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from market_mapper.schemas.models import (
    ChartSpec,
    CompanyCandidate,
    CompanyProfile,
    ComparisonResult,
    DashboardState,
    Report,
    ResearchPlan,
    SandboxArtifact,
    SandboxTask,
    SourceDocument,
    VerificationResult,
)
from market_mapper.schemas.models.common import MarketMapperModel
from market_mapper.workflow.state import ResearchWorkflowState

WorkflowRoute = Literal[
    "planner",
    "executor",
    "company_discovery",
    "web_research",
    "structured_extraction",
    "comparison",
    "critic_verifier",
    "report_generation",
    "chart_generation",
    "dashboard_builder",
    "session_chatbot",
    "end",
]


class WorkflowNodeOutput(MarketMapperModel):
    """Base output returned by every workflow node."""

    next_route: WorkflowRoute
    summary: str
    used_sandbox: bool = False


class PlannerNodeInput(MarketMapperModel):
    session_id: str
    user_prompt: str
    existing_plan: ResearchPlan | None = None


class PlannerNodeOutput(WorkflowNodeOutput):
    research_plan: ResearchPlan
    assumptions: list[str] = Field(default_factory=list)


class ExecutorNodeInput(MarketMapperModel):
    state: ResearchWorkflowState
    current_node: str


class ExecutorNodeOutput(WorkflowNodeOutput):
    current_node: str


class CompanyDiscoveryNodeInput(MarketMapperModel):
    run_id: str
    research_plan: ResearchPlan
    existing_candidates: list[CompanyCandidate] = Field(default_factory=list)


class CompanyDiscoveryNodeOutput(WorkflowNodeOutput):
    company_candidates: list[CompanyCandidate] = Field(default_factory=list)


class WebResearchNodeInput(MarketMapperModel):
    run_id: str
    research_plan: ResearchPlan
    company_candidates: list[CompanyCandidate] = Field(default_factory=list)
    existing_documents: list[SourceDocument] = Field(default_factory=list)


class WebResearchNodeOutput(WorkflowNodeOutput):
    source_documents: list[SourceDocument] = Field(default_factory=list)


class StructuredExtractionNodeInput(MarketMapperModel):
    run_id: str
    company_candidates: list[CompanyCandidate] = Field(default_factory=list)
    source_documents: list[SourceDocument] = Field(default_factory=list)
    existing_profiles: list[CompanyProfile] = Field(default_factory=list)


class StructuredExtractionNodeOutput(WorkflowNodeOutput):
    company_profiles: list[CompanyProfile] = Field(default_factory=list)


class ComparisonNodeInput(MarketMapperModel):
    run_id: str
    research_plan: ResearchPlan
    company_profiles: list[CompanyProfile] = Field(default_factory=list)


class ComparisonNodeOutput(WorkflowNodeOutput):
    comparison_result: ComparisonResult


class CriticVerifierNodeInput(MarketMapperModel):
    run_id: str
    research_plan: ResearchPlan
    company_profiles: list[CompanyProfile] = Field(default_factory=list)
    comparison_result: ComparisonResult


class CriticVerifierNodeOutput(WorkflowNodeOutput):
    verification_result: VerificationResult


class ReportGenerationNodeInput(MarketMapperModel):
    run_id: str
    research_plan: ResearchPlan
    company_profiles: list[CompanyProfile] = Field(default_factory=list)
    comparison_result: ComparisonResult
    source_documents: list[SourceDocument] = Field(default_factory=list)


class ReportGenerationNodeOutput(WorkflowNodeOutput):
    report: Report


class ChartGenerationNodeInput(MarketMapperModel):
    run_id: str
    comparison_result: ComparisonResult
    existing_chart_specs: list[ChartSpec] = Field(default_factory=list)
    existing_artifacts: list[SandboxArtifact] = Field(default_factory=list)
    existing_sandbox_tasks: list[SandboxTask] = Field(default_factory=list)


class ChartGenerationNodeOutput(WorkflowNodeOutput):
    chart_specs: list[ChartSpec] = Field(default_factory=list)


class DashboardBuilderNodeInput(MarketMapperModel):
    session_id: str
    run_id: str
    company_profiles: list[CompanyProfile] = Field(default_factory=list)
    comparison_result: ComparisonResult
    report: Report
    chart_specs: list[ChartSpec] = Field(default_factory=list)
    source_documents: list[SourceDocument] = Field(default_factory=list)


class DashboardBuilderNodeOutput(WorkflowNodeOutput):
    dashboard_state: DashboardState


class SessionChatbotNodeInput(MarketMapperModel):
    session_id: str
    run_id: str
    dashboard_state: DashboardState


class SessionChatbotNodeOutput(WorkflowNodeOutput):
    chat_ready: bool
