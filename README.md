# Market Mapper

Market Mapper is an OpenAI-powered multi-agent research system that turns a broad market question into a structured, source-backed competitive analysis dashboard.

Give it a prompt like:

> "Analyze 4 of the largest companies in AI customer support and create a comparison report."

It will:

- turn the prompt into a research plan
- discover the right company set
- collect public sources
- extract normalized company profiles
- compare companies across defined dimensions
- verify gaps and retry weak stages when needed
- generate charts and a Markdown report
- assemble a dashboard
- answer follow-up questions from approved research only

## Why This Project Exists

Most market research workflows are slow, manual, and hard to trace back to evidence.

Market Mapper explores a different model:

- use multiple specialized agents instead of one giant prompt
- coordinate them through typed shared state
- let the UI show live progress while research is still happening
- preserve artifacts and sources so the final output stays inspectable

This repository is both:

- a working research application
- a reference architecture for multi-agent workflows

## What Makes It Interesting

Market Mapper combines:

- a planner/executor workflow in LangGraph
- OpenAI-powered specialist agents
- parallel company-level research and extraction
- parallel post-verification output generation
- sandbox-backed browser and artifact execution
- durable run state and resumable snapshots
- live dashboard streaming over SSE
- token-scoped multi-user access controls
- an approved-state-only session chatbot

## Core Capabilities

### Multi-Agent Research Workflow

The system decomposes one research request into specialized stages:

1. research planning
2. workflow routing
3. company discovery
4. source collection
5. structured extraction
6. comparison
7. verification and retry
8. report generation
9. chart generation
10. dashboard assembly
11. approved-state chat

### Parallel Work Where It Matters

Once the company set is known:

- web research fans out into per-company workers
- structured extraction fans out into per-company workers
- report and chart generation run in parallel after approval

That means the system is not just sequential orchestration. It is a real fan-out/fan-in workflow with synthesis stages.

### Live Workspace While The Run Is In Flight

The UI supports two modes:

- **Live workspace** while research is still running
- **Approved dashboard** after verification finishes

While the run is active, the frontend can show:

- current workflow stage
- progress percent
- per-company status
- partial source coverage
- live workflow events
- section-level readiness

### Source-Backed Outputs

The system keeps track of:

- source URLs
- extracted claims
- report citations
- sandbox-generated artifacts

The chatbot answers follow-up questions using only the approved session snapshot, not arbitrary in-memory context.

## High-Level Architecture

Market Mapper uses a planner/executor multi-agent pattern:

- the **planner** turns the raw prompt into a structured plan
- the **executor** decides what should happen next from workflow state
- **specialist agents** handle discovery, research, extraction, comparison, verification, reporting, charting, and dashboard building
- the **verifier** can send the workflow back for targeted retries
- the **frontend** streams live state until the approved dashboard is ready

## Technology Stack

### Backend

- FastAPI
- LangGraph
- OpenAI Responses API
- Pydantic
- Playwright
- Beautiful Soup
- Trafilatura

### Frontend

- HTML
- CSS
- modular browser-side JavaScript
- Server-Sent Events for live updates

### Persistence and Execution

- file-backed durable workflow state
- sandbox artifact storage
- subprocess-based worker execution

## Running The Project

### Requirements

- Python 3.11+
- an OpenAI API key

### 1. Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -e ".[dev]"
python -m playwright install
```

### 3. Set environment variables

At minimum:

```bash
export OPENAI_API_KEY="your_api_key_here"
```

Recommended local development defaults:

```bash
export OPENAI_MODEL="gpt-5-mini"
export OPENAI_REASONING_EFFORT="low"
export OPENAI_ENABLE_WEB_SEARCH="true"
export MARKET_MAPPER_MAX_RESEARCH_RETRIES="2"
export MARKET_MAPPER_STATE_DIR="/tmp/market_mapper/state"
export MARKET_MAPPER_AUTH_TOKENS='{"dev-token":"demo-user"}'
```

Notes:

- `MARKET_MAPPER_STATE_DIR` defaults to `/tmp/market_mapper/state`
- `MARKET_MAPPER_AUTH_TOKENS` maps bearer tokens to user ids
- the frontend assumes the development token `dev-token` unless you change it

### 4. Start the app

```bash
python -m uvicorn market_mapper.api.app:app --reload
```

Once it is running:

- Dashboard: [http://127.0.0.1:8000/dashboard/](http://127.0.0.1:8000/dashboard/)
- API docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

## Starting A Session

The dashboard supports creating sessions directly from the UI, but you can also start a session through the API.

Use the development token locally:

```bash
export MARKET_MAPPER_TOKEN="dev-token"
```

### Create a session

```bash
curl -X POST http://127.0.0.1:8000/api/sessions \
  -H "Authorization: Bearer ${MARKET_MAPPER_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Analyze 4 of the largest companies in AI customer support and create a comparison report."
  }'
```

### Start a run

```bash
curl -X POST http://127.0.0.1:8000/api/sessions/SESSION_ID/runs \
  -H "Authorization: Bearer ${MARKET_MAPPER_TOKEN}"
```

### Check progress

```bash
curl http://127.0.0.1:8000/api/runs/RUN_ID \
  -H "Authorization: Bearer ${MARKET_MAPPER_TOKEN}"
```

### Open the session in the dashboard

[http://127.0.0.1:8000/dashboard/?session_id=SESSION_ID](http://127.0.0.1:8000/dashboard/?session_id=SESSION_ID)

## Streaming and Live Updates

The dashboard no longer depends on polling alone.

While a run is active, the frontend opens a server-sent events stream and receives:

- workspace snapshots
- run status updates
- run event feeds
- the final approved dashboard payload

Route:

- `GET /api/sessions/{session_id}/stream`

This gives the UI a much more natural “live research workspace” feel while agents are still collecting and validating information.

## Sandbox Behavior

Sandbox execution is used for the parts of the workflow that benefit from isolation and reproducibility.

Current sandbox-backed routes include:

- `web_research`
  - page capture
  - screenshots
  - extracted text
- `structured_extraction`
  - per-company evidence packets
- `critic_verifier`
  - verification summaries
  - low-confidence profile reports
- `report_generation`
  - Markdown report artifacts
- `chart_generation`
  - chart image artifacts
- `dashboard_builder`
  - dashboard preview payloads
  - preview summaries

## Authentication Model

The app now supports token-scoped user ownership.

The default local development setup uses:

- token: `dev-token`
- user id: `demo-user`

Auth works through:

- `Authorization: Bearer <token>`
- or `access_token` query param for SSE-compatible endpoints

## Main API Surface

### Auth

- `GET /api/auth/me`

### Sessions

- `POST /api/sessions`
- `GET /api/sessions`
- `GET /api/sessions/{session_id}`
- `GET /api/sessions/{session_id}/workspace`
- `GET /api/sessions/{session_id}/dashboard`
- `GET /api/sessions/{session_id}/stream`
- `DELETE /api/sessions/{session_id}`

### Runs

- `POST /api/sessions/{session_id}/runs`
- `GET /api/runs/{run_id}`
- `GET /api/runs/{run_id}/events`

### Reports

- `GET /api/reports/{report_id}`
- `GET /api/reports/{report_id}/download`

### Artifacts

- `GET /api/artifacts/{artifact_id}`

### Chat

- `POST /api/chat/answer`

## Project Structure

- `src/market_mapper/agents/`
  - OpenAI-powered research agents
- `src/market_mapper/workflow/`
  - graph, routing, node contracts, helpers, shared state
- `src/market_mapper/api/`
  - FastAPI app and route layer
- `src/market_mapper/services/`
  - workflow execution, OpenAI integration, approved snapshot service, worker management
- `src/market_mapper/sandbox/`
  - trusted-harness execution and sandbox runtime handlers
- `src/market_mapper/storage/`
  - durable state storage
- `frontend/`
  - dashboard UI and streaming client
- `tests/`
  - unit tests

## Current Status

Implemented:

- typed shared workflow state
- planner/executor orchestration
- OpenAI-powered specialist agents
- parallel research and extraction
- parallel output generation
- durable run/session/artifact persistence
- live workspace snapshots
- SSE-based live dashboard updates
- sandbox-backed artifact production
- token-scoped session ownership
- approved-state-only chatbot

Still evolving:

- deeper distributed job infrastructure beyond subprocess workers
- more end-to-end integration coverage
- richer orchestration and synthesis patterns across later workflow stages

## Running Tests

```bash
pytest
```

## OpenAI Setup

Create an API key here:

- [OpenAI API keys](https://platform.openai.com/api-keys)

Reference docs:

- [OpenAI quickstart](https://platform.openai.com/docs/quickstart?api-mode=responses)

## Important Note

This project is intentionally OpenAI-powered end to end. If `OPENAI_API_KEY` is missing, the workflow will fail rather than silently falling back to placeholder behavior.
