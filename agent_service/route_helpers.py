# agent_service/route_helpers.py

from starlette.concurrency import run_in_threadpool

from agent_service.brain import (
    build_final_response,
    is_confirmation_text,
    is_rejection_text,
)
from agent_service.models import AgentRequest, AgentResponse, PendingAction
from agent_service.plugins.executor import execute_registered_tool
from agent_service.services.memory_gateway import retrieve_memory_context
from agent_service.tools.memory_tool import archive_session_chunk


async def archive_overflow(
    *,
    session_id: str,
    messages,
    session_started_at: str | None,
    chunk_reason: str,
) -> None:
    """
    Archive overflowed RAM messages to memory_service.

    This logic used to live in main.py. In Phase 4B it moves here so
    route files can stay focused on endpoint behavior.
    """
    if not messages:
        return

    await run_in_threadpool(
        archive_session_chunk,
        session_id=session_id,
        messages=messages,
        session_started_at=session_started_at,
        chunk_reason=chunk_reason,
    )


def store_pending_action_if_present(session_store, session_id: str, tool_result: dict | None) -> None:
    """
    Store a pending action if a tool returns one.
    """
    if not isinstance(tool_result, dict):
        return

    pending_payload = tool_result.get("pending_action")
    if not isinstance(pending_payload, dict):
        return

    session_store.set_pending_action(session_id, PendingAction(**pending_payload))


def load_memory_context_for_text(user_text: str) -> dict:
    """
    Ask memory_service for richer memory context.

    Phase 3B:
    - agent now owns exact/document/semantic memory context
    """
    return retrieve_memory_context(
        user_text,
        exact_limit=3,
        semantic_limit=5,
    )


async def handle_pending_confirmation(req: AgentRequest, session_store) -> AgentResponse | None:
    """
    Handle yes/no replies for an already-stored pending action.
    """
    pending_action = session_store.get_pending_action(req.session_id)

    if pending_action is None:
        return None

    if is_rejection_text(req.text):
        session_store.clear_pending_action(req.session_id)

        response_text = "Okay, I won't do that."
        overflowed_ai = session_store.add_ai_message(req.session_id, response_text)

        await archive_overflow(
            session_id=req.session_id,
            messages=overflowed_ai,
            session_started_at=session_store.get_started_at(req.session_id),
            chunk_reason="overflow_after_assistant_message",
        )

        return AgentResponse(
            response=response_text,
            action=None,
            confidence=0.95,
            tool_used=None,
            session_id=req.session_id,
        )

    if not is_confirmation_text(req.text):
        return None

    memory_query = (
        pending_action.payload.get("memory_query")
        or pending_action.payload.get("location")
        or pending_action.intent
    )

    memory_context = await run_in_threadpool(
        load_memory_context_for_text,
        str(memory_query),
    )
    relevant_memories = memory_context.get("merged", [])

    tool_used, tool_result = await run_in_threadpool(
        execute_registered_tool,
        session_id=req.session_id,
        user_text=req.text,
        tool_name=pending_action.tool_name,
        intent=pending_action.intent,
        extracted_data=pending_action.payload,
        memories=relevant_memories,
        history=session_store.get_history(req.session_id),
    )

    response_text = await run_in_threadpool(
        build_final_response,
        user_text=req.text,
        intent=pending_action.intent,
        tool_used=tool_used or "",
        tool_result=tool_result,
        action=None,
        memories=relevant_memories,
        history=session_store.get_history(req.session_id),
        memory_context=memory_context,
    )

    session_store.clear_pending_action(req.session_id)

    overflowed_ai = session_store.add_ai_message(req.session_id, response_text)

    await archive_overflow(
        session_id=req.session_id,
        messages=overflowed_ai,
        session_started_at=session_store.get_started_at(req.session_id),
        chunk_reason="overflow_after_assistant_message",
    )

    return AgentResponse(
        response=response_text,
        action=None,
        confidence=0.98,
        tool_used=tool_used,
        session_id=req.session_id,
    )