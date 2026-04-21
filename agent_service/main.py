# agent_service/main.py

from fastapi import FastAPI

from agent_service.graph import build_graph
from agent_service.routes.ask import router as ask_router
from agent_service.routes.documents import router as documents_router
from agent_service.routes.health import router as health_router
from agent_service.routes.sessions import router as sessions_router
from agent_service.session import SessionStore

app = FastAPI(title="Arfy Agent Service")

# Keep long-lived runtime objects at application startup.
#
# Phase 4B purpose:
# - main.py should own bootstrap/runtime wiring
# - route handlers should move into focused modules
# - orchestration behavior should remain unchanged
app.state.graph = build_graph()
app.state.session_store = SessionStore(max_turns=12)

app.include_router(health_router)
app.include_router(ask_router)
app.include_router(documents_router)
app.include_router(sessions_router)