"""
FastAPI bootstrap for rag_service.

Keep this file small.
It should only create the app and register routes.
"""

from __future__ import annotations

from fastapi import FastAPI

from rag_service.config import settings
from rag_service.routes.ask import router as ask_router
from rag_service.routes.health import router as health_router

app = FastAPI(title=settings.SERVICE_NAME)

app.include_router(health_router)
app.include_router(ask_router)