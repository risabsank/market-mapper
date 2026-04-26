# Market Mapper

Market Mapper is an OpenAI-powered market research app that turns a broad prompt into a structured competitive analysis dashboard.

Today the repo includes:

- a LangGraph planner/executor workflow
- OpenAI-powered specialist agents
- parallel per-company research and extraction workers during the heavy research stages
- parallel output generation for report drafting and chart rendering after approval
- durable session, run, dashboard, report, and artifact persistence
- progressive workspace snapshots, run event feeds, and server-sent event streaming while a session is still in flight
- subprocess-based workflow workers instead of an in-process thread pool
- token-scoped multi-user session ownership checks across sessions, runs, reports, artifacts, and chat
- a FastAPI backend
- a session-backed dashboard UI with modular auth, API, and stream helpers
- a session chatbot that answers only from server-approved research state

## What The App Does

A live session follows this flow:

1. create a research session from a prompt
2. start a workflow run for that session
3. let the backend run planner and discovery
4. fan out per-company web research and per-company structured extraction in parallel where it makes sense
5. merge the shared results back into comparison, verification, reporting, charting, and dashboard assembly
6. stream live workspace progress into the UI while the approved dashboard is still pending
7. open the dashboard with that session id
8. ask follow-up questions in the right-side chat
9. download the generated Markdown report

## Requirements

- Python 3.11+
- an OpenAI API key

## Get an OpenAI API Key

1. Create or log into your OpenAI account.
2. Open [API keys](https://platform.openai.com/api-keys).
3. Create a new key.
4. Export it in your shell before starting the app.

OpenAI quickstart: [Developer quickstart](https://platform.openai.com/docs/quickstart?api-mode=responses)

## Environment Setup

Market Mapper reads the key from `OPENAI_API_KEY`.

On macOS or Linux:

```bash
export OPENAI_API_KEY="your_api_key_here"
```

Optional environment variables:

```bash
export OPENAI_MODEL="gpt-5-mini"
export OPENAI_REASONING_EFFORT="low"
export OPENAI_ENABLE_WEB_SEARCH="true"
export MARKET_MAPPER_MAX_RESEARCH_RETRIES="2"
export MARKET_MAPPER_STATE_DIR="/tmp/market_mapper/state"
export MARKET_MAPPER_AUTH_TOKENS='{"dev-token":"demo-user"}'
```

Notes:

- `OPENAI_MODEL` defaults to `gpt-5-mini`
- `OPENAI_REASONING_EFFORT` defaults to `low`
- `OPENAI_ENABLE_WEB_SEARCH` controls whether web-enabled agents request OpenAI web search tools
- `MARKET_MAPPER_MAX_RESEARCH_RETRIES` caps verifier-driven retry loops before the workflow proceeds with explicit uncertainty
- `MARKET_MAPPER_STATE_DIR` controls where sessions, runs, snapshots, and sandbox artifacts are stored
- `MARKET_MAPPER_AUTH_TOKENS` maps bearer tokens to user ids for the built-in multi-user auth layer
- by default it uses `/tmp/market_mapper/state` so `uvicorn --reload` does not restart the server every time workflow state is written
- by default the frontend uses the development token `dev-token`

## Installation

From the project root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m playwright install
```

## Run The App

Start the API server from the project root:

```bash
python -m uvicorn market_mapper.api.app:app --reload
```

Once the server is running:

- dashboard host: [http://127.0.0.1:8000/dashboard/](http://127.0.0.1:8000/dashboard/)
- API docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

The dashboard now supports two modes:

- `live workspace` while the run is still gathering and validating data
- `approved dashboard` once verification, report generation, chart generation, and dashboard assembly are complete

The dashboard now authenticates every API call with a bearer token and streams live workspace updates over SSE from the backend rather than polling every few seconds.

## Start A Live Session

You now need to create a session, start a run, and then open the dashboard with that session id.

All API requests below use the default development token:

```bash
export MARKET_MAPPER_TOKEN="dev-token"
```

### 1. Create a session

```bash
curl -X POST http://127.0.0.1:8000/api/sessions \
  -H "Authorization: Bearer ${MARKET_MAPPER_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Analyze 4 of the largest companies in AI customer support and create a comparison report."
  }'
```

Example response shape:

```json
{
  "id": "session_...",
  "user_prompt": "Analyze 4 of the largest companies in AI customer support and create a comparison report.",
  "active_run_id": null
}
```

Copy the returned session id.

### 2. Start a workflow run

Replace `SESSION_ID` below with the returned id:

```bash
curl -X POST http://127.0.0.1:8000/api/sessions/SESSION_ID/runs \
  -H "Authorization: Bearer ${MARKET_MAPPER_TOKEN}"
```

This starts the LangGraph workflow and returns the run record.

### 3. Check run progress

Replace `RUN_ID` with the run id returned by the previous step:

```bash
curl http://127.0.0.1:8000/api/runs/RUN_ID \
  -H "Authorization: Bearer ${MARKET_MAPPER_TOKEN}"
```

The response includes:

- the run object
- current node
- percent complete
- completed task count

### 4. Open the real dashboard

Open the dashboard with the session id in the query string:

[http://127.0.0.1:8000/dashboard/?session_id=SESSION_ID](http://127.0.0.1:8000/dashboard/?session_id=SESSION_ID)

The frontend will:

- fetch the session
- open an authenticated server-sent event stream for the session while the run is in progress
- load the live workspace snapshot and run events while the approved dashboard is not ready
- render partial company progress, partial source coverage, section-level statuses, and live activity updates
- switch over to the approved dashboard payload once ready
- render the real report sections, dashboard sections, charts, sources, and chat context

## API Routes

### Sessions

- `GET /api/auth/me`
  - resolve the current authenticated user from the bearer token
- `POST /api/sessions`
  - create a research session from a prompt
- `GET /api/sessions`
  - list the current user's sessions
- `GET /api/sessions/{session_id}`
  - fetch session metadata
- `GET /api/sessions/{session_id}/dashboard`
  - fetch the approved dashboard payload enriched with artifact URLs
- `GET /api/sessions/{session_id}/workspace`
  - fetch the progressive workspace snapshot for a running session
- `GET /api/sessions/{session_id}/stream`
  - stream workspace, run status, run events, and approved dashboard updates over SSE
- `DELETE /api/sessions/{session_id}`
  - delete one session and its durable outputs

### Runs

- `POST /api/sessions/{session_id}/runs`
  - start a workflow run for a session
- `GET /api/runs/{run_id}`
  - inspect run status and progress
- `GET /api/runs/{run_id}/events`
  - fetch the run event feed derived from checkpoints and task activity

### Reports

- `GET /api/reports/{report_id}`
  - fetch the generated report object
- `GET /api/reports/{report_id}/download`
  - download the sandbox-produced Markdown report artifact when present, otherwise the saved Markdown body

### Artifacts

- `GET /api/artifacts/{artifact_id}`
  - serve persisted chart, dashboard, and other sandbox artifacts

### Chat

- `POST /api/chat/answer`
  - production chat route
  - accepts only `session_id` and `question`
  - resolves answers from server-approved snapshot state
- `POST /api/chat/demo-answer`
  - demo-only route for inline approved-state payloads

## How The Dashboard Works

The dashboard is no longer bootstrapped from hardcoded demo data.

It now:

- loads real approved session data from the backend
- loads a live workspace snapshot while the approved dashboard is still pending
- shows parallel company progress and live workflow activity
- shows loading and error states while runs are still executing
- renders approved `DashboardState.sections`
- renders approved report sections
- uses served chart artifact URLs when available
- downloads the report from the backend route
- sends chat questions using only `session_id`

## Parallel Workflow Model

Market Mapper is no longer a purely sequential research pipeline.

The current model is:

1. planner builds the research plan
2. executor routes into discovery
3. once the company set is known, web research fans out into parallel per-company workers
4. structured extraction fans out into parallel per-company workers
5. those partial company results are persisted into a live workspace snapshot
6. comparison, verification, reporting, charts, and dashboard assembly fan back in over the shared state

This gives the UI something meaningful to render before the final approved dashboard is ready.

## Worker Model

Workflow runs no longer execute inside the API server's in-process thread pool.

Instead:

1. the API creates a durable run record
2. the run job manager starts a dedicated subprocess worker
3. the worker executes `python -m market_mapper.worker RUN_ID`
4. the worker persists live state as the graph advances
5. the dashboard streams those persisted updates

This keeps long-running LLM and sandbox work isolated from the request-handling process.

## Sandbox Behavior

The sandbox layer is now more than simple payload preservation:

- `web_research` captures pages, screenshots, and extracted text
- `structured_extraction` emits per-company evidence packets for downstream review
- `critic_verifier` emits verification summaries and low-confidence profile reports
- `report_generation` renders Markdown artifacts
- `chart_generation` renders chart image artifacts
- `dashboard_builder` emits dashboard preview payloads and human-readable preview summaries

## Packages Used

Core dependencies declared in `pyproject.toml`:

- `openai`
- `langgraph`
- `pydantic`
- `playwright`
- `beautifulsoup4`
- `trafilatura`
- `pandas`
- `jinja2`

Dev dependency:

- `pytest`

## Project Structure

- `src/market_mapper/agents/`
  OpenAI-powered planner, executor, research, extraction, comparison, verifier, report, chart, dashboard, and chat agents
- `src/market_mapper/workflow/`
  graph, node contracts, routing, helpers, progressive snapshot building, and shared workflow state
- `src/market_mapper/api/`
  FastAPI app plus routes for sessions, runs, reports, artifacts, and chat
- `src/market_mapper/storage/`
  durable file-backed persistence for sessions, runs, live workspace snapshots, dashboards, sandbox tasks, and artifacts
- `src/market_mapper/services/`
  OpenAI integration, workflow execution service, and approved session snapshot service
- `src/market_mapper/sandbox/`
  trusted-harness sandbox orchestration and local runtime handlers
- `frontend/`
  dashboard UI, live workspace rendering, run activity feed, and right-side session chat
- `tests/`
  unit tests for workflow, state, sandbox, and service behavior

## Current Status

Implemented:

- typed Pydantic models for all main workflow entities
- durable file-backed state storage
- LangGraph workflow graph and node flow
- OpenAI-powered agents with structured outputs
- sandbox-backed web research, report artifacts, chart artifacts, and dashboard preview artifacts
- session/run/report/artifact/chat API routes
- live workspace snapshot and run events APIs
- session-backed dashboard loading
- progressive dashboard filling while the run is still in progress
- server-approved chatbot state

Still worth improving:

- more comprehensive backend integration tests
- websockets layered on top of the existing SSE stream for richer bidirectional collaboration
- deeper fan-out/fan-in orchestration beyond the current parallel company stages

## Running Tests

After installing dependencies:

```bash
pytest
```

## Important Note

This app assumes OpenAI is the primary intelligence layer. If `OPENAI_API_KEY` is missing, OpenAI-backed agents will fail instead of silently falling back to local placeholder behavior.
