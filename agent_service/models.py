# agent_service/models.py

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class MemoryItem(BaseModel):
    """
    A memory item returned by memory_service and passed into the agent.
    """

    category: str
    key: str
    value: Any

    score: Optional[float] = None

    record_id: Optional[int] = None
    public_id: Optional[str] = None
    session_id: Optional[str] = None
    document_id: Optional[str] = None

    source_ref: Optional[str] = None
    content_hash: Optional[str] = None

    created_at: Optional[str] = None

    memory_kind: Optional[str] = None
    chunk_reason: Optional[str] = None

    source: Optional[str] = None
    source_layer: Optional[str] = None

    # Phase 3C additions for document chunk retrieval
    file_name: Optional[str] = None
    extension: Optional[str] = None
    chunk_index: Optional[int] = None
    start_char: Optional[int] = None
    end_char: Optional[int] = None

class SessionMessage(BaseModel):
    """
    A single short-term chat message stored for the active session.
    """

    role: Literal["user", "assistant"]
    content: str
    timestamp: str


class PendingAction(BaseModel):
    """
    A follow-up tool/action request waiting for user confirmation.
    """

    intent: str
    tool_name: Optional[str] = None
    payload: dict[str, Any] = Field(default_factory=dict)


class AgentRequest(BaseModel):
    """
    Input payload sent from desktop app to agent service.
    """

    text: str
    session_id: str = "default_session"

    # Deprecated in active runtime flow.
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

    Phase 3B change:
    - memory_context carries richer exact/semantic/document memory breakdown
    - memories keeps the merged flat list for backward compatibility
    """

    session_id: str
    user_text: str

    # Backward-compatible merged list
    memories: List[MemoryItem] = Field(default_factory=list)

    # New richer context packet from memory_service
    memory_context: Dict[str, Any] = Field(default_factory=dict)

    history: List[SessionMessage] = Field(default_factory=list)

    pending_action: Optional[PendingAction] = None

    intent: Optional[str] = None
    extracted_data: Dict[str, Any] = Field(default_factory=dict)
    tool_name: Optional[str] = None

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
        "document_upload",
        "document_qa", # Rag
        "spotify_play_song",
        "spotify_play_playlist",
        "unknown",
    ]
    confidence: float = 0.0
    extracted_data: Dict[str, Any] = Field(default_factory=dict)
    action: Optional[AgentAction] = None
    tool_name: Optional[str] = None


class AgentDocumentIngestRequest(BaseModel):
    """
    Manual request to test document ingestion through the agent.
    """
    file_path: str
    session_id: str = "default_session"

    enable_ocr: bool = True
    persist: bool = True
    pdf_ocr_min_chars: int = 30

    chunk_size: int = 1200
    chunk_overlap: int = 200
    index_chunks_to_vector: bool = True


class AgentDocumentIngestResponse(BaseModel):
    """
    Response returned by agent after forwarding to document_service.
    """
    success: bool
    message: str
    tool_used: str = "document_ingest"

    document_id: Optional[str] = None
    source_ref: Optional[str] = None
    content_hash: Optional[str] = None
    local_file_path: Optional[str] = None
    file_name: Optional[str] = None
    extension: Optional[str] = None

    text_length: int = 0
    chunk_count: int = 0
    ocr_used: bool = False

    preview: Optional[str] = None
    persisted_dir: Optional[str] = None

    # New in 3B
    memory_registered: bool = False
    memory_register_message: Optional[str] = None

    # New in 3C
    chunks_registered: int = 0
    chunks_indexed: int = 0
    chunk_register_message: Optional[str] = None

    metadata: Dict[str, Any] = Field(default_factory=dict)
