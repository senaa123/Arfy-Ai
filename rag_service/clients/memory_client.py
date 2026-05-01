"""
Client for talking to memory_service.

Architectural rule:
rag_service does NOT own the vector DB or shared index.
It asks memory_service for indexed document chunks.
"""

from __future__ import annotations

from typing import Any

import requests

from rag_service.config import settings
from rag_service.schemas import RetrievedChunk


class MemoryClient:
    """
    Thin HTTP client for memory_service.

    Only this file should know the exact memory search endpoint path.
    If the memory endpoint changes later, update this file only.
    """

    def __init__(self) -> None:
        self.base_url = settings.MEMORY_SERVICE_BASE_URL
        self.search_chunks_url = f"{self.base_url}{settings.MEMORY_SEARCH_CHUNKS_PATH}"

    def search_chunks(
        self,
        *,
        query: str,
        document_ids: list[str] | None = None,
        top_k: int | None = None,
        session_id: str | None = None,
    ) -> list[RetrievedChunk]:
        """
        Ask memory_service for semantically relevant document chunks.

        Expected memory_service response shape:
        {
          "chunks": [
            {
              "chunk_id": "...",
              "document_id": "...",
              "text": "...",
              "score": 0.42,
              "source_ref": "...",
              "file_name": "...",
              "metadata": {...}
            }
          ]
        }

        If your actual endpoint returns a different raw shape,
        adapt it here only.
        """
        payload: dict[str, Any] = {
            "query": query,
            "document_ids": document_ids or [],
            "top_k": top_k or settings.DEFAULT_TOP_K,
            "session_id": session_id,
        }

        response = requests.post(
            self.search_chunks_url,
            json=payload,
            timeout=settings.REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()

        data = response.json()
        raw_chunks = data.get("chunks", [])

        normalized: list[RetrievedChunk] = []
        for item in raw_chunks:
            normalized.append(
                RetrievedChunk(
                    chunk_id=str(item.get("chunk_id", "")),
                    document_id=str(item.get("document_id", "")),
                    text=str(item.get("text", "")),
                    score=float(item.get("score", 0.0) or 0.0),
                    source_ref=item.get("source_ref"),
                    file_name=item.get("file_name"),
                    metadata=item.get("metadata", {}) or {},
                )
            )

        return normalized