"""Chart data shaping and lightweight chart rendering helpers."""

from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape

from market_mapper.schemas.models import ChartSpec, CompanyProfile, ComparisonResult
from market_mapper.schemas.models.common import ArtifactKind
from market_mapper.sandbox.artifacts import register_file_artifact, write_json_artifact


def build_fallback_chart_specs(
    *,
    run_id: str,
    comparison_result: ComparisonResult,
    company_profiles: list[CompanyProfile],
) -> list[ChartSpec]:
    """Create a small, reliable chart set from validated comparison inputs."""

    specs: list[ChartSpec] = []
    if company_profiles:
        specs.append(
            ChartSpec(
                run_id=run_id,
                chart_type="bar",
                title="Research Confidence by Company",
                description="Compares overall profile confidence across the researched companies.",
                data=[
                    {"company": profile.name, "confidence": round(profile.confidence, 2)}
                    for profile in company_profiles
                ],
                x_field="company",
                y_field="confidence",
                comparison_result_id=comparison_result.id,
            )
        )
        specs.append(
            ChartSpec(
                run_id=run_id,
                chart_type="bar",
                title="Source Coverage by Company",
                description="Shows how many traceable public sources support each company profile.",
                data=[
                    {"company": profile.name, "source_count": len(profile.source_document_ids)}
                    for profile in company_profiles
                ],
                x_field="company",
                y_field="source_count",
                comparison_result_id=comparison_result.id,
            )
        )
        specs.append(
            ChartSpec(
                run_id=run_id,
                chart_type="heatmap",
                title="Dimension Coverage Matrix",
                description="Highlights where public evidence exists across the requested comparison dimensions.",
                data=[
                    {
                        "company": profile.name,
                        "dimension": dimension,
                        "coverage": 1 if _profile_has_dimension_data(profile, dimension) else 0,
                    }
                    for profile in company_profiles
                    for dimension in comparison_result.dimensions
                ],
                x_field="dimension",
                y_field="company",
                series_field="coverage",
                comparison_result_id=comparison_result.id,
            )
        )
    return specs


def validate_chart_specs(
    *,
    chart_specs: list[ChartSpec],
    run_id: str,
    comparison_result: ComparisonResult,
) -> list[ChartSpec]:
    """Normalize and filter chart specs into a dashboard-safe set."""

    validated: list[ChartSpec] = []
    seen_titles: set[str] = set()
    for chart_spec in chart_specs:
        if not chart_spec.data:
            continue
        chart_spec.run_id = run_id
        chart_spec.comparison_result_id = comparison_result.id
        chart_spec.chart_type = chart_spec.chart_type.strip().lower()
        title_key = chart_spec.title.strip().lower()
        if not title_key or title_key in seen_titles:
            continue
        seen_titles.add(title_key)
        if chart_spec.chart_type not in {"bar", "grouped_bar", "heatmap", "scorecard"}:
            chart_spec.chart_type = "bar"
        validated.append(chart_spec)
    return validated


def render_chart_artifacts(
    *,
    root_dir: Path,
    chart_specs: list[ChartSpec],
) -> tuple[list, list[dict]]:
    """Render lightweight SVG chart artifacts plus a JSON manifest."""

    artifacts = []
    rendered_charts: list[dict] = []
    for index, chart_spec in enumerate(chart_specs, start=1):
        svg_markup = render_chart_svg(chart_spec)
        filename = f"chart_{index:02d}_{_slugify(chart_spec.title)}.svg"
        svg_path = root_dir / filename
        svg_path.write_text(svg_markup, encoding="utf-8")
        artifacts.append(
            register_file_artifact(
                path=svg_path,
                label=chart_spec.title,
                kind=ArtifactKind.CHART_IMAGE,
                content_type="image/svg+xml",
                metadata={"chart_id": chart_spec.id, "chart_type": chart_spec.chart_type},
            )
        )
        rendered_charts.append(
            {
                "chart_id": chart_spec.id,
                "title": chart_spec.title,
                "artifact_path": str(svg_path),
                "chart_type": chart_spec.chart_type,
            }
        )

    artifacts.append(
        write_json_artifact(
            root_dir=root_dir,
            filename="chart_specs.json",
            label="Chart specs",
            payload=[chart_spec.model_dump(mode="json") for chart_spec in chart_specs],
            metadata={"rendered_chart_count": len(rendered_charts)},
        )
    )
    return artifacts, rendered_charts


def render_chart_svg(chart_spec: ChartSpec) -> str:
    """Render a very small SVG chart for dashboard previews and artifact inspection."""

    if chart_spec.chart_type == "heatmap":
        return _render_heatmap_svg(chart_spec)
    return _render_bar_svg(chart_spec)


def _render_bar_svg(chart_spec: ChartSpec) -> str:
    width = 760
    height = 440
    left = 120
    right = 40
    top = 70
    bottom = 80
    chart_width = width - left - right
    chart_height = height - top - bottom
    y_field = chart_spec.y_field or _first_numeric_field(chart_spec.data) or "value"
    x_field = chart_spec.x_field or _first_text_field(chart_spec.data, exclude={y_field}) or "label"
    values = [float(row.get(y_field, 0) or 0) for row in chart_spec.data]
    max_value = max(values) if values else 1.0
    max_value = max(max_value, 1.0)
    bar_gap = 16
    bar_width = max(32, (chart_width - bar_gap * max(0, len(values) - 1)) / max(1, len(values)))
    bars = []
    labels = []
    for index, row in enumerate(chart_spec.data):
        value = float(row.get(y_field, 0) or 0)
        bar_height = (value / max_value) * chart_height
        x = left + index * (bar_width + bar_gap)
        y = top + (chart_height - bar_height)
        color = "#2F80ED"
        bars.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_width:.1f}" height="{bar_height:.1f}" fill="{color}" rx="4" />')
        labels.append(
            f'<text x="{x + bar_width / 2:.1f}" y="{height - 45}" text-anchor="middle" font-size="12" fill="#1F2937">{escape(str(row.get(x_field, "")))}</text>'
        )
        labels.append(
            f'<text x="{x + bar_width / 2:.1f}" y="{y - 8:.1f}" text-anchor="middle" font-size="12" fill="#1F2937">{escape(str(round(value, 2)))}</text>'
        )
    return _wrap_svg(
        width=width,
        height=height,
        title=chart_spec.title,
        description=chart_spec.description or "",
        body="\n".join(
            [
                f'<line x1="{left}" y1="{top + chart_height}" x2="{width - right}" y2="{top + chart_height}" stroke="#CBD5E1" stroke-width="1" />',
                *bars,
                *labels,
                f'<text x="{left}" y="{top - 20}" font-size="14" fill="#475569">{escape(y_field.replace("_", " ").title())}</text>',
            ]
        ),
    )


def _render_heatmap_svg(chart_spec: ChartSpec) -> str:
    width = 860
    height = 460
    left = 170
    top = 90
    cell_width = 90
    cell_height = 42
    x_field = chart_spec.x_field or "dimension"
    y_field = chart_spec.y_field or "company"
    value_field = chart_spec.series_field or "coverage"
    dimensions = list(dict.fromkeys(str(row.get(x_field, "")) for row in chart_spec.data))
    companies = list(dict.fromkeys(str(row.get(y_field, "")) for row in chart_spec.data))
    lookup = {
        (str(row.get(y_field, "")), str(row.get(x_field, ""))): float(row.get(value_field, 0) or 0)
        for row in chart_spec.data
    }
    cells = []
    labels = []
    for row_index, company in enumerate(companies):
        labels.append(
            f'<text x="{left - 12}" y="{top + row_index * cell_height + 26}" text-anchor="end" font-size="12" fill="#1F2937">{escape(company)}</text>'
        )
        for col_index, dimension in enumerate(dimensions):
            value = lookup.get((company, dimension), 0.0)
            color = "#2F80ED" if value >= 0.99 else "#DCEAFE" if value > 0 else "#F3F4F6"
            x = left + col_index * cell_width
            y = top + row_index * cell_height
            cells.append(f'<rect x="{x}" y="{y}" width="{cell_width - 6}" height="{cell_height - 6}" fill="{color}" rx="4" />')
    for col_index, dimension in enumerate(dimensions):
        labels.append(
            f'<text x="{left + col_index * cell_width + (cell_width - 6)/2:.1f}" y="{top - 15}" text-anchor="middle" font-size="12" fill="#1F2937">{escape(dimension.replace("_", " "))}</text>'
        )
    return _wrap_svg(
        width=width,
        height=height,
        title=chart_spec.title,
        description=chart_spec.description or "",
        body="\n".join([*cells, *labels]),
    )


def _wrap_svg(*, width: int, height: int, title: str, description: str, body: str) -> str:
    return "\n".join(
        [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
            f"<title>{escape(title)}</title>",
            f"<desc>{escape(description)}</desc>",
            f'<rect width="{width}" height="{height}" fill="#FFFFFF" rx="12" />',
            f'<text x="32" y="38" font-size="22" font-weight="700" fill="#111827">{escape(title)}</text>',
            body,
            "</svg>",
        ]
    )


def _first_numeric_field(data: list[dict]) -> str | None:
    if not data:
        return None
    for key in data[0]:
        if isinstance(data[0][key], (int, float)):
            return key
    return None


def _first_text_field(data: list[dict], exclude: set[str]) -> str | None:
    if not data:
        return None
    for key in data[0]:
        if key in exclude:
            continue
        if isinstance(data[0][key], str):
            return key
    return None


def _profile_has_dimension_data(profile: CompanyProfile, dimension: str) -> bool:
    mapping = {
        "pricing": bool(profile.pricing_model or profile.public_pricing_details),
        "features": bool(profile.core_features),
        "positioning": bool(profile.positioning_statement),
        "target_customers": bool(profile.target_customers),
        "integrations": bool(profile.integrations),
        "differentiators": bool(profile.differentiators),
        "strengths": bool(profile.strengths),
        "gaps": bool(profile.weaknesses_or_gaps),
    }
    return mapping.get(dimension, False)


def _slugify(value: str) -> str:
    pieces = [character.lower() if character.isalnum() else "_" for character in value]
    slug = "".join(pieces).strip("_")
    while "__" in slug:
        slug = slug.replace("__", "_")
    return slug[:80] or "chart"
