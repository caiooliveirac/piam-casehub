"""FastAPI application entrypoint (web service).

Mounts session middleware, static files and all web routes. The Telegram bot
runs as a separate process (app/bot/runner.py), not inside this app.
"""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.config import settings
from app.web.routes import router

# Hide the interactive API docs in production — this is an internal admin tool
# and the OpenAPI schema would otherwise disclose every route without auth.
_docs_kwargs = (
    {"docs_url": None, "redoc_url": None, "openapi_url": None}
    if settings.is_production
    else {}
)
app = FastAPI(title=settings.app_name, **_docs_kwargs)

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    https_only=settings.is_production,
    same_site="lax",
)

_STATIC_DIR = os.path.join(os.path.dirname(__file__), "web", "static")
app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")

app.include_router(router)
