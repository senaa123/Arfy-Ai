# ocr_service/main.py

from fastapi import FastAPI

from ocr_service.routes.health import router as health_router
from ocr_service.routes.ocr import router as ocr_router

app = FastAPI(title="Arfy OCR Service")

# Phase 4B:
# - keep main.py as bootstrap only
# - keep OCR route logic in a focused route file
# - keep OCR computation inside engine.py where it already belongs
app.include_router(health_router)
app.include_router(ocr_router)