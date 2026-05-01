# document_service/schemas.py

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class DocumentIngestRequest(BaseModel):
    """
    Request to ingest one local file.

    Phase 3C:
    - index_chunks_to_vector controls whether chunk vectors are created

    Phase 4:
    - request is still local-file based, because desktop/local workflows
      are still the active runtime path
    """
    file_path: str
    persist: bool = True

    enable_ocr: bool = True
    pdf_ocr_min_chars: int = 30

    chunk_size: int = 1200
    chunk_overlap: int = 200

    index_chunks_to_vector: bool = True


class DocumentChunk(BaseModel):
    """
    One normalized chunk of document text.
    """
    chunk_id: str
    chunk_index: int
    text: str
    start_char: int
    end_char: int
    pages: list[int] = Field(default_factory=list)


class ExtractedDocument(BaseModel):
    """
    Internal normalized document representation.

    Phase 4 separation:
    - document_id / source_ref / content_hash are portable
    - local_file_path is local-only metadata
    """

    document_id: str
    source_ref: str
    content_hash: str

    local_file_path: str
    file_name: str
    extension: str

    text: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    ocr_used: bool = False


class DocumentIngestResponse(BaseModel):
    """
    Public response from document_service.

    Phase 3B:
    - metadata registration state

    Phase 3C:
    - chunk registration/indexing state

    Phase 4:
    - expose portable document identity fields
    """
    success: bool
    message: str

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

    memory_registered: bool = False
    memory_register_message: Optional[str] = None

    chunks_registered: int = 0
    chunks_indexed: int = 0
    chunk_register_message: Optional[str] = None

    metadata: Dict[str, Any] = Field(default_factory=dict)
