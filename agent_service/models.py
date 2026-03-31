from typing import Any, Dict, List, Optional, Literal
from pydantic  import BaseModel, Field

#
class MemoryItem(BaseModel):
    category: str
    key: str
    value: Any
    score: Optional[float] = None

#Data desktop sends to agent
class AgentRequestt(BaseModel):
    text: str
    session_id: str = "default_session"
    memories: List[MemoryItem] = Field(default_factory=list)

#action agent want to execute in app
class AgenticAction(BaseModel):
    type: str
    payload: dict[str, Any] = Field(default_factory=dict)

#final response sent back to the desktop app
class AgentResponse(BaseModel):
    response: str
    action: Optional[AgenticAction] = None
    confidence: float = 0.8

#Internal routing result
class RouteDecision(BaseModel):
    intent: Literal[
        "chat",
        "open_app",
        "close_app",
        "weather",
        "search",
        "remember",
        "spotify_play",
        "unknown"
    ]
    confidence: float = 0.8
    action: Optional[AgenticAction] = None
    tool_name: Optional[str] =None 
    extracted_data: Dict[str, Any] = Field(default_factory=dict)
