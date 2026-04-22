"""Comparison, verification, chart, and report models."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field

from .common import MarketMapperModel, VerificationSeverity, make_id, utc_now


class ComparisonFinding(MarketMapperModel):
    """One comparison result for a given dimension."""

    dimension: str
    summary: str
    winner_company_id: str | None = None
    evidence_claim_ids: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class ComparisonResult(MarketMapperModel):
    """Aggregate competitive analysis output."""

    id: str = Field(default_factory=lambda: make_id("comparison"))
    run_id: str
    company_ids: list[str] = Field(default_factory=list)
    dimensions: list[str] = Field(default_factory=list)
    findings: list[ComparisonFinding] = Field(default_factory=list)
    similarities: list[str] = Field(default_factory=list)
    differences: list[str] = Field(default_factory=list)
    tradeoffs: list[str] = Field(default_factory=list)
    ideal_customer_notes: list[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=utc_now)


class VerificationIssue(MarketMapperModel):
    """Issue raised during verification."""

    severity: VerificationSeverity
    message: str
    agent_task_id: str | None = None
    company_id: str | None = None
    fix_target: str | None = None


class VerificationResult(MarketMapperModel):
    """Review output that determines whether the workflow can proceed."""

    id: str = Field(default_factory=lambda: make_id("verification"))
    run_id: str
    approved: bool = False
    requires_retry: bool = False
    issues: list[VerificationIssue] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    reviewed_at: datetime = Field(default_factory=utc_now)


class ChartSpec(MarketMapperModel):
    """Chart-ready payload plus metadata for rendering."""

    id: str = Field(default_factory=lambda: make_id("chart"))
    run_id: str
    chart_type: str
    title: str
    description: str | None = None
    data: list[dict[str, Any]] = Field(default_factory=list)
    x_field: str | None = None
    y_field: str | None = None
    series_field: str | None = None
    comparison_result_id: str | None = None
    artifact_id: str | None = None
    created_at: datetime = Field(default_factory=utc_now)


class ReportSection(MarketMapperModel):
    """One section of the generated report."""

    heading: str
    body: str
    citation_ids: list[str] = Field(default_factory=list)


class Report(MarketMapperModel):
    """Generated report and its Markdown payload."""

    id: str = Field(default_factory=lambda: make_id("report"))
    run_id: str
    title: str
    executive_summary: str
    sections: list[ReportSection] = Field(default_factory=list)
    markdown_body: str
    source_document_ids: list[str] = Field(default_factory=list)
    artifact_id: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
