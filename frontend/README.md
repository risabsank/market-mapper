# Frontend

The dashboard is still plain HTML/CSS/JS, but it is no longer a single monolithic handcrafted file.

Current shape:

- `index.html`
  - static shell and layout
- `app.js`
  - orchestration and rendering entrypoint
- `src/lib/auth.js`
  - token resolution and auth-aware URL helpers
- `src/lib/api.js`
  - shared authenticated fetch helpers
- `src/lib/sessionStream.js`
  - SSE client for live workspace updates

This keeps the browser client light while still giving it a real application structure for:

- authenticated API calls
- live session streaming
- reusable report and artifact retrieval
- progressive rendering from workspace snapshots into approved dashboards
