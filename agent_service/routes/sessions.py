# agent_service/routes/sessions.py

from fastapi import APIRouter, Request
from starlette.concurrency import run_in_threadpool

from agent_service.tools.memory_tool import finalize_session_archive

router = APIRouter(tags=["sessions"])


@router.post("/agent/reset")
async def reset_session(session_id: str, request: Request):
    """
    Force-reset session from RAM without archiving.
    Useful for debugging only.
    """
    session_store = request.app.state.session_store
    session_store.reset(session_id)
    return {"status": "reset", "session_id": session_id}


@router.post("/agent/session/end")
async def end_session(session_id: str, request: Request):
    """
    Finalize the session when Arfy goes to sleep.
    """
    session_store = request.app.state.session_store
    session_data = session_store.end_session(session_id)

    result = await run_in_threadpool(
        finalize_session_archive,
        session_id=session_data["session_id"],
        messages=session_data["messages"],
        session_started_at=session_data["session_started_at"],
        session_ended_at=session_data["session_ended_at"],
    )

    return {
        "status": "ended",
        "session_id": session_id,
        "archive_result": result,
    }