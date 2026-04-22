"""OpenAI-powered Web Research Agent implementation."""

from __future__ import annotations

from market_mapper.research import normalize_url
from market_mapper.services import generate_structured_output, render_agent_input
from market_mapper.workflow.contracts import WebResearchNodeInput, WebResearchNodeOutput

WEB_RESEARCH_SYSTEM_PROMPT = """
You are the Web Research Agent for Market Mapper.

Collect source documents that are likely to support downstream extraction and comparison.

Rules:
- Prefer official company websites and product pages.
- Include the official homepage for each selected company when possible.
- Include additional useful public sources such as pricing pages, docs, integration pages,
  knowledge-base pages, or credible public writeups that support downstream extraction.
- Include titles and short snippets when possible.
- Return source documents only; do not summarize the full market yet.
- Use public web knowledge and web search when available.
"""


def run_web_research(node_input: WebResearchNodeInput) -> WebResearchNodeOutput:
    """Return OpenAI-generated source plans for downstream sandbox capture."""

    response = generate_structured_output(
        response_model=WebResearchNodeOutput,
        system_prompt=WEB_RESEARCH_SYSTEM_PROMPT,
        user_input=render_agent_input(
            task_description="Collect public source documents for the selected companies.",
            context={
                "run_id": node_input.run_id,
                "research_plan": node_input.research_plan.model_dump(mode="json"),
                "company_candidates": [
                    candidate.model_dump(mode="json")
                    for candidate in node_input.company_candidates
                ],
                "existing_documents": [
                    document.model_dump(mode="json")
                    for document in node_input.existing_documents
                ],
            },
        ),
        use_web_search=True,
    )
    response.source_documents = _normalize_source_documents(
        source_documents=response.source_documents,
        company_names=[candidate.name for candidate in node_input.company_candidates],
    )
    response.summary = (
        f"Web research planned {len(response.source_documents)} source targets for sandbox capture."
    )
    response.next_route = "executor"
    return response


def _normalize_source_documents(
    *,
    source_documents,
    company_names: list[str],
):
    known_company_names = {name.strip().lower(): name for name in company_names}
    deduped = {}
    for document in source_documents:
        normalized_url = normalize_url(document.url)
        if not normalized_url:
            continue
        document.url = normalized_url
        metadata = dict(document.metadata)
        company_name = str(metadata.get("company_name", "")).strip().lower()
        if not company_name and len(company_names) == 1:
            metadata["company_name"] = company_names[0]
        elif company_name in known_company_names:
            metadata["company_name"] = known_company_names[company_name]
        document.metadata = metadata
        deduped[normalized_url] = document
    return list(deduped.values())
