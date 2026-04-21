# Implementation Plan

## Current Repository State

The current codebase contains only two project documents:

- `AGENTS.md`
- `scope.md`

There is no existing application code yet, so the implementation plan starts from a clean slate.

## Implementation Goals

Build the project exactly as scoped in `scope.md`:

- a planner and executor based multi-agent workflow
- sandbox-backed execution where it adds value
- a backend that manages sessions, runs, artifacts, and chat
- a dashboard that presents the report, tables, charts, and sources
- a session-specific chatbot that answers follow-up questions from approved research state

## Ordered Phases

### Phase 1: Foundation and Types

Create the core package layout, shared configuration points, and typed models for:

- research sessions
- research plans
- workflow runs
- agent tasks
- sandbox tasks and artifacts
- company profiles
- comparison results
- verification results
- chart specs
- reports
- dashboard state

This phase gives the rest of the system a stable vocabulary.

### Phase 2: Workflow Spine

Implement the planner and executor graph skeleton in LangGraph:

- `Research Planner`
- `Workflow Executor`
- graph state container
- node routing
- task lifecycle tracking
- retry and verification loop boundaries

This phase should make the orchestration path visible even if downstream agents are still placeholders.

### Phase 3: Research Pipeline

Implement the agent pipeline in order:

1. `Company Discovery Agent`
2. `Web Research Agent`
3. `Structured Extraction Agent`
4. `Comparison Agent`
5. `Critic and Verifier Agent`

This is the core research path that turns a user prompt into structured analysis.

### Phase 4: Sandbox Runtime

Implement sandbox-backed execution for the tasks that benefit from isolation:

- browser automation
- page capture and snapshots
- temporary extraction artifacts
- chart rendering
- report artifact generation
- validation passes over generated files

The trusted harness should continue to own orchestration, approvals, run state, and recovery.

### Phase 5: Output Generation

Implement:

- `Report Generation Agent`
- `Chart Generation Agent`
- `Dashboard Builder`

This phase turns approved analysis into a user-facing output package.

### Phase 6: Backend API Layer

Implement API surfaces for:

- creating and reading research sessions
- starting and inspecting workflow runs
- fetching dashboard state
- downloading Markdown reports
- chatting against the approved research session state

This phase connects orchestration to the frontend.

### Phase 7: Frontend Dashboard

Build the dashboard UI around one research session:

- prompt summary
- research plan
- executive summary
- company selection rationale
- comparison table
- feature matrix
- pricing section
- charts
- key takeaways
- sources
- Markdown download

### Phase 8: Session Chatbot

Implement the collapsible right-side session chatbot that answers follow-up questions using only the current session's approved state and source-backed claims.

### Phase 9: Testing and Hardening

Add:

- unit tests for schemas and transformations
- fixture-based tests for extraction and verification
- integration tests for workflow state transitions
- API tests for sessions, runs, reports, and chat

## Core Modules

### `src/market_mapper/workflow/`

Owns the LangGraph workflow shape, node registration, and orchestration state transitions.

### `src/market_mapper/agents/`

Owns the planner, executor, specialist agents, and the prompt boundaries for each role.

### `src/market_mapper/schemas/`

Owns the typed models and state objects passed between workflow steps and APIs.

### `src/market_mapper/sandbox/`

Owns sandbox task definitions, runtime adapters, artifact handling, and validation boundaries.

### `src/market_mapper/research/`

Owns lower-level research utilities such as fetching, parsing, extraction helpers, and source normalization.

### `src/market_mapper/reports/`

Owns report composition, Markdown generation, and export handling.

### `src/market_mapper/charts/`

Owns chart specs, chart data preparation, and rendered chart artifact handling.

### `src/market_mapper/storage/`

Owns persistence interfaces for workflow runs, artifacts, session state, and caches.

### `src/market_mapper/api/`

Owns the backend app entrypoint and route surfaces for sessions, runs, reports, and chat.

### `frontend/`

Owns the dashboard shell, report views, comparison UI, chart presentation, and session chatbot.

## Missing Decisions

These decisions are still open and should be resolved before deep implementation:

1. Backend framework:
   The scope implies APIs, but it does not explicitly choose FastAPI, Flask, or another framework.

2. Frontend framework:
   The scope describes a dashboard and collapsible chat, but it does not explicitly choose Next.js, React with Vite, or another stack.

3. Persistence model:
   The scope names Redis as useful, but it does not define what should be durable in Redis versus stored in files or a database.

4. Search and web discovery provider:
   The scope says web research and public discovery are needed, but it does not yet choose the exact search provider or tool contract.

5. Sandbox runtime contract:
   The scope says to use sandbox agents where useful, but it does not define the exact adapter layer, artifact schema, or retry policy.

6. Authentication and user scope:
   The scope is session-centric and does not currently define user accounts, auth, or multi-user separation.

7. Chart rendering approach:
   The scope requires charts, but it does not specify whether charts are rendered server-side, client-side, or both.

8. Source citation format:
   The scope requires source traceability, but the exact citation structure for dashboard cards, report sections, and chat answers is still open.

## Recommended Next Step

Implement the typed schemas and workflow skeleton first. That gives the planner, executor, sandbox, API, and frontend layers a shared contract before the research logic gets deeper.

