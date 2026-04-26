import {
  DEFAULT_ACCESS_TOKEN,
  resolveAccessToken,
  storeAccessToken,
  withAccessToken,
} from "./src/lib/auth.js";
import {
  deleteJsonRequest,
  fetchBlob,
  getJson,
  postJsonRequest,
} from "./src/lib/api.js";
import { openSessionStream } from "./src/lib/sessionStream.js";

const DEFAULT_CHAT_SUGGESTIONS = [
  "Which company looks strongest for enterprise support teams?",
  "Where is pricing transparency strongest or weakest?",
  "Which parts of this comparison are the least certain?",
];

const RUN_POLL_INTERVAL_MS = 3000;
const RUN_POLL_ATTEMPTS = 240;

const state = {
  theme: localStorage.getItem("market-mapper-theme") || "light",
  chatCollapsed: false,
  sidebarCollapsed: localStorage.getItem("market-mapper-sidebar-collapsed") === "true",
  accessToken: resolveAccessToken(),
  currentUser: null,
  sessions: [],
  sessionId: null,
  session: null,
  runStatus: null,
  workspace: null,
  runEvents: [],
  dashboard: null,
  loading: true,
  error: null,
  thread: [],
  composerPrompt: "",
  loadRequestId: 0,
  sessionStream: null,
};

initialize().catch((error) => {
  console.error(error);
  showErrorState("Unable to load workspace", error.message || "The dashboard could not be loaded.");
});

async function initialize() {
  applyTheme(state.theme);
  applySidebarState();
  bindEvents();
  renderDashboard();
  await bootstrapAuth();
  await bootstrapWorkspace();
}

async function bootstrapAuth() {
  state.accessToken = resolveAccessToken() || DEFAULT_ACCESS_TOKEN;
  storeAccessToken(state.accessToken);
  state.currentUser = await getJson("/api/auth/me", state.accessToken);
}

function bindEvents() {
  document.getElementById("theme-toggle").addEventListener("click", toggleTheme);
  document.getElementById("chat-toggle").addEventListener("click", toggleChat);
  document.getElementById("sidebar-toggle").addEventListener("click", toggleSidebar);
  document.getElementById("new-session").addEventListener("click", beginNewSessionDraft);
  document.getElementById("download-report").addEventListener("click", downloadMarkdown);
  document.getElementById("chat-form").addEventListener("submit", handleChatSubmit);
  document.getElementById("prompt-form").addEventListener("submit", handlePromptSubmit);
  document.getElementById("prompt-clear").addEventListener("click", () => {
    state.composerPrompt = "";
    document.getElementById("prompt-input").value = "";
  });
  document.getElementById("app-state-retry").addEventListener("click", () => {
    bootstrapWorkspace().catch((error) => {
      console.error(error);
      showErrorState("Unable to reload workspace", error.message || "The dashboard could not be reloaded.");
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

async function bootstrapWorkspace() {
  await loadSessions();
  const sessionId = resolveSessionId();
  if (sessionId) {
    await loadDashboard(sessionId);
    return;
  }

  closeSessionStream();
  state.session = null;
  state.runStatus = null;
  state.workspace = null;
  state.runEvents = [];
  state.dashboard = null;
  state.sessionId = null;
  state.thread = [];
  state.loading = false;
  state.error = null;
  hideAppState();
  renderDashboard();
}

async function loadSessions() {
  try {
    state.sessions = await fetchJson("/api/sessions");
  } catch (error) {
    state.sessions = [];
    if (error.status !== 404) {
      throw error;
    }
  }
  renderSessionList();
}

async function loadDashboard(sessionId = resolveSessionId()) {
  const loadRequestId = ++state.loadRequestId;
  closeSessionStream();
  state.loading = true;
  state.error = null;
  renderAppState({
    eyebrow: "Loading",
    title: "Fetching session data",
    body: "Looking up the current session, run state, and approved dashboard payload.",
    showRetry: false,
  });
  renderDashboard();

  if (!sessionId) {
    state.loading = false;
    hideAppState();
    renderDashboard();
    return;
  }

  state.sessionId = sessionId;
  state.session = await fetchJson(`/api/sessions/${encodeURIComponent(sessionId)}`);
  if (loadRequestId !== state.loadRequestId) {
    return;
  }
  if (state.session?.id) {
    storeSessionId(state.session.id);
  }
  state.runStatus = state.session.active_run_id
    ? await fetchRunStatus(state.session.active_run_id)
    : null;
  if (loadRequestId !== state.loadRequestId) {
    return;
  }

  let payload;
  try {
    payload = await waitForApprovedDashboard(sessionId, loadRequestId);
  } catch (error) {
    if (String(error.message || "").includes("superseded")) {
      return;
    }
    throw error;
  }
  if (loadRequestId !== state.loadRequestId) {
    return;
  }
  state.dashboard = mapSnapshotToDashboard({
    session: state.session,
    runStatus: state.runStatus,
    payload,
  });
  state.workspace = null;
  state.runEvents = [];
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

async function handlePromptSubmit(event) {
  event.preventDefault();
  const input = document.getElementById("prompt-input");
  const prompt = input.value.trim();
  if (!prompt) {
    return;
  }

  state.composerPrompt = prompt;
  state.loading = true;
  state.error = null;
  renderAppState({
    eyebrow: "Starting",
    title: "Creating a new research session",
    body: "Saving the prompt and starting the workflow in the background.",
    showRetry: false,
  });
  renderRunProgress({
    run: { current_node: "planner" },
    progress: { current_node: "planner", percent_complete: 2 },
  });
  renderDashboard();

  try {
    const session = await postJson("/api/sessions", { prompt });
    await postJson(`/api/sessions/${encodeURIComponent(session.id)}/runs`, {});
    await loadSessions();
    await loadDashboard(session.id);
  } catch (error) {
    console.error(error);
    showErrorState("Unable to start research", error.message || "The session could not be created.");
  }
}

function beginNewSessionDraft() {
  openFreshWorkspace();
}

async function waitForApprovedDashboard(sessionId, loadRequestId) {
  try {
    return await fetchJson(`/api/sessions/${encodeURIComponent(sessionId)}/dashboard`);
  } catch (error) {
    if (loadRequestId !== state.loadRequestId) {
      throw new Error("Dashboard load was superseded by a newer session.");
    }
    if (error.status !== 404) {
      throw error;
    }
    state.runStatus = state.session?.active_run_id
      ? await fetchRunStatus(state.session.active_run_id)
      : state.runStatus;
    state.workspace = await fetchWorkspaceSnapshot(sessionId);
    state.runEvents = state.workspace?.run_id ? await fetchRunEvents(state.workspace.run_id) : [];
    state.dashboard = mapWorkspaceSnapshotToDashboard({
      session: state.session,
      runStatus: state.runStatus,
      workspace: state.workspace,
      runEvents: state.runEvents,
    });
    if (!state.runStatus || !isRunPending(state.runStatus.run.status)) {
      throw new Error("No approved dashboard is available for this session yet.");
    }
    renderAppState({
      eyebrow: "Running",
      title: "Research is still in progress",
      body: buildRunProgressMessage(state.runStatus),
      showRetry: false,
    });
    renderRunProgress(state.runStatus);
    renderDashboard();
    return streamApprovedDashboard(sessionId, loadRequestId);
  }
}

function renderDashboard() {
  const dashboard = state.dashboard;
  const hasDashboard = Boolean(dashboard);
  const hasSessions = state.sessions.length > 0;
  const contentGrid = document.querySelector(".content-grid");
  const promptInput = document.getElementById("prompt-input");
  const promptTitle = state.session?.user_prompt || "Market Mapper Dashboard";
  const promptSummary = state.session?.user_prompt
    ? "This session is tied to the prompt below. The report view fills in after the workflow finishes collecting and approving data."
    : "Start a session with a prompt, or reopen a previous session from the left rail.";

  document.getElementById("run-status-label").textContent = dashboard?.session.status || "Ready";
  document.getElementById("prompt-title").textContent = promptTitle;
  document.getElementById("hero-heading").textContent = dashboard?.plan.marketQuery || "No approved dashboard loaded";
  document.getElementById("hero-summary").textContent =
    dashboard?.session.promptSummary ||
    "This page stays blank until a session is running and approved research is available.";
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

  document.getElementById("composer-title").textContent = hasSessions
    ? hasDashboard
      ? "Start another research session"
      : "Complete this session with a prompt"
    : "Start with a prompt";
  document.getElementById("composer-body").textContent = promptSummary;
  promptInput.value = state.composerPrompt || state.session?.user_prompt || "";
  contentGrid.hidden = !hasDashboard;

  renderSessionList();

  renderConfidencePanel();
  renderCompanyCards();
  renderPricingCards();
  renderComparisonTable();
  renderFeatureMatrix();
  renderCharts();
  renderSources();
  renderDashboardSections();
  renderRunEvents();
  renderChatSuggestions();
  renderChatThread();
  renderReportSections();
  renderMarkdownPreview();
  syncControlState();
}

function renderSessionList() {
  const container = document.getElementById("session-list");
  if (!container) {
    return;
  }

  if (!state.sessions.length) {
    container.innerHTML = `<div class="session-empty">No sessions yet. Start with a prompt and the results will appear here.</div>`;
    return;
  }

  container.innerHTML = state.sessions
    .map((session) => {
      const isActive = session.id === state.sessionId;
      const title = truncateText(session.user_prompt || "Untitled session", 72);
      const status = formatRunLabel(session.status || "pending");
      const updated = formatRelativeDate(session.updated_at || session.created_at);
      return `
        <article class="session-item ${isActive ? "is-active" : ""}">
          <span class="session-item-row">
            <button class="session-open" type="button" data-session-id="${escapeAttribute(session.id)}">
              <span class="session-item-title">${escapeHtml(title)}</span>
            </button>
            <span>
              <button class="session-delete" type="button" data-delete-session-id="${escapeAttribute(
                session.id
              )}" aria-label="Delete session">Delete</button>
            </span>
          </span>
          <span class="session-item-meta">${escapeHtml(status)} · ${escapeHtml(updated)}</span>
        </article>
      `;
    })
    .join("");

  container.querySelectorAll("[data-session-id]").forEach((button) => {
    button.addEventListener("click", async () => {
      const nextSessionId = button.dataset.sessionId;
      if (!nextSessionId || nextSessionId === state.sessionId) {
        return;
      }
      try {
        await loadDashboard(nextSessionId);
      } catch (error) {
        console.error(error);
        showErrorState("Unable to open session", error.message || "That session could not be loaded.");
      }
    });
  });

  container.querySelectorAll("[data-delete-session-id]").forEach((button) => {
    button.addEventListener("click", async (event) => {
      event.preventDefault();
      event.stopPropagation();
      const targetSessionId = button.dataset.deleteSessionId;
      if (!targetSessionId) {
        return;
      }
      const session = state.sessions.find((entry) => entry.id === targetSessionId);
      const label = session?.user_prompt ? truncateText(session.user_prompt, 60) : "this session";
      const confirmed = window.confirm(`Delete ${label}? This will remove the saved run and dashboard state.`);
      if (!confirmed) {
        return;
      }

      try {
        await deleteRequest(`/api/sessions/${encodeURIComponent(targetSessionId)}`);
        const deletedCurrentSession = targetSessionId === state.sessionId;
        await loadSessions();
        if (deletedCurrentSession) {
          beginNewSessionDraft();
        } else {
          renderDashboard();
        }
      } catch (error) {
        console.error(error);
        showErrorState("Unable to delete session", error.message || "The session could not be deleted.");
      }
    });
  });
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
          const chartImage = chart.artifactUrl
            ? `<img src="${escapeAttribute(chart.artifactUrl)}" alt="${escapeAttribute(chart.title)}" />`
            : `<img src="data:image/svg+xml;charset=utf-8,${encodeURIComponent(chart.artifactSvg)}" alt="${escapeAttribute(chart.title)}" />`;
          return `
            <article class="chart-card">
              <p class="eyebrow">${escapeHtml(chart.type)}</p>
              <h4>${escapeHtml(chart.title)}</h4>
              <p class="muted-copy" style="margin:8px 0 14px;">${escapeHtml(chart.description || "Chart artifact generated from the approved session state.")}</p>
              ${chartImage}
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

function renderDashboardSections() {
  const container = document.getElementById("dashboard-sections");
  const sections = state.dashboard?.dashboardSections || [];
  container.innerHTML = sections.length
    ? sections
        .map(
          (section) => `
            <article class="section-card">
              <p class="eyebrow">${escapeHtml(section.key)}</p>
              <h4>${escapeHtml(section.title)}</h4>
              ${
                section.status
                  ? `<p class="muted-copy section-status-line">${escapeHtml(formatRunLabel(section.status))}${
                      Number.isFinite(section.progressPercent) ? ` · ${Math.round(section.progressPercent)}%` : ""
                    }</p>`
                  : ""
              }
              <p class="muted-copy">${escapeHtml(section.summary || "No section summary available.")}</p>
              ${
                section.contentRefs?.length
                  ? `<p class="muted-copy" style="margin-top:10px;">References: ${section.contentRefs
                      .map((ref) => escapeHtml(ref))
                      .join(", ")}</p>`
                  : ""
              }
            </article>
          `
        )
        .join("")
    : `<article class="section-card"><p class="muted-copy">Saved dashboard sections will appear here once the dashboard builder has run.</p></article>`;
}

function renderRunEvents() {
  const container = document.getElementById("live-events");
  if (!container) {
    return;
  }
  const events = (state.dashboard?.liveEvents || []).slice(-8).reverse();
  container.innerHTML = events.length
    ? events
        .map(
          (event) => `
            <article class="section-card event-card">
              <p class="eyebrow">${escapeHtml(formatRunLabel(event.kind || "update"))}</p>
              <h4>${escapeHtml(event.node_name ? formatStageLabel(event.node_name) : "Workflow update")}</h4>
              <p class="muted-copy">${escapeHtml(event.message || "An update was recorded for this run.")}</p>
              <p class="muted-copy section-status-line">${escapeHtml(formatRelativeDate(event.created_at))}</p>
            </article>
          `
        )
        .join("")
    : `<article class="section-card"><p class="muted-copy">Live workflow events will appear here while the session is running.</p></article>`;
}

function renderReportSections() {
  const container = document.getElementById("report-sections");
  const sections = state.dashboard?.report.sections || [];
  container.innerHTML = sections.length
    ? sections
        .map(
          (section) => `
            <article class="section-card">
              <p class="eyebrow">Report Section</p>
              <h4>${escapeHtml(section.heading)}</h4>
              <p class="muted-copy">${escapeHtml(section.body || "No report section body available.")}</p>
              ${
                section.citationIds?.length
                  ? `<p class="muted-copy" style="margin-top:10px;">Citations: ${section.citationIds
                      .map((citationId) => escapeHtml(citationId))
                      .join(", ")}</p>`
                  : ""
              }
            </article>
          `
        )
        .join("")
    : `<article class="section-card"><p class="muted-copy">Approved report sections will appear here once the report is generated.</p></article>`;
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
  return postJson("/api/chat/answer", {
    session_id: state.sessionId,
    question,
  });
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

function toggleSidebar() {
  state.sidebarCollapsed = !state.sidebarCollapsed;
  applySidebarState();
}

function applySidebarState() {
  document.body.dataset.sidebarCollapsed = String(state.sidebarCollapsed);
  localStorage.setItem("market-mapper-sidebar-collapsed", String(state.sidebarCollapsed));
  const button = document.getElementById("sidebar-toggle");
  if (button) {
    button.textContent = state.sidebarCollapsed ? "Open" : "Collapse";
    button.setAttribute("aria-expanded", String(!state.sidebarCollapsed));
  }
}

function downloadMarkdown() {
  const reportDownloadUrl = state.dashboard?.report.downloadUrl;
  if (reportDownloadUrl) {
    downloadAuthenticatedReport(reportDownloadUrl).catch((error) => {
      console.error(error);
      showErrorState("Unable to download report", error.message || "The Markdown artifact could not be downloaded.");
    });
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
  document.getElementById("app-state-progress").hidden = true;
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
  const hasApprovedDashboard = Boolean(state.dashboard?.isApproved);
  document.getElementById("download-report").disabled =
    state.loading || (!state.dashboard?.report?.downloadUrl && !state.dashboard?.report?.markdown);
  document.getElementById("chat-input").disabled = state.loading || !hasApprovedDashboard;
  document.querySelector("#chat-form button[type='submit']").disabled = state.loading || !hasApprovedDashboard;
  document.getElementById("prompt-submit").disabled = state.loading;
  document.getElementById("prompt-clear").disabled = state.loading;
}

function mapSnapshotToDashboard({ session, runStatus, payload }) {
  const snapshot = payload.snapshot;
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
  const charts = buildCharts(
    snapshot.chart_specs || [],
    payload.chart_artifacts || [],
    companyProfiles,
    snapshot.comparison_result
  );
  const reportSections = snapshot.report?.sections || [];
  const keyTakeawaysSection = reportSections.find((section) => section.heading.toLowerCase() === "key takeaways");
  const keyTakeaways = keyTakeawaysSection
    ? parseBulletSection(keyTakeawaysSection.body)
    : snapshot.comparison_result?.ideal_customer_notes || [];
  const tradeoffs = snapshot.comparison_result?.tradeoffs || [];

  return {
    isApproved: true,
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
      downloadUrl: withAccessToken(payload.report_download_url, state.accessToken),
      sections: reportSections.map((section) => ({
        heading: section.heading,
        body: section.body,
        citationIds: section.citation_ids || [],
      })),
    },
    sources,
    chatSuggestions: buildChatSuggestions(snapshot),
    dashboardSections: (snapshot.dashboard_state?.sections || []).map((section) => ({
      key: section.key,
      title: section.title,
      summary: section.summary,
      contentRefs: section.content_refs || [],
    })),
    dashboardArtifactUrl: withAccessToken(payload.dashboard_artifact?.url || null, state.accessToken),
    reportArtifactUrl: withAccessToken(payload.report_artifact?.url || null, state.accessToken),
  };
}

function mapWorkspaceSnapshotToDashboard({ session, runStatus, workspace, runEvents }) {
  const companyStatuses = workspace?.company_statuses || [];
  const companies = companyStatuses.map((company) => ({
    id: company.company_profile_id || company.company_candidate_id || company.id,
    name: company.name,
    website: company.website,
    positioning: company.summary || "Research is still being gathered for this company.",
    targetCustomers: [],
    pricingModel: "Still collecting public pricing evidence",
    publicPricingDetails: company.source_document_ids?.length
      ? [`${company.source_document_ids.length} source documents have been collected so far.`]
      : [],
    coreFeatures: [],
    integrations: [],
    differentiators: [],
    strengths: [],
    gaps: company.missing_fields || [],
    confidence: company.confidence || 0,
    missing: company.missing_fields || [],
    sources: company.source_document_ids || [],
    claims: [],
    status: company.status,
  }));
  const sources = (workspace?.source_documents || []).map((source) => ({
    id: source.id,
    title: source.title || source.id,
    url: source.url,
    snippet: source.snippet || "",
    company: source.metadata?.company_name || "Source",
    sourceType: source.source_type || "web",
  }));
  const dashboardSections = (workspace?.sections || []).map((section) => ({
    key: section.key,
    title: section.title,
    summary: section.summary,
    contentRefs: section.content_refs || [],
    status: section.status,
    progressPercent: section.progress_percent || 0,
  }));
  return {
    isApproved: false,
    session: {
      id: session.id,
      prompt: session.user_prompt,
      promptSummary:
        "This live workspace updates as parallel company workers collect evidence, normalize profiles, and hand results back to the shared run.",
      status: formatRunLabel(runStatus?.run.status || session.status || workspace?.session_status || "pending"),
    },
    plan: {
      marketQuery: workspace?.research_plan?.market_query || "Live research workspace",
      requestedCompanyCount: workspace?.research_plan?.requested_company_count || companies.length,
      discoveryCriteria: workspace?.research_plan?.discovery_criteria || [],
      comparisonDimensions: (workspace?.research_plan?.comparison_dimensions || []).map(formatDimensionLabel),
      assumptions: workspace?.research_plan?.assumptions || [],
    },
    executiveSummary:
      workspace?.comparison_result?.ideal_customer_notes?.[0] ||
      "The dashboard is filling in with live research while the final approved comparison is still being assembled.",
    keyTakeaways: [
      `${companies.length} companies are currently in the parallel research set.`,
      `${sources.length} source documents have been gathered so far.`,
      workspace?.current_node ? `Current workflow step: ${formatStageLabel(workspace.current_node)}.` : "The workflow is warming up.",
    ],
    tradeoffs: [
      "This is a live workspace snapshot, so some sections may still be incomplete.",
      "The final approved report and chat unlock after verification finishes.",
    ],
    companies,
    comparisonFindings: (workspace?.comparison_result?.findings || []).map((finding) => ({
      dimension: finding.dimension,
      summary: finding.summary,
    })),
    charts: [],
    report: {
      id: workspace?.report?.id || null,
      markdown: workspace?.report?.markdown_body || "",
      downloadUrl: null,
      sections: (workspace?.report?.sections || []).map((section) => ({
        heading: section.heading,
        body: section.body,
        citationIds: section.citation_ids || [],
      })),
    },
    sources,
    chatSuggestions: DEFAULT_CHAT_SUGGESTIONS,
    dashboardSections,
    dashboardArtifactUrl: null,
    reportArtifactUrl: null,
    liveEvents: runEvents?.events || [],
  };
}

function buildCharts(chartSpecs, chartArtifacts, companyProfiles, comparisonResult) {
  const chartArtifactsById = Object.fromEntries(
    chartArtifacts.map((artifact) => [artifact.chart_id, artifact])
  );
  return chartSpecs.map((chart) => ({
    id: chart.id,
    title: chart.title,
    description: chart.description,
    type: chart.chart_type,
    artifactUrl: withAccessToken(chartArtifactsById[chart.id]?.artifact?.url || null, state.accessToken),
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

function clearStoredSessionId() {
  localStorage.removeItem("market-mapper-session-id");
  const url = new URL(window.location.href);
  url.searchParams.delete("session_id");
  window.history.replaceState({}, "", url);
}

function openFreshWorkspace() {
  closeSessionStream();
  localStorage.removeItem("market-mapper-session-id");
  const url = new URL(window.location.href);
  url.searchParams.delete("session_id");
  url.hash = "";
  window.location.assign(url.toString());
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

function renderRunProgress(runStatus) {
  const progressPanel = document.getElementById("app-state-progress");
  const percent = Math.max(3, Math.min(Math.round(runStatus?.progress?.percent_complete || 0), 100));
  const stage = formatStageLabel(runStatus?.progress?.current_node || runStatus?.run?.current_node || "starting");
  progressPanel.hidden = false;
  document.getElementById("app-state-stage").textContent = stage;
  document.getElementById("app-state-percent").textContent = `${percent}%`;
  document.getElementById("app-state-progress-bar").style.width = `${percent}%`;
}

function formatStageLabel(value) {
  const labels = {
    planner: "Planning the research",
    executor: "Coordinating the workflow",
    company_discovery: "Finding the right companies",
    web_research: "Collecting public sources",
    structured_extraction: "Normalizing company data",
    comparison: "Comparing the market",
    critic_verifier: "Verifying the evidence",
    output_generation: "Generating report and charts",
    report_generation: "Writing the report",
    chart_generation: "Rendering charts",
    dashboard_builder: "Building the dashboard",
    session_chatbot: "Preparing follow-up chat",
  };
  return labels[value] || formatRunLabel(value);
}

async function fetchRunStatus(runId) {
  return fetchJson(`/api/runs/${encodeURIComponent(runId)}`);
}

async function fetchWorkspaceSnapshot(sessionId) {
  return fetchJson(`/api/sessions/${encodeURIComponent(sessionId)}/workspace`);
}

async function fetchRunEvents(runId) {
  return fetchJson(`/api/runs/${encodeURIComponent(runId)}/events`);
}

async function fetchJson(url) {
  return getJson(url, state.accessToken);
}

async function postJson(url, payload) {
  return postJsonRequest(url, payload, state.accessToken);
}

async function deleteRequest(url) {
  return deleteJsonRequest(url, state.accessToken);
}

function streamApprovedDashboard(sessionId, loadRequestId) {
  if (typeof EventSource !== "function") {
    return pollForApprovedDashboard(sessionId, loadRequestId);
  }
  return new Promise((resolve, reject) => {
    let settled = false;
    const timeout = window.setTimeout(() => {
      if (settled) {
        return;
      }
      settled = true;
      closeSessionStream();
      renderAppState({
        eyebrow: "Still working",
        title: "The research run is taking longer than usual",
        body: "Market Mapper is still collecting and verifying information. You can keep this page open and retry in a moment without losing the session.",
        showRetry: true,
      });
      renderRunProgress(state.runStatus || { run: { current_node: "executor" }, progress: { percent_complete: 85 } });
      reject(new Error("The research stream is still in progress. Retry in a moment to refresh the dashboard."));
    }, RUN_POLL_INTERVAL_MS * RUN_POLL_ATTEMPTS);

    const guard = () => loadRequestId === state.loadRequestId && state.sessionId === sessionId;
    const settle = (fn, payload) => {
      if (settled) {
        return;
      }
      settled = true;
      window.clearTimeout(timeout);
      closeSessionStream();
      fn(payload);
    };

    state.sessionStream = openSessionStream({
      sessionId,
      accessToken: state.accessToken,
      onWorkspace: (workspace) => {
        if (!guard()) {
          settle(reject, new Error("Dashboard load was superseded by a newer session."));
          return;
        }
        state.workspace = workspace;
        state.dashboard = mapWorkspaceSnapshotToDashboard({
          session: state.session,
          runStatus: state.runStatus,
          workspace: state.workspace,
          runEvents: state.runEvents,
        });
        renderDashboard();
      },
      onRunStatus: (runStatus) => {
        if (!guard()) {
          return;
        }
        state.runStatus = runStatus;
        renderAppState({
          eyebrow: "Running",
          title: "Research is still in progress",
          body: buildRunProgressMessage(runStatus),
          showRetry: false,
        });
        renderRunProgress(runStatus);
        renderDashboard();
        if (["failed", "canceled", "blocked"].includes(String(runStatus.run.status))) {
          settle(reject, new Error(`Run finished with status ${runStatus.run.status}.`));
        }
      },
      onRunEvents: (runEvents) => {
        if (!guard()) {
          return;
        }
        state.runEvents = runEvents.events || [];
        if (state.workspace) {
          state.dashboard = mapWorkspaceSnapshotToDashboard({
            session: state.session,
            runStatus: state.runStatus,
            workspace: state.workspace,
            runEvents: state.runEvents,
          });
          renderDashboard();
        }
      },
      onApprovedDashboard: (payload) => {
        if (!guard()) {
          settle(reject, new Error("Dashboard load was superseded by a newer session."));
          return;
        }
        settle(resolve, payload);
      },
      onError: (payload) => {
        if (!guard()) {
          return;
        }
        const message = payload?.detail || payload?.message || "The live session stream disconnected.";
        if (state.runStatus && !isRunPending(state.runStatus.run.status)) {
          settle(reject, new Error(message));
        }
      },
    });
  });
}

async function pollForApprovedDashboard(sessionId, loadRequestId) {
  for (let attempt = 0; attempt < RUN_POLL_ATTEMPTS; attempt += 1) {
    if (loadRequestId !== state.loadRequestId) {
      throw new Error("Dashboard load was superseded by a newer session.");
    }
    try {
      return await fetchJson(`/api/sessions/${encodeURIComponent(sessionId)}/dashboard`);
    } catch (error) {
      if (error.status !== 404) {
        throw error;
      }
      state.runStatus = state.session?.active_run_id
        ? await fetchRunStatus(state.session.active_run_id)
        : state.runStatus;
      state.workspace = await fetchWorkspaceSnapshot(sessionId);
      state.runEvents = state.workspace?.run_id ? await fetchRunEvents(state.workspace.run_id) : [];
      state.dashboard = mapWorkspaceSnapshotToDashboard({
        session: state.session,
        runStatus: state.runStatus,
        workspace: state.workspace,
        runEvents: state.runEvents,
      });
      renderDashboard();
      await sleep(RUN_POLL_INTERVAL_MS);
    }
  }
  throw new Error("The research run is still in progress. Retry in a moment to refresh the dashboard.");
}

function closeSessionStream() {
  if (state.sessionStream) {
    state.sessionStream.close();
    state.sessionStream = null;
  }
}

async function downloadAuthenticatedReport(url) {
  const blob = await fetchBlob(url, state.accessToken);
  const downloadUrl = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = downloadUrl;
  anchor.download = "market-mapper-report.md";
  anchor.click();
  URL.revokeObjectURL(downloadUrl);
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

function truncateText(value, maxLength) {
  const text = String(value);
  return text.length > maxLength ? `${text.slice(0, maxLength - 1)}…` : text;
}

function formatRelativeDate(value) {
  const date = value ? new Date(value) : null;
  if (!date || Number.isNaN(date.valueOf())) {
    return "recently";
  }
  const diffMs = Date.now() - date.getTime();
  const diffMinutes = Math.max(Math.round(diffMs / 60000), 0);
  if (diffMinutes < 1) {
    return "just now";
  }
  if (diffMinutes < 60) {
    return `${diffMinutes}m ago`;
  }
  const diffHours = Math.round(diffMinutes / 60);
  if (diffHours < 24) {
    return `${diffHours}h ago`;
  }
  const diffDays = Math.round(diffHours / 24);
  if (diffDays < 7) {
    return `${diffDays}d ago`;
  }
  return date.toLocaleDateString();
}
