const DEFAULT_CHAT_SUGGESTIONS = [
  "Which company looks strongest for enterprise support teams?",
  "Where is pricing transparency strongest or weakest?",
  "Which parts of this comparison are the least certain?",
];

const RUN_POLL_INTERVAL_MS = 3000;
const RUN_POLL_ATTEMPTS = 20;

const state = {
  theme: localStorage.getItem("market-mapper-theme") || "light",
  chatCollapsed: false,
  sessionId: null,
  session: null,
  runStatus: null,
  dashboard: null,
  loading: true,
  error: null,
  thread: [],
};

initialize().catch((error) => {
  console.error(error);
  showErrorState("Unable to load dashboard", error.message || "The dashboard could not be loaded.");
});

async function initialize() {
  applyTheme(state.theme);
  bindEvents();
  renderDashboard();
  await loadDashboard();
}

function bindEvents() {
  document.getElementById("theme-toggle").addEventListener("click", toggleTheme);
  document.getElementById("chat-toggle").addEventListener("click", toggleChat);
  document.getElementById("download-report").addEventListener("click", downloadMarkdown);
  document.getElementById("chat-form").addEventListener("submit", handleChatSubmit);
  document.getElementById("app-state-retry").addEventListener("click", () => {
    loadDashboard().catch((error) => {
      console.error(error);
      showErrorState("Unable to reload dashboard", error.message || "The dashboard could not be reloaded.");
    });
  });

  document.querySelectorAll(".nav-item").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelectorAll(".nav-item").forEach((item) => item.classList.remove("is-active"));
      button.classList.add("is-active");
      document.getElementById(button.dataset.target)?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  });
}

async function loadDashboard() {
  state.loading = true;
  state.error = null;
  renderAppState({
    eyebrow: "Loading",
    title: "Fetching session data",
    body: "Looking up the current session, run state, and approved dashboard payload.",
    showRetry: false,
  });
  renderDashboard();

  const sessionId = resolveSessionId();
  if (!sessionId) {
    showErrorState(
      "No session selected",
      "Open the dashboard with a `session_id` query parameter, or create a session and run through the backend API first."
    );
    return;
  }

  state.sessionId = sessionId;
  state.session = await fetchJson(`/api/sessions/${encodeURIComponent(sessionId)}`);
  if (state.session?.id) {
    storeSessionId(state.session.id);
  }
  state.runStatus = state.session.active_run_id
    ? await fetchRunStatus(state.session.active_run_id)
    : null;

  const snapshot = await waitForApprovedDashboard(sessionId);
  state.dashboard = mapSnapshotToDashboard({
    session: state.session,
    runStatus: state.runStatus,
    snapshot,
  });
  state.thread = [
    {
      role: "assistant",
      text:
        "This panel stays inside the approved research for the current session. Ask about pricing, differentiators, sources, or uncertainty and I’ll answer from the saved dashboard state.",
      references: [],
      citations: [],
      uncertainty: null,
    },
  ];
  state.loading = false;
  hideAppState();
  renderDashboard();
}

async function waitForApprovedDashboard(sessionId) {
  for (let attempt = 0; attempt < RUN_POLL_ATTEMPTS; attempt += 1) {
    try {
      return await fetchJson(`/api/sessions/${encodeURIComponent(sessionId)}/dashboard`);
    } catch (error) {
      if (error.status !== 404) {
        throw error;
      }
      state.runStatus = state.session?.active_run_id
        ? await fetchRunStatus(state.session.active_run_id)
        : state.runStatus;
      if (!state.runStatus || !isRunPending(state.runStatus.run.status)) {
        throw new Error("No approved dashboard is available for this session yet.");
      }
      renderAppState({
        eyebrow: "Running",
        title: "Research is still in progress",
        body: buildRunProgressMessage(state.runStatus),
        showRetry: false,
      });
      renderDashboard();
      await sleep(RUN_POLL_INTERVAL_MS);
    }
  }
  throw new Error("Timed out while waiting for the approved dashboard payload.");
}

function renderDashboard() {
  const dashboard = state.dashboard;
  document.getElementById("run-status-label").textContent = dashboard?.session.status || "Waiting for session";
  document.getElementById("prompt-title").textContent = dashboard?.session.prompt || "Market Mapper Dashboard";
  document.getElementById("hero-heading").textContent = dashboard?.plan.marketQuery || "No approved dashboard loaded";
  document.getElementById("hero-summary").textContent =
    dashboard?.session.promptSummary ||
    "This dashboard will populate once the approved session state is available from the backend.";
  document.getElementById("metric-company-count").textContent = String(dashboard?.companies.length || 0);
  document.getElementById("metric-source-count").textContent = String(dashboard?.sources.length || 0);
  document.getElementById("metric-chart-count").textContent = String(dashboard?.charts.length || 0);
  document.getElementById("plan-company-count").textContent = dashboard
    ? `${dashboard.plan.requestedCompanyCount} companies`
    : "No plan yet";
  document.getElementById("executive-summary").textContent =
    dashboard?.executiveSummary || "The executive summary will appear here when the approved dashboard is ready.";

  populateList("discovery-criteria", dashboard?.plan.discoveryCriteria || []);
  populateTagList("comparison-dimensions", dashboard?.plan.comparisonDimensions || []);
  populateList("plan-assumptions", dashboard?.plan.assumptions || []);
  populateList("key-takeaways", dashboard?.keyTakeaways || []);
  populateList("tradeoffs", dashboard?.tradeoffs || []);

  renderConfidencePanel();
  renderCompanyCards();
  renderPricingCards();
  renderComparisonTable();
  renderFeatureMatrix();
  renderCharts();
  renderSources();
  renderChatSuggestions();
  renderChatThread();
  renderMarkdownPreview();
  syncControlState();
}

function renderConfidencePanel() {
  const companies = state.dashboard?.companies || [];
  const averageConfidence = companies.length
    ? companies.reduce((sum, company) => sum + company.confidence, 0) / companies.length
    : 0;
  const percentage = Math.round(averageConfidence * 100);
  document.getElementById("confidence-value").textContent = `${percentage}%`;
  const circumference = 2 * Math.PI * 48;
  const offset = circumference * (1 - averageConfidence);
  document.getElementById("ring-progress").style.strokeDasharray = `${circumference}`;
  document.getElementById("ring-progress").style.strokeDashoffset = `${offset}`;

  const strongCoverageCount = companies.filter((company) => company.confidence >= 0.8).length;
  const uncertainCompanyCount = companies.filter((company) => company.missing.length > 0).length;
  populateList("confidence-notes", [
    companies.length
      ? `${strongCoverageCount} companies have strong public evidence coverage.`
      : "No company evidence has been loaded yet.",
    `${uncertainCompanyCount} companies still have at least one uncertain area.`,
    state.dashboard?.plan.comparisonDimensions.includes("pricing")
      ? "Pricing remains one of the least evenly documented dimensions in most markets."
      : "Confidence notes will become more specific once the market data is available.",
  ]);
}

function renderCompanyCards() {
  const container = document.getElementById("company-cards");
  const companies = state.dashboard?.companies || [];
  container.innerHTML = companies.length
    ? companies
        .map(
          (company) => `
            <article class="company-card">
              <p class="eyebrow">${escapeHtml(company.targetCustomers.join(" / ") || "Unknown target")}</p>
              <h4>${escapeHtml(company.name)}</h4>
              <p class="muted-copy">${escapeHtml(company.positioning || "No positioning summary available.")}</p>
              <div class="company-meta">
                <span class="meta-chip">${Math.round(company.confidence * 100)}% confidence</span>
                <span class="coverage-chip">${company.sources.length} sources</span>
                ${company.missing.length ? `<span class="missing-chip">${company.missing.length} uncertain areas</span>` : ""}
              </div>
            </article>
          `
        )
        .join("")
    : `<article class="company-card"><p class="muted-copy">Selected companies will appear here once the dashboard has loaded.</p></article>`;
}

function renderPricingCards() {
  const container = document.getElementById("pricing-cards");
  const companies = state.dashboard?.companies || [];
  container.innerHTML = companies.length
    ? companies
        .map(
          (company) => `
            <article class="pricing-card">
              <p class="eyebrow">${escapeHtml(company.name)}</p>
              <h4>${escapeHtml(company.pricingModel || "Pricing not publicly disclosed")}</h4>
              <div class="bullet-list">
                ${(company.publicPricingDetails.length
                  ? company.publicPricingDetails
                  : ["No detailed public pricing information is available."]
                )
                  .map((detail) => `<div>${escapeHtml(detail)}</div>`)
                  .join("")}
              </div>
              ${
                !company.publicPricingDetails.length ||
                (company.pricingModel || "").toLowerCase().includes("sales")
                  ? `<p class="warning-text" style="margin-top:12px;">Pricing evidence is incomplete or sales-led.</p>`
                  : ""
              }
            </article>
          `
        )
        .join("")
    : `<article class="pricing-card"><p class="muted-copy">Pricing comparisons will appear here once the dashboard has loaded.</p></article>`;
}

function renderComparisonTable() {
  const table = document.getElementById("comparison-table");
  const columns = ["Company", "Positioning", "Target Customers", "Differentiators", "Strengths", "Gaps"];
  table.querySelector("thead").innerHTML = `<tr>${columns.map((column) => `<th>${escapeHtml(column)}</th>`).join("")}</tr>`;
  const companies = state.dashboard?.companies || [];
  table.querySelector("tbody").innerHTML = companies.length
    ? companies
        .map(
          (company) => `
            <tr>
              <td><strong>${escapeHtml(company.name)}</strong></td>
              <td>${escapeHtml(company.positioning || "Not available")}</td>
              <td>${escapeHtml(company.targetCustomers.join(", ") || "Not available")}</td>
              <td>${escapeHtml(company.differentiators.join(", ") || "Not available")}</td>
              <td>${escapeHtml(company.strengths.join(", ") || "Not available")}</td>
              <td>${escapeHtml(company.gaps.join(", ") || "Not available")}</td>
            </tr>
          `
        )
        .join("")
    : `<tr><td colspan="${columns.length}">No comparison data is available yet.</td></tr>`;
}

function renderFeatureMatrix() {
  const table = document.getElementById("feature-matrix");
  const companies = state.dashboard?.companies || [];
  const features = Array.from(new Set(companies.flatMap((company) => company.coreFeatures)));
  table.querySelector("thead").innerHTML = `
    <tr>
      <th>Feature</th>
      ${companies.map((company) => `<th>${escapeHtml(company.name)}</th>`).join("")}
    </tr>
  `;
  table.querySelector("tbody").innerHTML =
    companies.length && features.length
      ? features
          .map(
            (feature) => `
              <tr>
                <td><strong>${escapeHtml(feature)}</strong></td>
                ${companies
                  .map((company) => {
                    const hasFeature = company.coreFeatures.includes(feature);
                    return `<td><span class="feature-cell ${hasFeature ? "" : "is-missing"}">${hasFeature ? "Supported" : "Not clear"}</span></td>`;
                  })
                  .join("")}
              </tr>
            `
          )
          .join("")
      : `<tr><td colspan="${Math.max(companies.length + 1, 2)}">No feature matrix is available yet.</td></tr>`;
}

function renderCharts() {
  const container = document.getElementById("chart-grid");
  const charts = state.dashboard?.charts || [];
  container.innerHTML = charts.length
    ? charts
        .map((chart) => {
          const svgDataUrl = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(chart.artifactSvg)}`;
          return `
            <article class="chart-card">
              <p class="eyebrow">${escapeHtml(chart.type)}</p>
              <h4>${escapeHtml(chart.title)}</h4>
              <p class="muted-copy" style="margin:8px 0 14px;">${escapeHtml(chart.description || "Chart artifact generated from the approved session state.")}</p>
              <img src="${svgDataUrl}" alt="${escapeAttribute(chart.title)}" />
            </article>
          `;
        })
        .join("")
    : `<article class="chart-card"><p class="muted-copy">Charts will appear here when chart-ready data is available.</p></article>`;
}

function renderSources() {
  const container = document.getElementById("source-list");
  const sources = state.dashboard?.sources || [];
  container.innerHTML = sources.length
    ? sources
        .map(
          (source) => `
            <article class="source-card">
              <p class="eyebrow">${escapeHtml(source.company || "Source")}</p>
              <h4><a href="${escapeAttribute(source.url)}" target="_blank" rel="noreferrer">${escapeHtml(source.title || source.id)}</a></h4>
              <p class="source-snippet">${escapeHtml(source.snippet || "No source snippet available.")}</p>
              <div class="source-meta">
                <span class="meta-chip">${escapeHtml(source.id)}</span>
                <span class="meta-chip">${escapeHtml((source.sourceType || "web").replaceAll("_", " "))}</span>
              </div>
            </article>
          `
        )
        .join("")
    : `<article class="source-card"><p class="muted-copy">Source references will appear here once the approved dashboard is ready.</p></article>`;
}

function renderChatSuggestions() {
  const container = document.getElementById("chat-suggestions");
  const suggestions = state.dashboard?.chatSuggestions || DEFAULT_CHAT_SUGGESTIONS;
  container.innerHTML = suggestions
    .map(
      (suggestion) => `
        <button class="suggestion-card ghost-button" type="button" data-suggestion="${escapeAttribute(suggestion)}">
          ${escapeHtml(suggestion)}
        </button>
      `
    )
    .join("");
  container.querySelectorAll("[data-suggestion]").forEach((button) => {
    button.addEventListener("click", () => {
      document.getElementById("chat-input").value = button.dataset.suggestion;
      document.getElementById("chat-form").requestSubmit();
    });
  });
}

function renderChatThread() {
  const container = document.getElementById("chat-thread");
  container.innerHTML = state.thread
    .map(
      (item) => `
        <article class="chat-bubble ${item.role}">
          <strong>${item.role === "assistant" ? "Market Mapper" : "You"}</strong>
          <p style="margin:8px 0 0;">${escapeHtml(item.text)}</p>
          ${
            item.references?.length
              ? `<p class="muted-copy" style="margin:10px 0 0;">Evidence: ${item.references
                  .map((reference) => formatChatReference(reference))
                  .join(", ")}</p>`
              : item.citations?.length
              ? `<p class="muted-copy" style="margin:10px 0 0;">Sources: ${item.citations
                  .map((citationId) => {
                    const source = (state.dashboard?.sources || []).find((entry) => entry.id === citationId);
                    return source
                      ? `<a href="${escapeAttribute(source.url)}" target="_blank" rel="noreferrer">\`${escapeHtml(
                          citationId
                        )}\`</a>`
                      : `\`${escapeHtml(citationId)}\``;
                  })
                  .join(", ")}</p>`
              : ""
          }
          ${item.uncertainty ? `<p class="warning-text" style="margin:8px 0 0;">${escapeHtml(item.uncertainty)}</p>` : ""}
        </article>
      `
    )
    .join("");
}

function renderMarkdownPreview() {
  document.getElementById("markdown-preview").textContent =
    state.dashboard?.report.markdown || "Markdown export will appear here once the report is ready.";
}

async function handleChatSubmit(event) {
  event.preventDefault();
  const input = document.getElementById("chat-input");
  const question = input.value.trim();
  if (!question || !state.sessionId) {
    return;
  }

  state.thread.push({ role: "user", text: question, references: [], citations: [], uncertainty: null });
  renderChatThread();
  input.value = "";

  try {
    const answer = await askSessionChat(question);
    state.thread.push({
      role: "assistant",
      text: answer.answer,
      references: answer.references || [],
      citations: answer.citation_ids || [],
      uncertainty: answer.uncertainty_note || null,
    });
  } catch (error) {
    state.thread.push({
      role: "assistant",
      text: "I couldn't reach the session chat service for this dashboard.",
      references: [],
      citations: [],
      uncertainty: error.message || "Please retry once the backend is available.",
    });
  }
  renderChatThread();
}

async function askSessionChat(question) {
  const response = await fetch("/api/chat/answer", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      session_id: state.sessionId,
      question,
    }),
  });
  if (!response.ok) {
    throw new Error(`Chat request failed with status ${response.status}`);
  }
  return response.json();
}

function toggleTheme() {
  state.theme = state.theme === "light" ? "dark" : "light";
  applyTheme(state.theme);
}

function applyTheme(theme) {
  document.body.dataset.theme = theme;
  localStorage.setItem("market-mapper-theme", theme);
  const button = document.getElementById("theme-toggle");
  if (button) {
    const isDark = theme === "dark";
    button.textContent = isDark ? "Light mode" : "Dark mode";
    button.setAttribute("aria-pressed", String(isDark));
  }
}

function toggleChat() {
  state.chatCollapsed = !state.chatCollapsed;
  document.body.dataset.chatCollapsed = String(state.chatCollapsed);
  const button = document.getElementById("chat-toggle");
  button.textContent = state.chatCollapsed ? "Show Chat" : "Hide Chat";
  button.setAttribute("aria-expanded", String(!state.chatCollapsed));
}

function downloadMarkdown() {
  const reportId = state.dashboard?.report.id;
  if (reportId) {
    window.location.href = `/api/reports/${encodeURIComponent(reportId)}/download`;
    return;
  }
  const blob = new Blob([state.dashboard?.report.markdown || ""], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = "market-mapper-report.md";
  anchor.click();
  URL.revokeObjectURL(url);
}

function renderAppState({ eyebrow, title, body, showRetry }) {
  const panel = document.getElementById("app-state-panel");
  panel.hidden = false;
  document.getElementById("app-state-eyebrow").textContent = eyebrow;
  document.getElementById("app-state-title").textContent = title;
  document.getElementById("app-state-body").textContent = body;
  document.getElementById("app-state-retry").hidden = !showRetry;
}

function hideAppState() {
  document.getElementById("app-state-panel").hidden = true;
}

function showErrorState(title, body) {
  state.loading = false;
  state.error = body;
  renderAppState({
    eyebrow: "Unavailable",
    title,
    body,
    showRetry: true,
  });
  renderDashboard();
}

function syncControlState() {
  const disabled = state.loading || !state.dashboard;
  document.getElementById("download-report").disabled = disabled;
  document.getElementById("chat-input").disabled = disabled;
  document.querySelector("#chat-form button[type='submit']").disabled = disabled;
}

function mapSnapshotToDashboard({ session, runStatus, snapshot }) {
  const companyProfiles = snapshot.company_profiles || [];
  const sources = (snapshot.source_documents || []).map((source) => ({
    id: source.id,
    title: source.title || source.id,
    url: source.url,
    snippet: source.snippet || "",
    company: source.metadata?.company_name || "Source",
    sourceType: source.source_type || "web",
  }));
  const companies = companyProfiles.map((profile) => ({
    id: profile.id,
    name: profile.name,
    website: profile.website,
    positioning: profile.positioning_statement || profile.product_summary || "No positioning summary available.",
    targetCustomers: profile.target_customers || [],
    pricingModel: profile.pricing_model || "Pricing not publicly disclosed",
    publicPricingDetails: profile.public_pricing_details || [],
    coreFeatures: profile.core_features || [],
    integrations: profile.integrations || [],
    differentiators: profile.differentiators || [],
    strengths: profile.strengths || [],
    gaps: profile.weaknesses_or_gaps || [],
    confidence: profile.confidence || 0,
    missing: profile.explicit_missing_fields || [],
    sources: profile.source_document_ids || [],
    claims: profile.claims || [],
  }));
  const charts = buildCharts(snapshot.chart_specs || [], companyProfiles, snapshot.comparison_result);
  const reportSections = snapshot.report?.sections || [];
  const keyTakeawaysSection = reportSections.find((section) => section.heading.toLowerCase() === "key takeaways");
  const keyTakeaways = keyTakeawaysSection
    ? parseBulletSection(keyTakeawaysSection.body)
    : snapshot.comparison_result?.ideal_customer_notes || [];
  const tradeoffs = snapshot.comparison_result?.tradeoffs || [];

  return {
    session: {
      id: session.id,
      prompt: session.user_prompt,
      promptSummary: buildPromptSummary(snapshot, companies.length),
      status: formatRunLabel(runStatus?.run.status || session.status || "pending"),
    },
    plan: {
      marketQuery: snapshot.research_plan?.market_query || "Market research session",
      requestedCompanyCount: snapshot.research_plan?.requested_company_count || companies.length,
      discoveryCriteria: snapshot.research_plan?.discovery_criteria || [],
      comparisonDimensions: (snapshot.research_plan?.comparison_dimensions || []).map(formatDimensionLabel),
      assumptions: snapshot.research_plan?.assumptions || [],
    },
    executiveSummary:
      snapshot.dashboard_state?.executive_summary ||
      snapshot.executive_summary ||
      snapshot.report?.executive_summary ||
      "No executive summary is available yet.",
    keyTakeaways,
    tradeoffs,
    companies,
    comparisonFindings: (snapshot.comparison_result?.findings || []).map((finding) => ({
      dimension: finding.dimension,
      summary: finding.summary,
    })),
    charts,
    report: {
      id: snapshot.report?.id,
      markdown: snapshot.report?.markdown_body || "",
    },
    sources,
    chatSuggestions: buildChatSuggestions(snapshot),
  };
}

function buildCharts(chartSpecs, companyProfiles, comparisonResult) {
  return chartSpecs.map((chart) => ({
    id: chart.id,
    title: chart.title,
    description: chart.description,
    type: chart.chart_type,
    artifactSvg: renderChartSvg(chart, companyProfiles, comparisonResult),
  }));
}

function renderChartSvg(chart, companyProfiles, comparisonResult) {
  if (chart.chart_type === "heatmap") {
    const columns = chart.data?.[0]?.columns;
    const rows = chart.data?.[0]?.rows;
    if (columns && rows) {
      return createHeatmapSvg({
        title: chart.title,
        columns,
        rows,
      });
    }
    return createHeatmapSvg({
      title: chart.title,
      columns: ["Coverage"],
      rows: companyProfiles.map((profile) => ({
        label: profile.name,
        values: [Math.max(profile.confidence || 0, 0.1)],
      })),
    });
  }

  const barData =
    chart.data?.length
      ? chart.data.map((row) => ({
          label: String(row.label ?? row.name ?? row.company ?? row[chart.x_field] ?? "Value"),
          value: Number(row.value ?? row.score ?? row[chart.y_field] ?? 0),
        }))
      : inferBarDataFromChart(chart, companyProfiles, comparisonResult);

  return createBarChartSvg({
    title: chart.title,
    data: barData.length ? barData : [{ label: "No data", value: 0 }],
    valueSuffix: "",
  });
}

function inferBarDataFromChart(chart, companyProfiles, comparisonResult) {
  const title = (chart.title || "").toLowerCase();
  if (title.includes("confidence")) {
    return companyProfiles.map((profile) => ({
      label: profile.name,
      value: profile.confidence || 0,
    }));
  }
  if (title.includes("source")) {
    return companyProfiles.map((profile) => ({
      label: profile.name,
      value: (profile.source_document_ids || []).length,
    }));
  }
  if (title.includes("pricing")) {
    return companyProfiles.map((profile) => ({
      label: profile.name,
      value: (profile.public_pricing_details || []).length,
    }));
  }
  return (comparisonResult?.company_ids || []).map((companyId) => ({
    label: companyProfiles.find((profile) => profile.id === companyId)?.name || companyId,
    value: 1,
  }));
}

function buildPromptSummary(snapshot, companyCount) {
  const market = snapshot.research_plan?.market_query || "the selected market";
  return `This session analyzes ${companyCount} companies in ${market} using approved research, extracted claims, comparison findings, and source-backed reporting.`;
}

function buildChatSuggestions(snapshot) {
  const companies = (snapshot.company_profiles || []).slice(0, 2).map((profile) => profile.name);
  if (!companies.length) {
    return DEFAULT_CHAT_SUGGESTIONS;
  }
  return [
    `Which company looks strongest overall in ${snapshot.research_plan?.market_query || "this market"}?`,
    `How do ${companies.join(" and ")} differ on positioning?`,
    "Which claims in this dashboard are the least certain?",
  ];
}

function parseBulletSection(body) {
  return String(body || "")
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line.startsWith("- "))
    .map((line) => line.slice(2));
}

function formatRunLabel(status) {
  return String(status).replaceAll("_", " ").replace(/\b\w/g, (char) => char.toUpperCase());
}

function formatDimensionLabel(value) {
  return String(value).replaceAll("_", " ");
}

function formatChatReference(reference) {
  if (reference.reference_type === "source") {
    const label = escapeHtml(reference.label || reference.reference_id);
    return reference.url
      ? `<a href="${escapeAttribute(reference.url)}" target="_blank" rel="noreferrer">${label}</a>`
      : label;
  }
  if (reference.reference_type === "claim") {
    const label = escapeHtml(reference.label || reference.reference_id);
    const snippet = reference.snippet ? `: ${escapeHtml(reference.snippet)}` : "";
    return `<span title="${escapeAttribute(reference.reference_id)}">Claim: ${label}${snippet}</span>`;
  }
  if (reference.reference_type === "report_section") {
    return `<span>Report: ${escapeHtml(reference.label || reference.reference_id)}</span>`;
  }
  return escapeHtml(reference.reference_id);
}

function resolveSessionId() {
  const params = new URLSearchParams(window.location.search);
  return params.get("session_id") || localStorage.getItem("market-mapper-session-id");
}

function storeSessionId(sessionId) {
  localStorage.setItem("market-mapper-session-id", sessionId);
  const url = new URL(window.location.href);
  url.searchParams.set("session_id", sessionId);
  window.history.replaceState({}, "", url);
}

function isRunPending(status) {
  return ["pending", "running", "waiting_for_approval"].includes(String(status));
}

function buildRunProgressMessage(runStatus) {
  const progress = runStatus.progress;
  return `${formatRunLabel(runStatus.run.status)} at ${progress.percent_complete}% complete. Current step: ${
    progress.current_node || "starting"
  }.`;
}

async function fetchRunStatus(runId) {
  return fetchJson(`/api/runs/${encodeURIComponent(runId)}`);
}

async function fetchJson(url) {
  const response = await fetch(url);
  if (!response.ok) {
    const error = new Error(`Request failed with status ${response.status}`);
    error.status = response.status;
    throw error;
  }
  return response.json();
}

function sleep(ms) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

function populateList(elementId, items) {
  document.getElementById(elementId).innerHTML = items.length
    ? items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")
    : `<li class="muted-copy">No data available.</li>`;
}

function populateTagList(elementId, items) {
  document.getElementById(elementId).innerHTML = items.length
    ? items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")
    : `<li class="muted-copy">No dimensions available.</li>`;
}

function createBarChartSvg({ title, data, valueSuffix }) {
  const width = 760;
  const height = 420;
  const left = 80;
  const right = 30;
  const top = 60;
  const bottom = 60;
  const maxValue = Math.max(...data.map((item) => item.value), 1);
  const chartWidth = width - left - right;
  const chartHeight = height - top - bottom;
  const gap = 18;
  const barWidth = (chartWidth - gap * (data.length - 1)) / data.length;
  const bars = data
    .map((item, index) => {
      const barHeight = (item.value / maxValue) * chartHeight;
      const x = left + index * (barWidth + gap);
      const y = top + chartHeight - barHeight;
      return `
        <rect x="${x}" y="${y}" width="${barWidth}" height="${barHeight}" rx="6" fill="#69b34c" />
        <text x="${x + barWidth / 2}" y="${y - 10}" text-anchor="middle" font-size="12" fill="#2d3748">${escapeHtml(item.value)}${escapeHtml(valueSuffix)}</text>
        <text x="${x + barWidth / 2}" y="${height - 20}" text-anchor="middle" font-size="12" fill="#4a5568">${escapeHtml(item.label)}</text>
      `;
    })
    .join("");
  return `
    <svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">
      <rect width="${width}" height="${height}" rx="12" fill="#ffffff" />
      <text x="28" y="34" font-size="20" font-weight="700" fill="#1a202c">${escapeHtml(title)}</text>
      <line x1="${left}" y1="${top + chartHeight}" x2="${width - right}" y2="${top + chartHeight}" stroke="#d9e2ec" />
      ${bars}
    </svg>
  `;
}

function createHeatmapSvg({ title, columns, rows }) {
  const width = 860;
  const height = 420;
  const left = 160;
  const top = 90;
  const cellWidth = 110;
  const cellHeight = 48;
  const cells = rows
    .flatMap((row, rowIndex) =>
      row.values.map((value, columnIndex) => {
        const x = left + columnIndex * cellWidth;
        const y = top + rowIndex * cellHeight;
        const color = value >= 0.99 ? "#69b34c" : value >= 0.6 ? "#b8df7a" : "#f4f6f8";
        return `<rect x="${x}" y="${y}" width="96" height="34" rx="6" fill="${color}" />`;
      })
    )
    .join("");
  const rowLabels = rows
    .map(
      (row, rowIndex) =>
        `<text x="${left - 14}" y="${top + rowIndex * cellHeight + 23}" text-anchor="end" font-size="12" fill="#4a5568">${escapeHtml(row.label)}</text>`
    )
    .join("");
  const columnLabels = columns
    .map(
      (column, columnIndex) =>
        `<text x="${left + columnIndex * cellWidth + 48}" y="${top - 18}" text-anchor="middle" font-size="12" fill="#4a5568">${escapeHtml(column)}</text>`
    )
    .join("");
  return `
    <svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">
      <rect width="${width}" height="${height}" rx="12" fill="#ffffff" />
      <text x="28" y="34" font-size="20" font-weight="700" fill="#1a202c">${escapeHtml(title)}</text>
      ${cells}
      ${rowLabels}
      ${columnLabels}
    </svg>
  `;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function escapeAttribute(value) {
  return escapeHtml(value);
}
