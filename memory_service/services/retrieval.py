# memory_service/services/retrieval.py

from __future__ import annotations

from sqlalchemy.orm import Session

from memory_service.services.structured_store import (
    exact_document_lookup,
    exact_memory_lookup,
)
from memory_service.services.vector_store import semantic_retrieve


def _record_namespace(item: dict) -> str:
    """
    Group retrieval rows by their underlying structured owner.
    """
    memory_kind = item.get("memory_kind")
    source_layer = str(item.get("source_layer") or "")

    if memory_kind == "durable_memory" or source_layer == "structured_exact":
        return "memory_record"

    if memory_kind == "document_meta" or source_layer == "structured_document":
        return "document_record"

    return f"{memory_kind or 'unknown'}:{source_layer or 'unknown'}"


def _dedupe_memory_items(items: list[dict]) -> list[dict]:
    """
    Remove duplicate memory items while preserving order.

    Phase 4:
    - prefer public_id over local SQL record_id when available
    """
    seen = set()
    output = []

    for item in items:
        public_id = item.get("public_id")
        record_id = item.get("record_id")

        if public_id:
            signature = (
                _record_namespace(item),
                public_id,
                item.get("document_id"),
            )
        elif record_id is not None:
            signature = (
                _record_namespace(item),
                record_id,
                item.get("document_id"),
            )
        else:
            signature = (
                item.get("category"),
                item.get("key"),
                str(item.get("value")),
                item.get("session_id"),
                item.get("document_id"),
            )

        if signature in seen:
            continue

        seen.add(signature)
        output.append(item)

    return output


def build_memory_context(
    db: Session,
    *,
    query: str,
    exact_limit: int = 3,
    semantic_limit: int = 5,
) -> dict:
    """
    Build a full memory context packet for the agent.
    """
    if not str(query).strip():
        return {
            "query": query,
            "exact": [],
            "documents": [],
            "semantic": [],
            "merged": [],
        }

    exact_memory_items = exact_memory_lookup(
        db=db,
        query=query,
        limit=exact_limit,
    )

    exact_document_items = exact_document_lookup(
        db=db,
        query=query,
        limit=exact_limit,
    )

    semantic_items = semantic_retrieve(
        query=query,
        limit=semantic_limit,
    )

    merged_items = _dedupe_memory_items(
        exact_memory_items + exact_document_items + semantic_items
    )

    return {
        "query": query,
        "exact": exact_memory_items,
        "documents": exact_document_items,
        "semantic": semantic_items,
        "merged": merged_items,
    }