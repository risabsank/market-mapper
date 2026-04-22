# Market Mapper

Market Mapper is an OpenAI-powered market research app that turns a broad prompt into a structured competitive analysis dashboard.

Today the repo includes:

- a LangGraph planner/executor workflow
- OpenAI-powered specialist agents
- durable session, run, dashboard, report, and artifact persistence
- a FastAPI backend
- a session-backed dashboard UI
- a session chatbot that answers only from server-approved research state

## What The App Does

A live session follows this flow:

1. create a research session from a prompt
2. start a workflow run for that session
3. let the backend run planner, discovery, research, extraction, comparison, verification, reporting, charting, and dashboard assembly
4. open the dashboard with that session id
5. ask follow-up questions in the right-side chat
6. download the generated Markdown report

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
export MARKET_MAPPER_STATE_DIR="/tmp/market_mapper/state"
```

Notes:

- `OPENAI_MODEL` defaults to `gpt-5-mini`
- `OPENAI_REASONING_EFFORT` defaults to `low`
- `OPENAI_ENABLE_WEB_SEARCH` controls whether web-enabled agents request OpenAI web search tools
- `MARKET_MAPPER_STATE_DIR` controls where sessions, runs, snapshots, and sandbox artifacts are stored
- by default it uses `/tmp/market_mapper/state` so `uvicorn --reload` does not restart the server every time workflow state is written

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

## Start A Live Session

You now need to create a session, start a run, and then open the dashboard with that session id.

### 1. Create a session

```bash
curl -X POST http://127.0.0.1:8000/api/sessions \
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
curl -X POST http://127.0.0.1:8000/api/sessions/SESSION_ID/runs
```

This starts the LangGraph workflow and returns the run record.

### 3. Check run progress

Replace `RUN_ID` with the run id returned by the previous step:

```bash
curl http://127.0.0.1:8000/api/runs/RUN_ID
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
- poll the run while it is still in progress
- load the approved dashboard payload once ready
- render the real report sections, dashboard sections, charts, sources, and chat context

## API Routes

### Sessions

- `POST /api/sessions`
  - create a research session from a prompt
- `GET /api/sessions/{session_id}`
  - fetch session metadata
- `GET /api/sessions/{session_id}/dashboard`
  - fetch the approved dashboard payload enriched with artifact URLs

### Runs

- `POST /api/sessions/{session_id}/runs`
  - start a workflow run for a session
- `GET /api/runs/{run_id}`
  - inspect run status and progress

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
- shows loading and error states while runs are still executing
- renders approved `DashboardState.sections`
- renders approved report sections
- uses served chart artifact URLs when available
- downloads the report from the backend route
- sends chat questions using only `session_id`

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
  graph, node contracts, routing, helpers, and shared workflow state
- `src/market_mapper/api/`
  FastAPI app plus routes for sessions, runs, reports, artifacts, and chat
- `src/market_mapper/storage/`
  durable file-backed persistence for sessions, runs, dashboards, sandbox tasks, and artifacts
- `src/market_mapper/services/`
  OpenAI integration, workflow execution service, and approved session snapshot service
- `src/market_mapper/sandbox/`
  trusted-harness sandbox orchestration and local runtime handlers
- `frontend/`
  dashboard UI and right-side session chat
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
- session-backed dashboard loading
- server-approved chatbot state

Still worth improving:

- a first-class prompt entry screen in the frontend so users can create sessions without using the API directly
- more comprehensive backend integration tests
- stronger end-to-end run monitoring and retries in the UI

## Running Tests

After installing dependencies:

```bash
pytest
```

## Important Note

This app assumes OpenAI is the primary intelligence layer. If `OPENAI_API_KEY` is missing, OpenAI-backed agents will fail instead of silently falling back to local placeholder behavior.
