"""FastAPI application entrypoint for Market Mapper."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from market_mapper.api.routes import (
    artifacts_router,
    chat_router,
    reports_router,
    runs_router,
    sessions_router,
)


def create_app() -> FastAPI:
    """Create the Market Mapper API and frontend host app."""

    app = FastAPI(title="Market Mapper")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(artifacts_router)
    app.include_router(chat_router)
    app.include_router(sessions_router)
    app.include_router(runs_router)
    app.include_router(reports_router)

    frontend_dir = Path(__file__).resolve().parents[3] / "frontend"
    if frontend_dir.exists():
        app.mount("/dashboard", StaticFiles(directory=frontend_dir, html=True), name="dashboard")

    @app.get("/")
    def root() -> RedirectResponse:
        return RedirectResponse(url="/dashboard/")

    return app


app = create_app()
