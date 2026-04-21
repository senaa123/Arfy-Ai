# memory_service/main.py

from fastapi import FastAPI

from memory_service.db import Base, engine
from memory_service.qdrant_store import ensure_all_collections
from memory_service.routes.actions import router as actions_router
from memory_service.routes.documents import router as documents_router
from memory_service.routes.health import router as health_router
from memory_service.routes.memory import router as memory_router
from memory_service.routes.sessions import router as sessions_router

# Create DB tables on startup.
#
# We are intentionally keeping this bootstrap behavior in main.py because it is
# application startup wiring, not route logic.
Base.metadata.create_all(bind=engine)

VECTOR_INIT_ERROR: str | None = None
try:
    ensure_all_collections()
except Exception as e:
    VECTOR_INIT_ERROR = str(e)

app = FastAPI(title="Arfy Memory Service")
app.state.vector_init_error = VECTOR_INIT_ERROR

# Phase 4B:
# - keep the same service
# - keep the same endpoints
# - move route ownership into modules grouped by responsibility
app.include_router(health_router)
app.include_router(memory_router)
app.include_router(actions_router)
app.include_router(documents_router)
app.include_router(sessions_router)