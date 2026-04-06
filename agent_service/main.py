from fastapi import FastAPI
from agent_service.models import AgentRequest, AgentResponse, GraphState
from agent_service.graph import build_graph
from agent_service.session import SessionStore


# Create FastAPI app
app = FastAPI(title="Arfy Agent Service")
# Build the agent graph once
graph = build_graph()
session_store = SessionStore()#create session


@app.get("/health")
async def health():
    """
    Simple health endpoint to check if service is running
    """
    return {"status": "ok", "service": "agent"}


@app.post("/agent/ask", response_model=AgentResponse)
async def agent_ask(req: AgentRequest):
    """
    Main endpoint used by desktop app.

    Flow:
    1. Save the user message into short-term session history
    2. Create the initial GraphState
    3. Run the LangGraph workflow
    4. Extract final response values
    5. Save assistant reply into session history
    6. Return a structured API response
    """
    #Store the user message in the session history
    session_store.add_user_message(req.session_id, req.text)

    # Create the initial graph state that will be passed into LangGraph
    state = GraphState(
        session_id=req.session_id,
        user_text=req.text,
        memories=req.memories
    )

    # run the langgraph workflow
    final_state = graph.invoke(state)
    # for dict return
    if isinstance(final_state, dict):
        response_text = final_state.get("response", "Sorry, I couldn't process that.")
        action = final_state.get("action")
        confidence = final_state.get("confidence", 0.0)
        tool_used = final_state.get("tool_used")
    
    # for graphstate object  return
    else:
        response_text = final_state.response or "Sorry, something went wrong."
        action = final_state.action
        confidence = final_state.confidence
        tool_used = final_state.tool_used
    
    # store response to session history
    session_store.add_ai_message(req.session_id, response_text)

    #return the final structures API respose
    return AgentResponse(
        response=response_text,
        action=action,
        confidence=confidence,
        tool_used=tool_used,
        session_id=req.session_id
    )



@app.post("/agent/reset")
async def reset_session(session_id: str):
    """
    Reset a specific session.

    This clears stored short-term conversation history
    for the given session_id.
    """
    session_store.reset(session_id)
    return {"status": "reset", "session_id": session_id}