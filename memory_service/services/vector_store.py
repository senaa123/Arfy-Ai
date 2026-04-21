# memory_service/services/vector_store.py

from __future__ import annotations

from typing import Iterable, List

from memory_service.qdrant_store import (
    DOCUMENT_COLLECTION,
    SESSION_COLLECTION,
    STRUCTURED_COLLECTION,
    generate_qdrant_id,
    now_iso,
    query_collection,
    upsert_vector_point,
)
from memory_service.services.memory_policy import build_structured_vector_text


def save_structured_memory_vector(
    *,
    category: str,
    key: str,
    value: str,
    memory_id: str,
    record_id: int,
    session_id: str | None = None,
    document_id: str | None = None,
    source: str = "agent",
    point_id: str | None = None,
) -> str:
    """
    Save one durable structured fact into vector memory.

    Phase 4:
    - keep record_id for local debugging
    - also store public_id for portable linking
    """
    point_id = point_id or generate_qdrant_id()

    text_for_embedding = build_structured_vector_text(category, key, value)

    payload = {
        "category": category,
        "key": key,
        "value": value,
        "created_at": now_iso(),
        "public_id": memory_id,
        "session_id": session_id,
        "document_id": document_id,
        "memory_kind": "durable_memory",
        "chunk_reason": None,
        "summary": None,
        "transcript": None,
        "linked_record_id": record_id,
        "source": source,
        "file_name": None,
        "source_ref": None,
        "content_hash": None,
        "extension": None,
        "chunk_index": None,
        "start_char": None,
        "end_char": None,
    }

    return upsert_vector_point(
        collection_name=STRUCTURED_COLLECTION,
        point_id=point_id,
        text_for_embedding=text_for_embedding,
        payload=payload,
    )


def save_session_archive_vector(
    *,
    session_id: str,
    transcript: str,
    summary: str,
    linked_record_id: int,
    session_started_at: str | None = None,
    session_ended_at: str | None = None,
    chunk_reason: str = "overflow",
    point_id: str | None = None,
) -> str:
    """
    Save one archived session chunk into vector memory.

    session_id already acts as the public session identity.
    """
    point_id = point_id or generate_qdrant_id()

    text_for_embedding = f"{summary}\n\n{transcript}".strip()

    payload = {
        "category": "session_history",
        "key": session_id,
        "value": summary,
        "created_at": now_iso(),
        "public_id": session_id,
        "session_id": session_id,
        "document_id": None,
        "memory_kind": "session_archive",
        "chunk_reason": chunk_reason,
        "summary": summary,
        "transcript": transcript,
        "session_started_at": session_started_at,
        "session_ended_at": session_ended_at,
        "linked_record_id": linked_record_id,
        "source": "system",
        "file_name": None,
        "source_ref": None,
        "content_hash": None,
        "extension": None,
        "chunk_index": None,
        "start_char": None,
        "end_char": None,
    }

    return upsert_vector_point(
        collection_name=SESSION_COLLECTION,
        point_id=point_id,
        text_for_embedding=text_for_embedding,
        payload=payload,
    )


def save_session_summary_vector(
    *,
    session_id: str,
    summary: str,
    linked_record_id: int,
    session_started_at: str | None = None,
    session_ended_at: str | None = None,
    point_id: str | None = None,
) -> str:
    """
    Save one final session summary into vector memory.
    """
    point_id = point_id or generate_qdrant_id()

    payload = {
        "category": "session_summary",
        "key": session_id,
        "value": summary,
        "created_at": now_iso(),
        "public_id": session_id,
        "session_id": session_id,
        "document_id": None,
        "memory_kind": "session_summary",
        "chunk_reason": "session_end",
        "summary": summary,
        "transcript": None,
        "session_started_at": session_started_at,
        "session_ended_at": session_ended_at,
        "linked_record_id": linked_record_id,
        "source": "system",
        "file_name": None,
        "source_ref": None,
        "content_hash": None,
        "extension": None,
        "chunk_index": None,
        "start_char": None,
        "end_char": None,
    }

    return upsert_vector_point(
        collection_name=SESSION_COLLECTION,
        point_id=point_id,
        text_for_embedding=summary,
        payload=payload,
    )


def save_document_chunk_vector(
    *,
    document_id: str,
    chunk_id: str,
    chunk_record_id: int,
    file_name: str,
    extension: str,
    chunk_index: int,
    text: str,
    start_char: int,
    end_char: int,
    point_id: str | None = None,
) -> str:
    """
    Save one document chunk into vector memory.

    Phase 4:
    - chunk_id is the portable chunk identity
    - document_id remains the portable parent identity
    """
    point_id = point_id or generate_qdrant_id()

    payload = {
        "category": "document_chunk",
        "key": f"{file_name}::chunk_{chunk_index}",
        "value": text,
        "created_at": now_iso(),
        "public_id": chunk_id,
        "session_id": None,
        "document_id": document_id,
        "memory_kind": "document_chunk",
        "chunk_reason": None,
        "summary": None,
        "transcript": None,
        "linked_record_id": chunk_record_id,
        "source": "document_service",
        "file_name": file_name,
        "source_ref": file_name,
        "content_hash": None,
        "extension": extension,
        "chunk_index": chunk_index,
        "start_char": start_char,
        "end_char": end_char,
    }

    return upsert_vector_point(
        collection_name=DOCUMENT_COLLECTION,
        point_id=point_id,
        text_for_embedding=text,
        payload=payload,
    )


def semantic_retrieve(
    *,
    query: str,
    limit: int = 5,
    collections: Iterable[str] | None = None,
) -> List[dict]:
    """
    Search multiple vector collections and return one merged ranked list.
    """
    collections = list(
        collections or [STRUCTURED_COLLECTION, SESSION_COLLECTION, DOCUMENT_COLLECTION]
    )

    merged = []
    for collection_name in collections:
        try:
            merged.extend(query_collection(query, collection_name, limit=limit))
        except Exception:
            continue

    merged.sort(key=lambda item: item.get("score", 0.0), reverse=True)

    normalized = []
    for item in merged[:limit]:
        normalized.append(
            {
                "category": item.get("category"),
                "key": item.get("key"),
                "value": item.get("summary") or item.get("value"),
                "score": item.get("score"),
                "record_id": item.get("linked_record_id"),
                "public_id": item.get("public_id"),
                "session_id": item.get("session_id"),
                "document_id": item.get("document_id"),
                "created_at": item.get("created_at"),
                "memory_kind": item.get("memory_kind"),
                "chunk_reason": item.get("chunk_reason"),
                "source": item.get("source"),
                "source_layer": f"vector_semantic:{item.get('collection_name')}",
                "file_name": item.get("file_name"),
                "source_ref": item.get("source_ref"),
                "content_hash": item.get("content_hash"),
                "extension": item.get("extension"),
                "chunk_index": item.get("chunk_index"),
                "start_char": item.get("start_char"),
                "end_char": item.get("end_char"),
            }
        )

    return normalized