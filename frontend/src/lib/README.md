# Frontend Lib

This folder now holds the reusable browser-client building blocks that keep the dashboard from devolving into one giant handcrafted script:

- `auth.js`
  - access-token storage and auth-aware URL helpers
- `api.js`
  - authenticated JSON/blob request helpers
- `sessionStream.js`
  - EventSource wiring for live workspace, run-status, and approved-dashboard updates

These modules are intentionally lightweight, but they give the frontend a clearer app structure and make a future migration to a fuller framework much easier.
