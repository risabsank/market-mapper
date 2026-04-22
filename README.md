# Market Mapper

Market Mapper is an OpenAI-powered market research system that turns a broad research prompt into a structured competitive analysis dashboard.

It is organized around:

- a planner/executor workflow built with LangGraph
- specialist agents powered by the OpenAI Responses API
- durable workflow state for sessions, runs, tasks, artifacts, approvals, and retries
- a future dashboard and session chatbot built on the same typed state

## What Is OpenAI-Powered

The current agent layer is designed to use OpenAI for:

- `Research Planner`
- `Workflow Executor`
- `Company Discovery Agent`
- `Web Research Agent`
- `Structured Extraction Agent`
- `Comparison Agent`
- `Critic and Verifier Agent`
- `Report Generation Agent`
- `Chart Generation Agent`
- `Dashboard Builder`
- `Session Chatbot`

These agents use the OpenAI Responses API with structured JSON schema output so each step returns typed models instead of raw free-form text.

## Requirements

- Python 3.11+
- an OpenAI API key

## How To Get an OpenAI API Key

1. Create or log into your OpenAI account.
2. Open the API keys page: [platform.openai.com/api-keys](https://platform.openai.com/api-keys)
3. Create a new key.
4. Export it in your shell before running the project.

OpenAI's official quickstart also shows the environment variable setup flow: [Developer quickstart](https://platform.openai.com/docs/quickstart?api-mode=responses)

## Where To Put the API Key

Market Mapper reads the API key from the `OPENAI_API_KEY` environment variable.

On macOS or Linux:

```bash
export OPENAI_API_KEY="your_api_key_here"
```

If you want it available every time you open a terminal, add that line to your shell config such as `~/.zshrc` or `~/.bashrc`, then reload your shell:

```bash
source ~/.zshrc
```

You can also set optional environment variables:

```bash
export OPENAI_MODEL="gpt-5-mini"
export OPENAI_REASONING_EFFORT="low"
export OPENAI_ENABLE_WEB_SEARCH="true"
export MARKET_MAPPER_STATE_DIR=".market_mapper/state"
```

Notes:

- `OPENAI_MODEL` defaults to `gpt-5-mini`
- `OPENAI_REASONING_EFFORT` defaults to `low`
- `OPENAI_ENABLE_WEB_SEARCH` controls whether web-enabled agents request OpenAI web search tools

`gpt-5-mini` is a good default because it supports structured outputs and the Responses API while being faster and cheaper than larger models. Official model page: [GPT-5 mini](https://platform.openai.com/docs/models/gpt-5-mini)

## Installation

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install the project and dev dependencies:

```bash
pip install -e ".[dev]"
```

Install Playwright browser binaries:

```bash
python -m playwright install
```

## Packages Used

Core packages currently declared in `pyproject.toml`:

- `openai`
- `langgraph`
- `pydantic`
- `playwright`
- `beautifulsoup4`
- `trafilatura`
- `pandas`
- `jinja2`

Dev packages:

- `pytest`

## Project Structure

- `docs/` for planning docs
- `src/market_mapper/agents/` for OpenAI-powered agents
- `src/market_mapper/workflow/` for graph state, routes, contracts, and nodes
- `src/market_mapper/schemas/` for typed models
- `src/market_mapper/storage/` for durable workflow state persistence
- `src/market_mapper/services/` for shared services such as OpenAI API integration
- `frontend/` for the future dashboard and session chat UI
- `tests/` for unit and integration tests

## Current Status

Implemented so far:

- typed Pydantic models for sessions, runs, tasks, artifacts, reports, charts, and dashboard state
- durable file-backed workflow state store
- LangGraph workflow skeleton with planner/executor routing
- OpenAI-powered specialist agent layer using structured outputs
- trusted-harness sandbox layer with route-specific sandbox tasks and artifact generation
- sandbox-backed web research using Playwright page capture plus extracted text artifacts

Not implemented yet:

- real backend API endpoints
- real frontend dashboard

## Running Tests

After installing dependencies:

```bash
pytest
```

Some tests may need mocking or API-key-aware setup as the project becomes more deeply OpenAI-backed.

## Important Implementation Note

This repository now assumes OpenAI is the primary intelligence layer. If `OPENAI_API_KEY` is missing, OpenAI-backed agents will raise a configuration error instead of silently falling back to local placeholder logic.
