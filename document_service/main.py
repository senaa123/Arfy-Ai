# document_service/main.py

from fastapi import FastAPI

from document_service.routes.documents import router as documents_router
from document_service.routes.health import router as health_router

app = FastAPI(title="Arfy Document Service")

# Phase 4B:
# - keep main.py as bootstrap only
# - move route handlers into focused route modules
# - keep document orchestration logic inside document_service,
#   but outside the HTTP route layer
app.include_router(health_router)
app.include_router(documents_router)