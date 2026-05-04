"""
Health route for rag_service.

Use this for smoke tests and service readiness checks.
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "rag_service"}