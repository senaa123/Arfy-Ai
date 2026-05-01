"""
Initial retrieval logic for rag_service.

This layer is responsible only for fetching candidate chunks from memory_service.
It does not judge or answer yet.
"""

from __future__ import annotations

from rag_service.clients import MemoryClient
from rag_service.config import settings
from rag_service.schemas import RetrievedChunk


def retrieve_candidate_chunks(
    *,
    question: str,
    document_ids: list[str] | None = None,
    top_k: int | None = None,
    session_id: str | None = None,
) -> list[RetrievedChunk]:
    """
    Retrieve initial candidate chunks from memory_service.

    Phase 1 keeps this very simple:
    - one semantic retrieval pass
    - no repair loop yet
    """
    client = MemoryClient()
    return client.search_chunks(
        query=question,
        document_ids=document_ids or [],
        top_k=top_k or settings.DEFAULT_TOP_K,
        session_id=session_id,
    )