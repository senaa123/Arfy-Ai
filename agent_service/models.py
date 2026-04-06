from typing import Any, Dict, List, Optional, Literal
from pydantic  import BaseModel, Field

#A single memory item passed from desktop or returned by memory service
class MemoryItem(BaseModel):
    category: str
    key: str
    value: Any
    score: Optional[float] = None

#Data desktop sends to agent
class AgentRequest(BaseModel):
    text: str
    session_id: str = "default_session"
    memories: List[MemoryItem] = Field(default_factory=list)

#action agent want to execute in app
class AgentAction(BaseModel):
    type: str
    payload: dict[str, Any] = Field(default_factory=dict)

#final response sent back to the desktop app
class AgentResponse(BaseModel):
    response: str
    action: Optional[AgentAction] = None
    confidence: float = 0.0
    tool_used: Optional[str] = None
    session_id: str

# Internal graph state used inside LangGraph flow
class GraphState(BaseModel):
    session_id: str
    user_text: str
    memories: List[MemoryItem] = Field(default_factory=list)

    # Values filled during graph execution
    intent: Optional[str] = None
    extracted_data: Dict[str, Any] = Field(default_factory=dict)
    tool_used: Optional[str] = None
    tool_result: Optional[Dict[str, Any]] = None
    action: Optional[AgentAction] = None
    response: Optional[str] = None
    confidence: float = 0.0

#Structured router output from LLM
class RouteDecision(BaseModel):
    intent: Literal[
        "chat",
        "open_app",
        "close_app",
        "weather",
        "search",
        "remember",
        "spotify_play_song",
        "spotify_play_playlist",
        "unknown"
    ]
    confidence: float = 0.0
    extracted_data: Dict[str, Any] = Field(default_factory=dict)
    action: Optional[AgentAction] = None
    tool_name: Optional[str] = None
