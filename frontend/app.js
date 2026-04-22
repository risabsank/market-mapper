const dashboardData = {
  session: {
    id: "session_ai_support",
    prompt:
      "Analyze 4 of the largest companies in AI customer support and create a comparison report.",
    promptSummary:
      "This session compares AI customer support platforms across pricing transparency, feature depth, enterprise fit, integrations, and public evidence quality.",
    status: "Approved for reporting",
  },
  plan: {
    marketQuery: "AI customer support",
    requestedCompanyCount: 4,
    discoveryCriteria: [
      "Largest public presence in AI customer support",
      "Clear product and pricing evidence from official sites",
      "Relevant enterprise and mid-market positioning",
      "Enough public documentation for structured comparison",
    ],
    comparisonDimensions: [
      "pricing",
      "features",
      "positioning",
      "target customers",
      "integrations",
      "differentiators",
      "strengths",
      "gaps",
    ],
    assumptions: [
      "Comparison uses public product, pricing, and documentation pages only.",
      "Sparse or missing public pricing is treated as uncertainty, not a negative signal by itself.",
      "Enterprise readiness is inferred from public messaging, integrations, and proof points.",
    ],
  },
  executiveSummary:
    "Intercom and Zendesk appear strongest overall for broad AI customer support maturity, but they win for different reasons. Intercom presents the sharper AI-first narrative and more visible automation packaging, while Zendesk looks strongest where enterprise process depth and operational breadth matter. Freshworks offers a more accessible path for teams that want breadth with simpler rollout, and Forethought stands out where agent-assist and automation sophistication matter more than platform breadth. Public pricing transparency remains uneven across the category, so pricing comparisons are more directional than definitive.",
  keyTakeaways: [
    "Intercom reads as the most AI-forward brand in the set, with strong messaging around automation, copilots, and resolution workflows.",
    "Zendesk looks like the safest choice for larger support organizations that need workflow depth, broad service coverage, and enterprise governance.",
    "Freshworks is easier to position as a value and simplicity play, especially for teams that want a broad support stack without an enterprise-heavy rollout.",
    "Forethought is compelling when AI automation quality is the center of the buying motion, but the public platform picture is narrower than Zendesk or Intercom.",
  ],
  tradeoffs: [
    "The strongest platforms on AI positioning are not always the most transparent on public pricing.",
    "Broader platform suites usually come with more complexity and more ambiguous entry pricing.",
    "AI-specialist products can look sharper on automation workflows while still needing adjacent tooling for full support operations.",
  ],
  companies: [
    {
      id: "company_intercom",
      name: "Intercom",
      website: "https://www.intercom.com",
      positioning: "AI-first customer service for support teams that want automation visible in the buying story.",
      targetCustomers: ["Mid-market", "Enterprise"],
      pricingModel: "Tiered plans plus usage-based AI features",
      publicPricingDetails: ["Starter and advanced tiers are public", "Some AI usage pricing needs sales context"],
      coreFeatures: ["AI agent", "Shared inbox", "Workflows", "Help center"],
      integrations: ["Salesforce", "HubSpot", "Slack", "Stripe"],
      differentiators: ["AI-forward messaging", "Modern support workflow design"],
      strengths: ["AI product narrative", "Automation clarity", "Strong self-serve support UX"],
      gaps: ["Enterprise governance details are less explicit than Zendesk"],
      confidence: 0.82,
      missing: ["deeper public enterprise governance detail"],
      sources: ["source_intercom_home", "source_intercom_pricing", "source_intercom_ai"],
    },
    {
      id: "company_zendesk",
      name: "Zendesk",
      website: "https://www.zendesk.com",
      positioning: "Enterprise-grade service platform with broad support operations coverage and growing AI layering.",
      targetCustomers: ["Enterprise", "Upper mid-market"],
      pricingModel: "Public plan tiers with enterprise upsell",
      publicPricingDetails: ["Suite plan ranges are public", "Enterprise packaging still requires sales motion"],
      coreFeatures: ["AI agents", "Ticketing", "Workflows", "Knowledge base", "Analytics"],
      integrations: ["Salesforce", "Slack", "Jira", "Shopify"],
      differentiators: ["Operational breadth", "Enterprise service maturity"],
      strengths: ["Governance depth", "Support operations breadth", "Enterprise credibility"],
      gaps: ["AI messaging feels less focused than Intercom"],
      confidence: 0.86,
      missing: ["finer AI pricing detail"],
      sources: ["source_zendesk_home", "source_zendesk_pricing", "source_zendesk_ai"],
    },
    {
      id: "company_freshworks",
      name: "Freshworks",
      website: "https://www.freshworks.com",
      positioning: "Broad support suite positioned around ease of use, speed to value, and accessible pricing.",
      targetCustomers: ["SMB", "Mid-market"],
      pricingModel: "Public tiered SaaS pricing",
      publicPricingDetails: ["Most core plans are public", "Advanced enterprise packaging can vary"],
      coreFeatures: ["Ticketing", "Bots", "Knowledge base", "Analytics"],
      integrations: ["Slack", "Microsoft Teams", "HubSpot", "Jira"],
      differentiators: ["Approachable rollout", "Value-oriented packaging"],
      strengths: ["Pricing transparency", "Ease of adoption", "Broad support coverage"],
      gaps: ["AI depth looks less differentiated in public materials"],
      confidence: 0.74,
      missing: ["clear enterprise AI differentiation"],
      sources: ["source_freshworks_home", "source_freshworks_pricing", "source_freshworks_ai"],
    },
    {
      id: "company_forethought",
      name: "Forethought",
      website: "https://forethought.ai",
      positioning: "AI automation specialist centered on agent-assist and support resolution quality.",
      targetCustomers: ["Mid-market", "Enterprise"],
      pricingModel: "Sales-led pricing",
      publicPricingDetails: ["No detailed public tier pricing"],
      coreFeatures: ["Agent assist", "Automated resolution", "Intent detection", "Insights"],
      integrations: ["Salesforce", "Zendesk", "Intercom", "Freshdesk"],
      differentiators: ["AI specialization", "Resolution-focused workflows"],
      strengths: ["Specialist AI story", "Focused support automation"],
      gaps: ["Less visible platform breadth", "Low public pricing transparency"],
      confidence: 0.68,
      missing: ["public pricing", "full support suite breadth"],
      sources: ["source_forethought_home", "source_forethought_platform", "source_forethought_integrations"],
    },
  ],
  comparisonFindings: [
    {
      dimension: "pricing",
      summary:
        "Freshworks is the most transparent publicly, Zendesk and Intercom show meaningful plan structure, and Forethought remains mostly sales-led.",
    },
    {
      dimension: "features",
      summary:
        "Zendesk and Intercom look broadest in public feature coverage, while Forethought is narrower but more specialized in AI support automation.",
    },
    {
      dimension: "positioning",
      summary:
        "Intercom is the clearest AI-first brand, Zendesk is the enterprise platform choice, Freshworks leans toward speed and value, and Forethought leans specialist AI depth.",
    },
    {
      dimension: "target_customers",
      summary:
        "Zendesk and Intercom cover enterprise most convincingly in public materials, while Freshworks feels strongest in SMB to mid-market accessibility.",
    },
  ],
  charts: [
    {
      id: "chart_confidence",
      title: "Research Confidence by Company",
      description: "How grounded each profile is based on public evidence and missing-field coverage.",
      type: "bar",
      artifactSvg: createBarChartSvg({
        title: "Research Confidence by Company",
        data: [
          { label: "Intercom", value: 0.82 },
          { label: "Zendesk", value: 0.86 },
          { label: "Freshworks", value: 0.74 },
          { label: "Forethought", value: 0.68 },
        ],
        valueSuffix: "",
      }),
    },
    {
      id: "chart_sources",
      title: "Source Coverage by Company",
      description: "Traceable source count per company profile.",
      type: "bar",
      artifactSvg: createBarChartSvg({
        title: "Source Coverage by Company",
        data: [
          { label: "Intercom", value: 3 },
          { label: "Zendesk", value: 3 },
          { label: "Freshworks", value: 3 },
          { label: "Forethought", value: 3 },
        ],
        valueSuffix: "",
      }),
    },
    {
      id: "chart_coverage",
      title: "Dimension Coverage Matrix",
      description: "Which dimensions have clear public evidence by company.",
      type: "heatmap",
      artifactSvg: createHeatmapSvg({
        title: "Dimension Coverage Matrix",
        columns: ["Pricing", "Features", "Positioning", "Integrations", "Differentiators"],
        rows: [
          { label: "Intercom", values: [1, 1, 1, 1, 1] },
          { label: "Zendesk", values: [1, 1, 1, 1, 1] },
          { label: "Freshworks", values: [1, 1, 1, 1, 0.6] },
          { label: "Forethought", values: [0.2, 0.8, 1, 1, 1] },
        ],
      }),
    },
  ],
  report: {
    title: "AI Customer Support Competitive Comparison",
    markdown: `# AI Customer Support Competitive Comparison

## Executive Summary

Intercom and Zendesk appear strongest overall for broad AI customer support maturity, but they win for different reasons. Intercom is the clearest AI-first brand in the set, while Zendesk looks strongest for enterprise-grade operational depth. Freshworks reads as the most accessible and publicly transparent option, and Forethought stands out where specialist AI automation matters more than suite breadth.

## Company Summaries

- **Intercom**: AI-first positioning with strong automation messaging and a modern support workflow story.
- **Zendesk**: Broad service platform with the strongest public enterprise credibility in the set.
- **Freshworks**: Accessible packaging and broad support coverage for teams prioritizing speed and value.
- **Forethought**: Specialist AI resolution and agent-assist platform with thinner public pricing coverage.

## Structured Comparison

- Pricing transparency favors Freshworks.
- Enterprise operations breadth favors Zendesk.
- AI-forward positioning favors Intercom.
- Specialist automation depth favors Forethought.

## Key Takeaways

- The strongest AI story and the strongest enterprise ops story are not exactly the same product.
- Pricing comparisons remain directional because public transparency is uneven.
- Teams that value speed and clarity will likely shortlist differently than teams that prioritize governance depth.

## Source References

- \`source_intercom_home\` - Intercom homepage
- \`source_zendesk_home\` - Zendesk homepage
- \`source_freshworks_home\` - Freshworks homepage
- \`source_forethought_home\` - Forethought homepage
`,
  },
  sources: [
    {
      id: "source_intercom_home",
      title: "Intercom customer service platform",
      url: "https://www.intercom.com",
      snippet: "Homepage and product overview used for positioning, AI workflows, and target customer framing.",
      company: "Intercom",
      sourceType: "official_site",
    },
    {
      id: "source_intercom_pricing",
      title: "Intercom pricing",
      url: "https://www.intercom.com/pricing",
      snippet: "Used for pricing model and packaging details.",
      company: "Intercom",
      sourceType: "official_pricing",
    },
    {
      id: "source_intercom_ai",
      title: "Intercom AI agent",
      url: "https://www.intercom.com/fin",
      snippet: "Used for AI capability and differentiation claims.",
      company: "Intercom",
      sourceType: "official_ai",
    },
    {
      id: "source_zendesk_home",
      title: "Zendesk service platform",
      url: "https://www.zendesk.com",
      snippet: "Used for positioning, support operations breadth, and platform framing.",
      company: "Zendesk",
      sourceType: "official_site",
    },
    {
      id: "source_zendesk_pricing",
      title: "Zendesk pricing",
      url: "https://www.zendesk.com/pricing",
      snippet: "Used for public plan structure and pricing transparency comparison.",
      company: "Zendesk",
      sourceType: "official_pricing",
    },
    {
      id: "source_zendesk_ai",
      title: "Zendesk AI",
      url: "https://www.zendesk.com/service/ai",
      snippet: "Used for AI feature and automation support.",
      company: "Zendesk",
      sourceType: "official_ai",
    },
    {
      id: "source_freshworks_home",
      title: "Freshworks service suite",
      url: "https://www.freshworks.com",
      snippet: "Used for suite positioning and target customer framing.",
      company: "Freshworks",
      sourceType: "official_site",
    },
    {
      id: "source_freshworks_pricing",
      title: "Freshworks pricing",
      url: "https://www.freshworks.com/freshdesk/pricing",
      snippet: "Used for pricing transparency and plan coverage.",
      company: "Freshworks",
      sourceType: "official_pricing",
    },
    {
      id: "source_freshworks_ai",
      title: "Freshworks Freddy AI",
      url: "https://www.freshworks.com/platform/ai",
      snippet: "Used for AI positioning and capability coverage.",
      company: "Freshworks",
      sourceType: "official_ai",
    },
    {
      id: "source_forethought_home",
      title: "Forethought homepage",
      url: "https://forethought.ai",
      snippet: "Used for product positioning and target buyer framing.",
      company: "Forethought",
      sourceType: "official_site",
    },
    {
      id: "source_forethought_platform",
      title: "Forethought platform overview",
      url: "https://forethought.ai/platform",
      snippet: "Used for specialist automation feature coverage.",
      company: "Forethought",
      sourceType: "official_platform",
    },
    {
      id: "source_forethought_integrations",
      title: "Forethought integrations",
      url: "https://forethought.ai/integrations",
      snippet: "Used for ecosystem and deployment fit.",
      company: "Forethought",
      sourceType: "official_integrations",
    },
  ],
  chatSuggestions: [
    "Which company looks strongest for enterprise support teams?",
    "Where is pricing transparency strongest or weakest?",
    "Which claims in this dashboard are the most uncertain?",
  ],
};

const state = {
  theme: localStorage.getItem("market-mapper-theme") || "light",
  chatCollapsed: false,
  thread: [
    {
      role: "assistant",
      text:
        "This panel stays inside the current research session. Ask about the comparison, sources, pricing, or uncertainty and I’ll answer from the approved dashboard state.",
      citations: [],
      uncertainty: null,
    },
  ],
};

initialize();

function initialize() {
  applyTheme(state.theme);
  renderDashboard();
  bindEvents();
}

function bindEvents() {
  document.getElementById("theme-toggle").addEventListener("click", toggleTheme);
  document.getElementById("chat-toggle").addEventListener("click", toggleChat);
  document.getElementById("download-report").addEventListener("click", downloadMarkdown);
  document.getElementById("chat-form").addEventListener("submit", handleChatSubmit);

  document.querySelectorAll(".nav-item").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelectorAll(".nav-item").forEach((item) => item.classList.remove("is-active"));
      button.classList.add("is-active");
      document.getElementById(button.dataset.target)?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  });
}

function renderDashboard() {
  document.getElementById("run-status-label").textContent = dashboardData.session.status;
  document.getElementById("prompt-title").textContent = dashboardData.session.prompt;
  document.getElementById("hero-heading").textContent = dashboardData.plan.marketQuery;
  document.getElementById("hero-summary").textContent = dashboardData.session.promptSummary;
  document.getElementById("metric-company-count").textContent = String(dashboardData.companies.length);
  document.getElementById("metric-source-count").textContent = String(dashboardData.sources.length);
  document.getElementById("metric-chart-count").textContent = String(dashboardData.charts.length);
  document.getElementById("plan-company-count").textContent = `${dashboardData.plan.requestedCompanyCount} companies`;
  document.getElementById("executive-summary").textContent = dashboardData.executiveSummary;

  populateList("discovery-criteria", dashboardData.plan.discoveryCriteria);
  populateTagList("comparison-dimensions", dashboardData.plan.comparisonDimensions);
  populateList("plan-assumptions", dashboardData.plan.assumptions);
  populateList("key-takeaways", dashboardData.keyTakeaways);
  populateList("tradeoffs", dashboardData.tradeoffs);

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
}

function renderConfidencePanel() {
  const averageConfidence =
    dashboardData.companies.reduce((sum, company) => sum + company.confidence, 0) /
    dashboardData.companies.length;
  const percentage = Math.round(averageConfidence * 100);
  document.getElementById("confidence-value").textContent = `${percentage}%`;
  const circumference = 2 * Math.PI * 48;
  const offset = circumference * (1 - averageConfidence);
  document.getElementById("ring-progress").style.strokeDasharray = `${circumference}`;
  document.getElementById("ring-progress").style.strokeDashoffset = `${offset}`;
  populateList("confidence-notes", [
    `${dashboardData.companies.filter((company) => company.confidence >= 0.8).length} companies have strong public evidence coverage.`,
    `${dashboardData.companies.filter((company) => company.missing.length > 0).length} companies still have at least one uncertain area.`,
    "Pricing remains the least evenly documented dimension across the set.",
  ]);
}

function renderCompanyCards() {
  const container = document.getElementById("company-cards");
  container.innerHTML = dashboardData.companies
    .map(
      (company) => `
        <article class="company-card">
          <p class="eyebrow">${company.targetCustomers.join(" / ")}</p>
          <h4>${company.name}</h4>
          <p class="muted-copy">${company.positioning}</p>
          <div class="company-meta">
            <span class="meta-chip">${Math.round(company.confidence * 100)}% confidence</span>
            <span class="coverage-chip">${company.sources.length} sources</span>
            ${company.missing.length ? `<span class="missing-chip">${company.missing.length} uncertain areas</span>` : ""}
          </div>
        </article>
      `
    )
    .join("");
}

function renderPricingCards() {
  const container = document.getElementById("pricing-cards");
  container.innerHTML = dashboardData.companies
    .map(
      (company) => `
        <article class="pricing-card">
          <p class="eyebrow">${company.name}</p>
          <h4>${company.pricingModel}</h4>
          <div class="bullet-list">
            ${company.publicPricingDetails.map((detail) => `<div>${detail}</div>`).join("")}
          </div>
          ${
            company.pricingModel.toLowerCase().includes("sales")
              ? `<p class="warning-text" style="margin-top:12px;">Public pricing is incomplete.</p>`
              : ""
          }
        </article>
      `
    )
    .join("");
}

function renderComparisonTable() {
  const table = document.getElementById("comparison-table");
  const columns = ["Company", "Positioning", "Target Customers", "Differentiators", "Strengths", "Gaps"];
  table.querySelector("thead").innerHTML = `<tr>${columns.map((column) => `<th>${column}</th>`).join("")}</tr>`;
  table.querySelector("tbody").innerHTML = dashboardData.companies
    .map(
      (company) => `
        <tr>
          <td><strong>${company.name}</strong></td>
          <td>${company.positioning}</td>
          <td>${company.targetCustomers.join(", ")}</td>
          <td>${company.differentiators.join(", ")}</td>
          <td>${company.strengths.join(", ")}</td>
          <td>${company.gaps.join(", ")}</td>
        </tr>
      `
    )
    .join("");
}

function renderFeatureMatrix() {
  const table = document.getElementById("feature-matrix");
  const features = Array.from(
    new Set(dashboardData.companies.flatMap((company) => company.coreFeatures))
  );
  table.querySelector("thead").innerHTML = `
    <tr>
      <th>Feature</th>
      ${dashboardData.companies.map((company) => `<th>${company.name}</th>`).join("")}
    </tr>
  `;
  table.querySelector("tbody").innerHTML = features
    .map(
      (feature) => `
        <tr>
          <td><strong>${feature}</strong></td>
          ${dashboardData.companies
            .map((company) => {
              const hasFeature = company.coreFeatures.includes(feature);
              return `<td><span class="feature-cell ${hasFeature ? "" : "is-missing"}">${hasFeature ? "Supported" : "Not clear"}</span></td>`;
            })
            .join("")}
        </tr>
      `
    )
    .join("");
}

function renderCharts() {
  const container = document.getElementById("chart-grid");
  container.innerHTML = dashboardData.charts
    .map((chart) => {
      const svgDataUrl = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(chart.artifactSvg)}`;
      return `
        <article class="chart-card">
          <p class="eyebrow">${chart.type}</p>
          <h4>${chart.title}</h4>
          <p class="muted-copy" style="margin:8px 0 14px;">${chart.description}</p>
          <img src="${svgDataUrl}" alt="${chart.title}" />
        </article>
      `;
    })
    .join("");
}

function renderSources() {
  const container = document.getElementById("source-list");
  container.innerHTML = dashboardData.sources
    .map(
      (source) => `
        <article class="source-card">
          <p class="eyebrow">${source.company}</p>
          <h4><a href="${source.url}" target="_blank" rel="noreferrer">${source.title}</a></h4>
          <p class="source-snippet">${source.snippet}</p>
          <div class="source-meta">
            <span class="meta-chip">${source.id}</span>
            <span class="meta-chip">${source.sourceType.replaceAll("_", " ")}</span>
          </div>
        </article>
      `
    )
    .join("");
}

function renderChatSuggestions() {
  const container = document.getElementById("chat-suggestions");
  container.innerHTML = dashboardData.chatSuggestions
    .map(
      (suggestion) => `
        <button class="suggestion-card ghost-button" type="button" data-suggestion="${escapeAttribute(suggestion)}">
          ${suggestion}
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
          <p style="margin:8px 0 0;">${item.text}</p>
          ${
            item.citations?.length
              ? `<p class="muted-copy" style="margin:10px 0 0;">Sources: ${item.citations
                  .map((citationId) => {
                    const source = dashboardData.sources.find((entry) => entry.id === citationId);
                    return source
                      ? `<a href="${source.url}" target="_blank" rel="noreferrer">\`${citationId}\`</a>`
                      : `\`${citationId}\``;
                  })
                  .join(", ")}</p>`
              : ""
          }
          ${item.uncertainty ? `<p class="warning-text" style="margin:8px 0 0;">${item.uncertainty}</p>` : ""}
        </article>
      `
    )
    .join("");
}

function renderMarkdownPreview() {
  document.getElementById("markdown-preview").textContent = dashboardData.report.markdown;
}

async function handleChatSubmit(event) {
  event.preventDefault();
  const input = document.getElementById("chat-input");
  const question = input.value.trim();
  if (!question) {
    return;
  }

  state.thread.push({ role: "user", text: question, citations: [], uncertainty: null });
  renderChatThread();
  input.value = "";
  const answer = await askSessionChat(question);
  state.thread.push({
    role: "assistant",
    text: answer.answer,
    citations: answer.citation_ids || [],
    uncertainty: answer.uncertainty_note || null,
  });
  renderChatThread();
}

async function askSessionChat(question) {
  try {
    const response = await fetch("/api/chat/answer", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        session_id: dashboardData.session.id,
        question,
        approved_state: buildApprovedStatePayload(),
      }),
    });
    if (!response.ok) {
      throw new Error(`Chat request failed with status ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    return fallbackSessionAnswer(question);
  }
}

function fallbackSessionAnswer(question) {
  const normalized = question.toLowerCase();
  if (normalized.includes("enterprise")) {
    return {
      answer:
        "Zendesk looks strongest for enterprise support operations overall, with Intercom close behind where AI-first workflow clarity matters more than governance breadth.",
      citation_ids: ["source_zendesk_home", "source_intercom_home"],
      uncertainty_note: null,
    };
  }
  if (normalized.includes("pricing")) {
    return {
      answer:
        "Freshworks is the most transparent on public pricing. Zendesk and Intercom expose meaningful packaging, but Forethought remains mostly sales-led, so that part of the comparison is less certain.",
      citation_ids: ["source_freshworks_pricing", "source_zendesk_pricing", "source_intercom_pricing"],
      uncertainty_note: "Pricing comparisons stay directional where sales-led packaging leaves public details incomplete.",
    };
  }
  if (normalized.includes("uncertain") || normalized.includes("confidence")) {
    return {
      answer:
        "Forethought has the thinnest public pricing coverage, and both Zendesk and Intercom still leave some deeper AI pricing details to sales conversations. Those are the biggest uncertainty pockets in this session.",
      citation_ids: ["source_forethought_home", "source_zendesk_pricing", "source_intercom_pricing"],
      uncertainty_note: "This answer is based on public pages only, not private pricing or customer references.",
    };
  }
  if (normalized.includes("differentiator")) {
    return {
      answer:
        "Intercom differentiates on AI-forward product narrative, Zendesk on enterprise service breadth, Freshworks on approachable rollout and pricing clarity, and Forethought on specialist AI automation depth.",
      citation_ids: ["source_intercom_ai", "source_zendesk_home", "source_freshworks_home", "source_forethought_platform"],
      uncertainty_note: null,
    };
  }
  return {
    answer:
      "Within this approved session state, the clearest answer is that Intercom and Zendesk lead overall, but they solve for different buying priorities. The dashboard sections above show where that conclusion is strong and where public evidence is thinner.",
    citation_ids: ["source_intercom_home", "source_zendesk_home"],
    uncertainty_note: "This fallback answer is limited to the currently embedded dashboard state.",
  };
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
  const blob = new Blob([dashboardData.report.markdown], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = "market-mapper-report.md";
  anchor.click();
  URL.revokeObjectURL(url);
}

function buildApprovedStatePayload() {
  const now = new Date().toISOString();
  return {
    session_id: dashboardData.session.id,
    run_id: "run_demo_dashboard",
    user_prompt: dashboardData.session.prompt,
    research_plan: {
      id: "plan_demo_dashboard",
      market_query: dashboardData.plan.marketQuery,
      requested_company_count: dashboardData.plan.requestedCompanyCount,
      named_companies: [],
      geography: null,
      target_segment: null,
      discovery_criteria: dashboardData.plan.discoveryCriteria,
      comparison_dimensions: dashboardData.plan.comparisonDimensions,
      required_outputs: ["dashboard", "markdown_report", "charts"],
      assumptions: dashboardData.plan.assumptions,
      created_at: now,
      updated_at: now,
    },
    dashboard_state: {
      id: "dashboard_demo",
      session_id: dashboardData.session.id,
      run_id: "run_demo_dashboard",
      executive_summary: dashboardData.executiveSummary,
      selected_company_ids: dashboardData.companies.map((company) => company.id),
      comparison_result_id: "comparison_demo",
      report_id: "report_demo",
      chart_ids: dashboardData.charts.map((chart) => chart.id),
      source_document_ids: dashboardData.sources.map((source) => source.id),
      sections: [
        {
          key: "summary",
          title: "Summary",
          summary: dashboardData.executiveSummary,
          content_refs: [],
        },
        {
          key: "sources",
          title: "Sources",
          summary: "Evidence behind the report",
          content_refs: dashboardData.sources.map((source) => source.id),
        },
      ],
      generated_at: now,
      updated_at: now,
    },
    executive_summary: dashboardData.executiveSummary,
    company_profiles: dashboardData.companies.map((company) => ({
      id: company.id,
      name: company.name,
      website: company.website,
      market_category: dashboardData.plan.marketQuery,
      product_summary: company.positioning,
      target_customers: company.targetCustomers,
      core_features: company.coreFeatures,
      ai_capabilities: company.coreFeatures.filter(
        (feature) =>
          feature.toLowerCase().includes("ai") || feature.toLowerCase().includes("agent")
      ),
      integrations: company.integrations,
      pricing_model: company.pricingModel,
      public_pricing_details: company.publicPricingDetails,
      packaging_or_plans: [],
      positioning_statement: company.positioning,
      differentiators: company.differentiators,
      customer_proof_points: [],
      notable_public_metrics: {},
      strengths: company.strengths,
      weaknesses_or_gaps: company.gaps,
      explicit_missing_fields: company.missing,
      claims: [],
      source_document_ids: company.sources,
      confidence: company.confidence,
      updated_at: now,
    })),
    comparison_result: {
      id: "comparison_demo",
      run_id: "run_demo_dashboard",
      company_ids: dashboardData.companies.map((company) => company.id),
      dimensions: dashboardData.plan.comparisonDimensions.map((dimension) =>
        dimension.replaceAll(" ", "_")
      ),
      findings: dashboardData.comparisonFindings.map((finding) => ({
        dimension: finding.dimension,
        summary: finding.summary,
        winner_company_id: null,
        evidence_claim_ids: [],
        notes: [],
      })),
      similarities: ["All companies position AI as part of the support experience."],
      differences: dashboardData.comparisonFindings.map((finding) => finding.summary),
      tradeoffs: dashboardData.tradeoffs,
      ideal_customer_notes: dashboardData.keyTakeaways,
      generated_at: now,
    },
    report: {
      id: "report_demo",
      run_id: "run_demo_dashboard",
      title: dashboardData.report.title,
      executive_summary: dashboardData.executiveSummary,
      sections: [
        {
          heading: "Key Takeaways",
          body: dashboardData.keyTakeaways.map((item) => `- ${item}`).join("\n"),
          citation_ids: dashboardData.sources.slice(0, 4).map((source) => source.id),
        },
      ],
      markdown_body: dashboardData.report.markdown,
      source_document_ids: dashboardData.sources.map((source) => source.id),
      artifact_id: null,
      created_at: now,
    },
    chart_specs: dashboardData.charts.map((chart) => ({
      id: chart.id,
      run_id: "run_demo_dashboard",
      chart_type: chart.type,
      title: chart.title,
      description: chart.description,
      data: [],
      x_field: null,
      y_field: null,
      series_field: null,
      comparison_result_id: "comparison_demo",
      artifact_id: null,
      created_at: now,
    })),
    source_documents: dashboardData.sources.map((source) => ({
      id: source.id,
      url: source.url,
      title: source.title,
      source_type: source.sourceType,
      accessed_at: now,
      snippet: source.snippet,
      snapshot_artifact_id: null,
      metadata: { company_name: source.company },
    })),
    approved_at: now,
  };
}

function populateList(elementId, items) {
  document.getElementById(elementId).innerHTML = items.map((item) => `<li>${item}</li>`).join("");
}

function populateTagList(elementId, items) {
  document.getElementById(elementId).innerHTML = items
    .map((item) => `<li>${item}</li>`)
    .join("");
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
        <text x="${x + barWidth / 2}" y="${y - 10}" text-anchor="middle" font-size="12" fill="#2d3748">${item.value}${valueSuffix}</text>
        <text x="${x + barWidth / 2}" y="${height - 20}" text-anchor="middle" font-size="12" fill="#4a5568">${item.label}</text>
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
