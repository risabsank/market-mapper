"""OpenAI-powered Structured Extraction Agent implementation."""

from __future__ import annotations

from pathlib import Path

from market_mapper.research import normalize_url
from market_mapper.schemas.models import CompanyProfile, ExtractedClaim, SourceDocument
from market_mapper.services import generate_structured_output, render_agent_input
from market_mapper.workflow.contracts import (
    StructuredExtractionNodeInput,
    StructuredExtractionNodeOutput,
)

STRUCTURED_EXTRACTION_SYSTEM_PROMPT = """
You are the Structured Extraction Agent for Market Mapper.

Turn discovery candidates and source documents into normalized company profiles.

Rules:
- Use source-backed information when possible.
- If a field is unavailable, leave it empty rather than inventing data.
- Record explicit missing fields for important categories that could not be verified.
- Keep claims concise, structured, and tied to source_document_ids.
- Confidence should reflect how grounded the information appears.
"""


def run_structured_extraction(
    node_input: StructuredExtractionNodeInput,
) -> StructuredExtractionNodeOutput:
    """Create validated company profiles from sandbox-captured research inputs."""

    source_context = _build_source_context(node_input.source_documents)

    response = generate_structured_output(
        response_model=StructuredExtractionNodeOutput,
        system_prompt=STRUCTURED_EXTRACTION_SYSTEM_PROMPT,
        user_input=render_agent_input(
            task_description="Normalize the research inputs into structured company profiles.",
            context={
                "run_id": node_input.run_id,
                "company_candidates": [
                    candidate.model_dump(mode="json")
                    for candidate in node_input.company_candidates
                ],
                "source_documents": [
                    packet
                    for packet in source_context
                ],
                "existing_profiles": [
                    profile.model_dump(mode="json")
                    for profile in node_input.existing_profiles
                ],
            },
        ),
    )
    response.company_profiles = _validate_company_profiles(
        company_profiles=response.company_profiles,
        company_candidates=node_input.company_candidates,
        source_documents=node_input.source_documents,
    )
    response.summary = (
        f"Structured extraction produced {len(response.company_profiles)} validated company profiles."
    )
    response.next_route = "executor"
    return response


def _build_source_context(source_documents: list[SourceDocument]) -> list[dict]:
    packets: list[dict] = []
    for document in source_documents:
        metadata = dict(document.metadata)
        extracted_text_path = metadata.get("extracted_text_path")
        extracted_text = _read_optional_text(extracted_text_path)
        packets.append(
            {
                "id": document.id,
                "url": document.url,
                "title": document.title,
                "source_type": document.source_type,
                "snippet": document.snippet,
                "company_name": metadata.get("company_name"),
                "source_rationale": metadata.get("source_rationale"),
                "headings": metadata.get("headings", []),
                "word_count": metadata.get("word_count"),
                "status_code": metadata.get("status_code"),
                "extracted_text": extracted_text,
            }
        )
    return packets


def _read_optional_text(path_value: str | None) -> str | None:
    if not path_value:
        return None
    path = Path(path_value)
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")


def _validate_company_profiles(
    *,
    company_profiles: list[CompanyProfile],
    company_candidates,
    source_documents: list[SourceDocument],
) -> list[CompanyProfile]:
    candidate_by_name = {
        candidate.name.strip().lower(): candidate
        for candidate in company_candidates
    }
    valid_source_ids = {document.id for document in source_documents}
    source_ids_by_company = _source_ids_by_company(source_documents)
    validated_profiles: list[CompanyProfile] = []
    seen_company_names: set[str] = set()

    for profile in company_profiles:
        company_key = profile.name.strip().lower()
        if not company_key or company_key in seen_company_names:
            continue
        candidate = candidate_by_name.get(company_key)
        if candidate and not profile.website:
            profile.website = candidate.website
        profile.website = normalize_url(profile.website) or profile.website
        profile.source_document_ids = _normalize_source_ids(
            profile.source_document_ids,
            valid_source_ids=valid_source_ids,
            fallback_source_ids=source_ids_by_company.get(company_key, []),
        )
        profile.claims = _validate_claims(
            profile.claims,
            valid_source_ids=valid_source_ids,
            fallback_source_ids=profile.source_document_ids,
        )
        profile.explicit_missing_fields = _compute_missing_fields(profile)
        if not profile.source_document_ids:
            profile.source_document_ids = [
                claim_source_id
                for claim in profile.claims
                for claim_source_id in claim.source_document_ids
            ]
        profile.source_document_ids = list(dict.fromkeys(profile.source_document_ids))
        claim_confidences = [claim.confidence for claim in profile.claims if claim.source_document_ids]
        if claim_confidences:
            average_confidence = sum(claim_confidences) / len(claim_confidences)
            profile.confidence = round(max(0.1, min(1.0, average_confidence)), 2)
        elif profile.source_document_ids:
            profile.confidence = max(0.3, min(1.0, round(profile.confidence, 2)))
        else:
            profile.confidence = min(profile.confidence, 0.2)
        profile.touch()
        validated_profiles.append(CompanyProfile.model_validate(profile.model_dump(mode="json")))
        seen_company_names.add(company_key)

    for company_key, candidate in candidate_by_name.items():
        if company_key in seen_company_names:
            continue
        fallback_profile = CompanyProfile(
            name=candidate.name,
            website=normalize_url(candidate.website) or candidate.website,
            market_category=candidate.market_category,
            source_document_ids=list(
                dict.fromkeys(source_ids_by_company.get(company_key, []))
            ),
            confidence=0.15 if source_ids_by_company.get(company_key) else 0.05,
        )
        fallback_profile.explicit_missing_fields = _compute_missing_fields(fallback_profile)
        fallback_profile.touch()
        validated_profiles.append(fallback_profile)

    return validated_profiles


def _source_ids_by_company(source_documents: list[SourceDocument]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    for document in source_documents:
        company_name = str(document.metadata.get("company_name", "")).strip().lower()
        if not company_name:
            continue
        grouped.setdefault(company_name, []).append(document.id)
    return grouped


def _normalize_source_ids(
    source_ids: list[str],
    *,
    valid_source_ids: set[str],
    fallback_source_ids: list[str],
) -> list[str]:
    normalized = [source_id for source_id in source_ids if source_id in valid_source_ids]
    if normalized:
        return list(dict.fromkeys(normalized))
    return list(dict.fromkeys([source_id for source_id in fallback_source_ids if source_id in valid_source_ids]))


def _validate_claims(
    claims: list[ExtractedClaim],
    *,
    valid_source_ids: set[str],
    fallback_source_ids: list[str],
) -> list[ExtractedClaim]:
    validated_claims: list[ExtractedClaim] = []
    for claim in claims:
        claim.source_document_ids = _normalize_source_ids(
            claim.source_document_ids,
            valid_source_ids=valid_source_ids,
            fallback_source_ids=fallback_source_ids,
        )
        if not claim.source_document_ids:
            continue
        claim.confidence = max(0.0, min(1.0, claim.confidence))
        validated_claims.append(
            ExtractedClaim.model_validate(claim.model_dump(mode="json"))
        )
    return validated_claims


def _compute_missing_fields(profile: CompanyProfile) -> list[str]:
    required_fields = {
        "product_summary": profile.product_summary,
        "target_customers": profile.target_customers,
        "core_features": profile.core_features,
        "ai_capabilities": profile.ai_capabilities,
        "integrations": profile.integrations,
        "pricing_model": profile.pricing_model,
        "public_pricing_details": profile.public_pricing_details,
        "packaging_or_plans": profile.packaging_or_plans,
        "positioning_statement": profile.positioning_statement,
        "differentiators": profile.differentiators,
        "customer_proof_points": profile.customer_proof_points,
        "strengths": profile.strengths,
        "weaknesses_or_gaps": profile.weaknesses_or_gaps,
    }
    missing = []
    for field_name, value in required_fields.items():
        if value is None:
            missing.append(field_name)
        elif isinstance(value, str) and not value.strip():
            missing.append(field_name)
        elif isinstance(value, list) and not value:
            missing.append(field_name)
    return missing
