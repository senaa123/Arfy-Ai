from fastapi import FastAPI
from starlette.concurrency import run_in_threadpool

from agent_service.brain import (
    build_final_response,
    is_confirmation_text,
    is_rejection_text,
)
from agent_service.graph import build_graph
from agent_service.models import AgentRequest, AgentResponse, GraphState, PendingAction
from agent_service.session import SessionStore
from agent_service.tools.memory_tool import archive_session_chunk, finalize_session_archive
from agent_service.tools.weather import get_weather

# FastAPI app
app = FastAPI(title="Arfy Agent Service")

# Build the graph once
graph = build_graph()

# Keep active session memory in RAM
session_store = SessionStore(max_turns=12)


@app.get("/health")
async def health():
    """
    Health check endpoint.
    """
    return {"status": "ok", "service": "agent"}


@app.post("/agent/ask", response_model=AgentResponse)
async def agent_ask(req: AgentRequest):
    """
    Main endpoint used by the desktop app.

    Flow:
    1. Save the user message into RAM
    2. Archive overflowed old messages into vector memory
    3. If a pending action exists and the user confirms/rejects it, handle that first
    4. Otherwise pass recent history + memories into the graph
    5. Save assistant reply into RAM
    6. Archive any new overflow after assistant reply
    """
    # Save the user message first
    overflowed_user = session_store.add_user_message(req.session_id, req.text)

    if overflowed_user:
        await run_in_threadpool(
            archive_session_chunk,
            session_id=req.session_id,
            messages=overflowed_user,
            session_started_at=session_store.get_started_at(req.session_id),
            chunk_reason="overflow_after_user_message",
        )

    # NEW:
    # Check whether this session already has a pending follow-up action
    pending_action = session_store.get_pending_action(req.session_id)

    # -------------------------
    # If user confirms a pending action, execute it directly
    # -------------------------
    if pending_action and is_confirmation_text(req.text):
        if pending_action.intent == "weather":
            location = pending_action.payload.get("location", "Malabe")

            tool_result = await run_in_threadpool(get_weather, location)

            response_text = await run_in_threadpool(
                build_final_response,
                user_text=req.text,
                intent="weather",
                tool_used="weather",
                tool_result=tool_result,
                action=None,
                memories=req.memories,
                history=session_store.get_history(req.session_id),
            )

            # Clear pending action after executing it
            session_store.clear_pending_action(req.session_id)

            overflowed_ai = session_store.add_ai_message(req.session_id, response_text)
            if overflowed_ai:
                await run_in_threadpool(
                    archive_session_chunk,
                    session_id=req.session_id,
                    messages=overflowed_ai,
                    session_started_at=session_store.get_started_at(req.session_id),
                    chunk_reason="overflow_after_assistant_message",
                )

            return AgentResponse(
                response=response_text,
                action=None,
                confidence=0.98,
                tool_used="weather",
                session_id=req.session_id,
            )

    # -------------------------
    # If user rejects a pending action, clear it
    # -------------------------
    if pending_action and is_rejection_text(req.text):
        session_store.clear_pending_action(req.session_id)

        response_text = "Okay, I won't do that."

        overflowed_ai = session_store.add_ai_message(req.session_id, response_text)
        if overflowed_ai:
            await run_in_threadpool(
                archive_session_chunk,
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

    # Build state with live short-term history included
    state = GraphState(
        session_id=req.session_id,
        user_text=req.text,
        memories=req.memories,
        history=session_store.get_history(req.session_id),
        pending_action=pending_action,
    )

    # Run LangGraph
    final_state = await run_in_threadpool(graph.invoke, state)

    if isinstance(final_state, dict):
        response_text = final_state.get("response", "Sorry, I couldn't process that.")
        action = final_state.get("action")
        confidence = final_state.get("confidence", 0.0)
        tool_used = final_state.get("tool_used")
    else:
        response_text = final_state.response or "Sorry, something went wrong."
        action = final_state.action
        confidence = final_state.confidence
        tool_used = final_state.tool_used

    # -------------------------
    # NEW:
    # Very simple starter logic:
    # If Arfy asks for weather confirmation about Balangoda,
    # store it as a pending action.
    #
    # You can later generalize this to extract any location.
    # -------------------------
    lower_response = response_text.lower()
    if (
        "do you want me to check" in lower_response
        and "weather" in lower_response
        and "balangoda" in lower_response
    ):
        session_store.set_pending_action(
            req.session_id,
            PendingAction(
                intent="weather",
                payload={"location": "Balangoda"},
            ),
        )

    # Save assistant response into RAM
    overflowed_ai = session_store.add_ai_message(req.session_id, response_text)

    if overflowed_ai:
        await run_in_threadpool(
            archive_session_chunk,
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


@app.post("/agent/reset")
async def reset_session(session_id: str):
    """
    Force-reset a session from RAM without archiving.
    Useful for debugging only.
    """
    session_store.reset(session_id)
    return {"status": "reset", "session_id": session_id}


@app.post("/agent/session/end")
async def end_session(session_id: str):
    """
    Finalize a session when Arfy goes to sleep.
    """
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
