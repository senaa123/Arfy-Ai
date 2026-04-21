# agent_service/routes/ask.py

from fastapi import APIRouter, Request
from starlette.concurrency import run_in_threadpool

from agent_service.models import AgentRequest, AgentResponse, GraphState
from agent_service.route_helpers import (
    archive_overflow,
    handle_pending_confirmation,
    load_memory_context_for_text,
    store_pending_action_if_present,
)

router = APIRouter(tags=["agent"])


@router.post("/agent/ask", response_model=AgentResponse)
async def agent_ask(req: AgentRequest, request: Request):
    """
    Main endpoint used by the desktop app.

    Phase 3B change:
    - agent now loads full memory_context
    - graph still gets merged memories for compatibility
    - but now also gets exact/document/semantic breakdown

    Phase 4B:
    - route moved out of main.py only
    - graph/session runtime still belong to agent_service
    """
    session_store = request.app.state.session_store
    graph = request.app.state.graph

    overflowed_user = session_store.add_user_message(req.session_id, req.text)

    await archive_overflow(
        session_id=req.session_id,
        messages=overflowed_user,
        session_started_at=session_store.get_started_at(req.session_id),
        chunk_reason="overflow_after_user_message",
    )

    pending_result = await handle_pending_confirmation(req, session_store)
    if pending_result is not None:
        return pending_result

    memory_context = await run_in_threadpool(
        load_memory_context_for_text,
        req.text,
    )
    relevant_memories = memory_context.get("merged", [])

    state = GraphState(
        session_id=req.session_id,
        user_text=req.text,
        memories=relevant_memories,
        memory_context=memory_context,
        history=session_store.get_history(req.session_id),
        pending_action=session_store.get_pending_action(req.session_id),
    )

    final_state = await run_in_threadpool(graph.invoke, state)

    if isinstance(final_state, dict):
        response_text = final_state.get("response", "Sorry, I couldn't process that.")
        action = final_state.get("action")
        confidence = final_state.get("confidence", 0.0)
        tool_used = final_state.get("tool_used")
        tool_result = final_state.get("tool_result")
    else:
        response_text = final_state.response or "Sorry, something went wrong."
        action = final_state.action
        confidence = final_state.confidence
        tool_used = final_state.tool_used
        tool_result = final_state.tool_result

    store_pending_action_if_present(session_store, req.session_id, tool_result)

    overflowed_ai = session_store.add_ai_message(req.session_id, response_text)

    await archive_overflow(
        session_id=req.session_id,
        messages=overflowed_ai,
        session_started_at=session_store.get_started_at(req.session_id),
        chunk_reason="overflow_after_assistant_message",
    )

    return AgentResponse(
        response=response_text,
        action=action,
        confidence=confidence,
        tool_used=tool_used,
        session_id=req.session_id,
    )