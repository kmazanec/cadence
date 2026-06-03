"""FastAPI application entry point.

Startup validation ensures the model configuration is correct before the app
begins serving. The /chat route is an SSE stream driven by the hub graph.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Load .env before any model config reads env vars.
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass  # python-dotenv is optional; env vars may be set by the shell/container

from .api.chat import router as chat_router
from .models.registry import validate_model_config
from .observability.tracer import enable_vendor_tracer


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    # Fail fast: refuse to start if a structured-output role is misconfigured.
    validate_model_config()

    # Turn on vendor tracing when its key is present; a no-op otherwise.
    enable_vendor_tracer()

    app = FastAPI(title="Cadence", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(chat_router)

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    return app


# Module-level app instance for uvicorn (`uvicorn backend.app.main:app`).
app = create_app()
