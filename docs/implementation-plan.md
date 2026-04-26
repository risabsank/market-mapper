## Implementation Notes

Market Mapper now runs as a planner/executor research system with a progressive dashboard experience.

### Current Workflow Shape

1. `Research Planner`
   - turns the user prompt into a structured `ResearchPlan`

2. `Workflow Executor`
   - decides the next route from workflow state
   - announces when a stage will fan out into parallel company workers
   - caps verifier-driven retry loops so the run can finish with explicit uncertainty

3. `Company Discovery`
   - selects the working company set

4. `Parallel Company Research`
   - web research fans out into one worker per company
   - each worker plans sources for its company
   - partial source results are persisted as they complete

5. `Parallel Company Extraction`
   - structured extraction fans out into one worker per company
   - each worker produces a normalized company profile
   - partial profile results are persisted as they complete

6. `Fan-In Output Stages`
   - comparison
   - critic/verifier
   - parallel output generation
     - report generation
     - chart generation
   - dashboard builder
   - session chatbot readiness

### Progressive Delivery

The backend now persists a `WorkspaceSnapshot` for each session while the run is in progress.

That snapshot includes:

- prompt and research plan
- current node and progress
- per-company statuses
- partial source documents
- partial company profiles
- section-level readiness across plan, discovery, research, extraction, comparison, report, charts, and dashboard

The API exposes:

- `GET /api/sessions/{session_id}/workspace`
- `GET /api/runs/{run_id}/events`
- `GET /api/sessions/{session_id}/stream`

The frontend uses those endpoints while the final approved dashboard is still pending, then switches to the approved dashboard payload when ready.

### Persistence Model

Durable state now includes:

- sessions
- runs
- workspace snapshots
- approved dashboards
- sandbox tasks
- sandbox artifacts
- auth-scoped approved session snapshots

This keeps partial progress visible even when the run has not finished.

### Parallelism Boundaries

Parallelism currently applies where it is most valuable and least risky:

- per-company web research
- per-company structured extraction
- report and chart generation after verification approval

The remaining stages still run as shared fan-in stages because they depend on the aggregate research state.

### Remaining Opportunities

The next logical upgrade would be moving from subprocess workers to a dedicated external queue/worker system and optionally layering websockets on top of the existing SSE stream for richer bidirectional coordination.
