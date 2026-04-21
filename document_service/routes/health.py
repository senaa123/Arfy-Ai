# document_service/routes/health.py

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    """
    Document service health endpoint.
    """
    return {
        "status": "ok",
        "service": "document_service",
    }