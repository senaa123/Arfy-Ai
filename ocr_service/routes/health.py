# ocr_service/routes/health.py

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    """
    OCR service health endpoint.
    """
    return {
        "status": "ok",
        "service": "ocr_service",
    }