# memory_service/routes/rag.py

from fastapi import APIRouter

from memory_service.schemas import (
    DocumentChunkSearchRequest,
    DocumentChunkSearchResponse,
)
from memory_service.services.vector_store import search_document_chunks

router = APIRouter(tags=["rag"])


@router.post("/memory/search/chunks", response_model=DocumentChunkSearchResponse)
async def search_chunks_for_rag(req: DocumentChunkSearchRequest):
    """
    Search only document chunks for rag_service.

    Why this route exists separately from /memory/context:
    - /memory/context is for broad agent memory grounding
    - RAG needs a narrower, document-chunk-only retrieval API
    - keeping it in routes/rag.py preserves a clean responsibility split
    """
    chunks = search_document_chunks(
        query=req.query,
        top_k=req.top_k,
        document_ids=req.document_ids,
        session_id=req.session_id,
    )
    return DocumentChunkSearchResponse(chunks=chunks)