# memory_service/schemas.py

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class MemorySaveRequest(BaseModel):
    """
    Save one durable memory record.
    """

    category: str
    key: str
    value: Any

    session_id: Optional[str] = None
    document_id: Optional[str] = None
    source: str = "agent"

    write_to_vector: bool = True


class MemoryRetrieveRequest(BaseModel):
    """
    Backward-compatible simple retrieval request.
    """
    query: str
    limit: int = 5


class MemoryContextRequest(BaseModel):
    """
    Richer retrieval request used by the agent.
    """
    query: str
    exact_limit: int = 3
    semantic_limit: int = 5


class ActionLogRequest(BaseModel):
    """
    Structured action log payload.
    """
    action: str
    type: str
    success: bool = True

    session_id: Optional[str] = None
    payload_json: Optional[str] = None


class DocumentMetaSaveRequest(BaseModel):
    """
    Register document metadata for one document.

    Phase 4:
    - source_ref and content_hash are portable/shared metadata
    - local_file_path is local-only metadata
    """
    document_id: str
    source_ref: str
    content_hash: str

    file_name: str
    local_file_path: Optional[str] = None
    extension: str

    text_length: int = 0
    chunk_count: int = 0
    ocr_used: bool = False


class DocumentChunkSaveItem(BaseModel):
    """
    One chunk record sent from document_service to memory_service.
    """
    chunk_id: str
    chunk_index: int
    text: str
    start_char: int
    end_char: int
    pages: List[int] = Field(default_factory=list)


class DocumentChunkBatchRegisterRequest(BaseModel):
    """
    Register a batch of chunks for one document.
    """

    document_id: str
    file_name: str
    extension: str
    index_to_vector: bool = True

    chunks: List[DocumentChunkSaveItem] = Field(default_factory=list)


class DocumentChunkBatchRegisterResponse(BaseModel):
    """
    Chunk registration result returned to document_service.
    """
    success: bool
    message: str

    document_id: Optional[str] = None
    registered_count: int = 0
    indexed_count: int = 0
    failed_count: int = 0


class MemoryItemResponse(BaseModel):
    """
    One memory item returned to the agent.
    """
    category: str
    key: str
    value: Any

    score: Optional[float] = None

    record_id: Optional[int] = None
    public_id: Optional[str] = None

    session_id: Optional[str] = None
    document_id: Optional[str] = None

    created_at: Optional[str] = None

    memory_kind: Optional[str] = None
    chunk_reason: Optional[str] = None

    source: Optional[str] = None
    source_layer: Optional[str] = None

    file_name: Optional[str] = None
    source_ref: Optional[str] = None
    content_hash: Optional[str] = None
    extension: Optional[str] = None
    chunk_index: Optional[int] = None
    start_char: Optional[int] = None
    end_char: Optional[int] = None


class ActionHistoryItem(BaseModel):
    action: str
    type: str
    success: bool
    created_at: str


class ChatMessage(BaseModel):
    """
    One archived session message.
    """
    role: Literal["user", "assistant"]
    content: str
    timestamp: str


class SessionArchiveChunkRequest(BaseModel):
    """
    Overflow archive request for old short-term RAM messages.
    """
    session_id: str
    messages: List[ChatMessage] = Field(default_factory=list)
    session_started_at: Optional[str] = None
    chunk_reason: str = "overflow"


class SessionFinalizeRequest(BaseModel):
    """
    Final archive request when a session ends.
    """
    session_id: str
    messages: List[ChatMessage] = Field(default_factory=list)
    session_started_at: Optional[str] = None
    session_ended_at: Optional[str] = None

#Rag_service
class DocumentChunkSearchRequest(BaseModel):
    """
    Request model for RAG-oriented document chunk search.

    This is intentionally separate from the richer /memory/context retrieval path:
    - RAG wants only document chunks
    - optional document_ids lets caller narrow retrieval to known documents
    - session_id is accepted for future narrowing/debugging even if unused today
    """

    query: str
    document_ids: List[str] = Field(default_factory=list)
    top_k: int = 8
    session_id: Optional[str] = None


class DocumentChunkSearchItem(BaseModel):
    """
    One normalized chunk returned to rag_service.
    """

    chunk_id: str
    document_id: str
    text: str
    score: float = 0.0
    source_ref: Optional[str] = None
    file_name: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DocumentChunkSearchResponse(BaseModel):
    """
    Response model for RAG chunk search.
    """

    chunks: List[DocumentChunkSearchItem] = Field(default_factory=list)
