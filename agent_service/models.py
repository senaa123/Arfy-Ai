from typing import Any, Dict, List, Optional, Literal
from pydantic import BaseModel, Field


class MemoryItem(BaseModel):
    """
    A memory item returned by memory_service and passed into the agent.
    """
    category: str
    key: str
    value: Any
    score: Optional[float] = None
    session_id: Optional[str] = None
    created_at: Optional[str] = None
    memory_kind: Optional[str] = None
    chunk_reason: Optional[str] = None


class SessionMessage(BaseModel):
    """
    A single short-term chat message stored for the active session.
    """
    role: Literal["user", "assistant"]
    content: str
    timestamp: str


class PendingAction(BaseModel):
    """
    A follow-up action waiting for user confirmation.

    Example:
    Arfy asks: "Do you want me to check the weather in Balangoda?"
    We store:
        intent = "weather"
        payload = {"location": "Balangoda"}
    """
    intent: str
    payload: dict[str, Any] = Field(default_factory=dict)


class AgentRequest(BaseModel):
    """
    Input payload sent from desktop app to agent service.
    """
    text: str
    session_id: str = "default_session"
    memories: List[MemoryItem] = Field(default_factory=list)


class AgentAction(BaseModel):
    """
    Action the desktop app may execute.
    """
    type: str
    payload: dict[str, Any] = Field(default_factory=dict)


class AgentResponse(BaseModel):
    """
    Final structured response returned to desktop app.
    """
    response: str
    action: Optional[AgentAction] = None
    confidence: float = 0.0
    tool_used: Optional[str] = None
    session_id: str


class GraphState(BaseModel):
    """
    Internal state passed through LangGraph.
    """
    session_id: str
    user_text: str
    memories: List[MemoryItem] = Field(default_factory=list)
    history: List[SessionMessage] = Field(default_factory=list)

    # NEW:
    # Stores a pending follow-up action for confirmation handling.
    pending_action: Optional[PendingAction] = None

    intent: Optional[str] = None
    extracted_data: Dict[str, Any] = Field(default_factory=dict)
    tool_used: Optional[str] = None
    tool_result: Optional[Dict[str, Any]] = None
    action: Optional[AgentAction] = None
    response: Optional[str] = None
    confidence: float = 0.0


class RouteDecision(BaseModel):
    """
    Router output produced by the LLM router or fallback parser.
    """
    intent: Literal[
        "chat",
        "open_app",
        "close_app",
        "weather",
        "search",
        "remember",
        "spotify_play_song",
        "spotify_play_playlist",
        "unknown",
    ]
    confidence: float = 0.0
    extracted_data: Dict[str, Any] = Field(default_factory=dict)
    action: Optional[AgentAction] = None
    tool_name: Optional[str] = None