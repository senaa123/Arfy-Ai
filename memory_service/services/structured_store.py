# memory_service/services/structured_store.py

from __future__ import annotations

from typing import List

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from memory_service.models import (
    ActionRecord,
    DocumentChunkRecord,
    DocumentRecord,
    MemoryRecord,
    SessionRecord,
)


KNOWN_EXACT_KEY_HINTS = {
    "favorite app": "favorite_app",
    "favorite song": "favorite_song",
    "favorite artist": "favorite_artist",
    "usual location": "usual_location",
    "preferred response style": "preferred_response_style",
}


def save_memory_record(
    db: Session,
    *,
    category: str,
    key: str,
    value: str,
    session_id: str | None = None,
    document_id: str | None = None,
    source: str = "agent",
) -> MemoryRecord:
    """
    Save or update one structured memory row.
    """
    existing = (
        db.query(MemoryRecord)
        .filter(
            MemoryRecord.category == category,
            MemoryRecord.key == key,
            MemoryRecord.session_id == session_id,
            MemoryRecord.document_id == document_id,
        )
        .order_by(MemoryRecord.id.desc())
        .first()
    )

    if existing:
        existing.value = str(value)
        existing.source = source
        db.commit()
        db.refresh(existing)
        return existing

    record = MemoryRecord(
        category=category,
        key=key,
        value=str(value),
        session_id=session_id,
        document_id=document_id,
        source=source,
    )

    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def list_all_memories(db: Session) -> list[MemoryRecord]:
    """
    Return all structured memory rows.
    """
    return db.query(MemoryRecord).order_by(MemoryRecord.created_at.desc()).all()


def log_action_record(
    db: Session,
    *,
    action: str,
    action_type: str,
    success: bool = True,
    session_id: str | None = None,
    payload_json: str | None = None,
) -> ActionRecord:
    """
    Save one action execution log.
    """
    record = ActionRecord(
        session_id=session_id,
        action=action,
        type=action_type,
        payload_json=payload_json,
        success=success,
    )

    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_recent_action_history(db: Session, limit: int = 10) -> list[ActionRecord]:
    """
    Return recent action logs ordered by newest first.
    """
    return (
        db.query(ActionRecord)
        .order_by(ActionRecord.created_at.desc())
        .limit(limit)
        .all()
    )


def upsert_session_record(
    db: Session,
    *,
    session_id: str,
    started_at: str | None = None,
    ended_at: str | None = None,
    summary: str | None = None,
    message_count: int = 0,
) -> SessionRecord:
    """
    Create or update one session metadata row.
    """
    record = (
        db.query(SessionRecord)
        .filter(SessionRecord.session_id == session_id)
        .first()
    )

    if record is None:
        record = SessionRecord(
            session_id=session_id,
            started_at=started_at,
            ended_at=ended_at,
            summary=summary,
            message_count=message_count,
        )
        db.add(record)
    else:
        if started_at is not None:
            record.started_at = started_at
        if ended_at is not None:
            record.ended_at = ended_at
        if summary is not None:
            record.summary = summary

        record.message_count = message_count

    db.commit()
    db.refresh(record)
    return record


def upsert_document_record(
    db: Session,
    *,
    document_id: str,
    source_ref: str,
    content_hash: str,
    file_name: str,
    local_file_path: str | None,
    extension: str,
    text_length: int,
    chunk_count: int,
    ocr_used: bool,
) -> DocumentRecord:
    """
    Create or update one document metadata row.

    Phase 4:
    - document_id is portable/shared
    - source_ref is sync-safe metadata
    - local_file_path is local-only metadata
    - content_hash supports future sync/dedupe checks
    """
    record = (
        db.query(DocumentRecord)
        .filter(DocumentRecord.document_id == document_id)
        .first()
    )

    if record is None:
        record = DocumentRecord(
            document_id=document_id,
            source_ref=source_ref,
            content_hash=content_hash,
            file_name=file_name,
            local_file_path=local_file_path,
            extension=extension,
            text_length=text_length,
            chunk_count=chunk_count,
            ocr_used=ocr_used,
        )
        db.add(record)
    else:
        record.source_ref = source_ref
        record.content_hash = content_hash
        record.file_name = file_name
        record.local_file_path = local_file_path
        record.extension = extension
        record.text_length = text_length
        record.chunk_count = chunk_count
        record.ocr_used = ocr_used

    db.commit()
    db.refresh(record)
    return record


def get_document_record_by_document_id(
    db: Session,
    *,
    document_id: str,
) -> DocumentRecord | None:
    """
    Return one document metadata row by its stable document_id.
    """
    return (
        db.query(DocumentRecord)
        .filter(DocumentRecord.document_id == document_id)
        .first()
    )


def upsert_document_chunk_record(
    db: Session,
    *,
    chunk_id: str,
    document_id: str,
    chunk_index: int,
    text: str,
    start_char: int,
    end_char: int,
    indexed_to_vector: bool = False,
) -> DocumentChunkRecord:
    """
    Create or update one document chunk row.

    Why this exists:
    - chunk rows become first-class structured records
    - later RAG can link directly to them
    """
    record = (
        db.query(DocumentChunkRecord)
        .filter(DocumentChunkRecord.chunk_id == chunk_id)
        .first()
    )

    if record is None:
        record = DocumentChunkRecord(
            chunk_id=chunk_id,
            document_id=document_id,
            chunk_index=chunk_index,
            text=text,
            start_char=start_char,
            end_char=end_char,
            indexed_to_vector=indexed_to_vector,
        )
        db.add(record)
    else:
        record.document_id = document_id
        record.chunk_index = chunk_index
        record.text = text
        record.start_char = start_char
        record.end_char = end_char

        # Only ever move forward here.
        # If the caller indexed it, mark it true.
        if indexed_to_vector:
            record.indexed_to_vector = True

    db.commit()
    db.refresh(record)
    return record


def list_document_chunk_records(
    db: Session,
    *,
    document_id: str,
    limit: int = 50,
) -> list[DocumentChunkRecord]:
    """
    Return chunk rows for one document in natural chunk order.
    """
    return (
        db.query(DocumentChunkRecord)
        .filter(DocumentChunkRecord.document_id == document_id)
        .order_by(DocumentChunkRecord.chunk_index.asc())
        .limit(limit)
        .all()
    )


def _serialize_memory_record(record: MemoryRecord) -> dict:
    """
    Convert MemoryRecord into the shared retrieval shape.

    Phase 4:
    - expose public_id in addition to local record_id
    """
    return {
        "category": record.category,
        "key": record.key,
        "value": record.value,
        "score": 1.0,
        "record_id": record.id,
        "public_id": record.memory_id,
        "session_id": record.session_id,
        "document_id": record.document_id,
        "created_at": record.created_at.isoformat() if record.created_at else None,
        "memory_kind": "durable_memory",
        "chunk_reason": None,
        "source": record.source,
        "source_layer": "structured_exact",
        "file_name": None,
        "source_ref": None,
        "content_hash": None,
        "extension": None,
        "chunk_index": None,
        "start_char": None,
        "end_char": None,
    }


def _serialize_document_record(record: DocumentRecord) -> dict:
    """
    Convert DocumentRecord into the shared retrieval shape.
    """
    document_summary = (
        f"Document '{record.file_name}' ({record.extension}) "
        f"has {record.chunk_count} chunks, text_length={record.text_length}, "
        f"ocr_used={record.ocr_used}."
    )

    return {
        "category": "document_meta",
        "key": record.file_name,
        "value": document_summary,
        "score": 1.0,
        "record_id": record.id,
        "public_id": record.document_id,
        "session_id": None,
        "document_id": record.document_id,
        "created_at": record.created_at.isoformat() if record.created_at else None,
        "memory_kind": "document_meta",
        "chunk_reason": None,
        "source": "document_service",
        "source_layer": "structured_document",
        "file_name": record.file_name,
        "source_ref": record.source_ref,
        "content_hash": record.content_hash,
        "extension": record.extension,
        "chunk_index": None,
        "start_char": None,
        "end_char": None,
    }


def exact_memory_lookup(
    db: Session,
    *,
    query: str,
    limit: int = 3,
) -> List[dict]:
    """
    Try to answer exact-memory questions using SQLite before semantic search.
    """
    lower_query = query.strip().lower()

    for phrase, exact_key in KNOWN_EXACT_KEY_HINTS.items():
        if phrase in lower_query:
            rows = (
                db.query(MemoryRecord)
                .filter(func.lower(MemoryRecord.key) == exact_key.lower())
                .order_by(MemoryRecord.updated_at.desc(), MemoryRecord.id.desc())
                .limit(limit)
                .all()
            )
            return [_serialize_memory_record(row) for row in rows]

    rows = (
        db.query(MemoryRecord)
        .filter(
            or_(
                func.lower(MemoryRecord.key).contains(lower_query),
                func.lower(MemoryRecord.value).contains(lower_query),
                func.lower(MemoryRecord.category).contains(lower_query),
            )
        )
        .order_by(MemoryRecord.updated_at.desc(), MemoryRecord.id.desc())
        .limit(limit)
        .all()
    )

    if rows:
        return [_serialize_memory_record(row) for row in rows]

    tokens = [token for token in lower_query.split() if len(token) >= 3]
    if not tokens:
        return []

    token_filters = []
    for token in tokens:
        token_filters.append(func.lower(MemoryRecord.key).contains(token))
        token_filters.append(func.lower(MemoryRecord.value).contains(token))
        token_filters.append(func.lower(MemoryRecord.category).contains(token))

    rows = (
        db.query(MemoryRecord)
        .filter(or_(*token_filters))
        .order_by(MemoryRecord.updated_at.desc(), MemoryRecord.id.desc())
        .limit(limit)
        .all()
    )

    return [_serialize_memory_record(row) for row in rows]


def exact_document_lookup(
    db: Session,
    *,
    query: str,
    limit: int = 3,
) -> List[dict]:
    """
    Exact lookup for document metadata.

    Phase 4:
    - query both portable metadata and local-only path metadata
    - local_file_path remains searchable for local desktop workflows,
      but it is no longer the shared identity
    """
    lower_query = query.strip().lower()

    if "ocr" in lower_query and ("document" in lower_query or "pdf" in lower_query or "file" in lower_query):
        rows = (
            db.query(DocumentRecord)
            .filter(DocumentRecord.ocr_used == True)  # noqa: E712
            .order_by(DocumentRecord.updated_at.desc(), DocumentRecord.id.desc())
            .limit(limit)
            .all()
        )
        return [_serialize_document_record(row) for row in rows]

    token_filters = []
    tokens = [token for token in lower_query.split() if len(token) >= 2]
    for token in tokens:
        token_filters.append(func.lower(DocumentRecord.file_name).contains(token))
        token_filters.append(func.lower(DocumentRecord.source_ref).contains(token))
        token_filters.append(func.lower(DocumentRecord.extension).contains(token))
        token_filters.append(func.lower(DocumentRecord.document_id).contains(token))
        token_filters.append(func.lower(DocumentRecord.content_hash).contains(token))

        # Local-only, still searchable for local debugging/workflows
        token_filters.append(func.lower(DocumentRecord.local_file_path).contains(token))

    if any(word in lower_query for word in ["document", "file", "pdf", "docx", "ingest", "uploaded"]):
        rows = (
            db.query(DocumentRecord)
            .order_by(DocumentRecord.updated_at.desc(), DocumentRecord.id.desc())
            .limit(limit)
            .all()
        )
        return [_serialize_document_record(row) for row in rows]

    if not token_filters:
        return []

    rows = (
        db.query(DocumentRecord)
        .filter(or_(*token_filters))
        .order_by(DocumentRecord.updated_at.desc(), DocumentRecord.id.desc())
        .limit(limit)
        .all()
    )

    return [_serialize_document_record(row) for row in rows]