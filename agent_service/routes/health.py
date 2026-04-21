# agent_service/routes/health.py

from fastapi import APIRouter

from agent_service.plugins.registry import registry

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    """
    Basic health endpoint.
    """
    return {
        "status": "ok",
        "service": "agent",
        "tools": registry.list_specs(),
    }