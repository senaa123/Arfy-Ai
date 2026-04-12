from typing import Any, List, Literal, Optional

from pydantic import BaseModel, Field


class MemorySaveRequest(BaseModel):
    category: str
    key: str
    value: Any


class MemoryRetrieveRequest(BaseModel):
    query: str
    limit: int = 5


class ActionLogRequest(BaseModel):
    action: str
    type: str
    success: bool = True


class MemoryItemResponse(BaseModel):
    category: str
    key: str
    value: Any
    score: Optional[float] = None
    session_id: Optional[str] = None
    created_at: Optional[str] = None
    memory_kind: Optional[str] = None
    chunk_reason: Optional[str] = None


class ActionHistoryItem(BaseModel):
    action: str
    type: str
    success: bool
    timestamp: str


class ChatMessage(BaseModel):
    """
    One archived message from the live session.
    """
    role: Literal["user", "assistant"]
    content: str
    timestamp: str


class SessionArchiveChunkRequest(BaseModel):
    """
    Request used when old in-memory messages overflow and need archiving.
    """
    session_id: str
    messages: List[ChatMessage] = Field(default_factory=list)
    session_started_at: Optional[str] = None
    chunk_reason: str = "overflow"


class SessionFinalizeRequest(BaseModel):
    """
    Request used when the whole active session ends.
    """
    session_id: str
    messages: List[ChatMessage] = Field(default_factory=list)
    session_started_at: Optional[str] = None
    session_ended_at: Optional[str] = None