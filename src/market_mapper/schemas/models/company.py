"""Company, source, and extracted claim models."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field

from .common import MarketMapperModel, make_id, utc_now


class SourceDocument(MarketMapperModel):
    """Source page or document used during research."""

    id: str = Field(default_factory=lambda: make_id("source"))
    url: str
    title: str | None = None
    source_type: str = "web"
    accessed_at: datetime = Field(default_factory=utc_now)
    snippet: str | None = None
    snapshot_artifact_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExtractedClaim(MarketMapperModel):
    """A structured claim backed by one or more sources."""

    id: str = Field(default_factory=lambda: make_id("claim"))
    label: str
    value: Any
    source_document_ids: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    is_inference: bool = False
    notes: str | None = None


class CompanyCandidate(MarketMapperModel):
    """Candidate company surfaced by discovery before deep research."""

    id: str = Field(default_factory=lambda: make_id("candidate"))
    name: str
    website: str | None = None
    market_category: str | None = None
    rationale: str
    score: float = Field(default=0.0, ge=0.0)
    evidence_source_ids: list[str] = Field(default_factory=list)
    public_signals: dict[str, Any] = Field(default_factory=dict)


class CompanyProfile(MarketMapperModel):
    """Normalized profile used for downstream comparison and reporting."""

    id: str = Field(default_factory=lambda: make_id("company"))
    name: str
    website: str | None = None
    market_category: str | None = None
    product_summary: str | None = None
    target_customers: list[str] = Field(default_factory=list)
    core_features: list[str] = Field(default_factory=list)
    ai_capabilities: list[str] = Field(default_factory=list)
    integrations: list[str] = Field(default_factory=list)
    pricing_model: str | None = None
    public_pricing_details: list[str] = Field(default_factory=list)
    packaging_or_plans: list[str] = Field(default_factory=list)
    positioning_statement: str | None = None
    differentiators: list[str] = Field(default_factory=list)
    customer_proof_points: list[str] = Field(default_factory=list)
    notable_public_metrics: dict[str, Any] = Field(default_factory=dict)
    strengths: list[str] = Field(default_factory=list)
    weaknesses_or_gaps: list[str] = Field(default_factory=list)
    claims: list[ExtractedClaim] = Field(default_factory=list)
    source_document_ids: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    updated_at: datetime = Field(default_factory=utc_now)

    def touch(self) -> None:
        self.updated_at = utc_now()

