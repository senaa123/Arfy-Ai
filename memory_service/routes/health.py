# memory_service/routes/health.py

from fastapi import APIRouter, Request

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(request: Request):
    """
    Basic health endpoint.

    Phase 4B note:
    - vector_init_error now lives on app.state
    - this keeps bootstrap concerns in main.py
    - and keeps route files focused on endpoint behavior
    """
    return {
        "status": "ok",
        "service": "memory",
        "layers": ["session_ram", "structured_sqlite", "vector_qdrant"],
        "vector_init_error": getattr(request.app.state, "vector_init_error", None),
    }