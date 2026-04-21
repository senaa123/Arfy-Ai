# memory_service/routes/sessions.py

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from memory_service.dependencies import get_db
from memory_service.qdrant_store import SESSION_COLLECTION, STRUCTURED_COLLECTION
from memory_service.schemas import SessionArchiveChunkRequest, SessionFinalizeRequest
from memory_service.services.linker import create_vector_link, get_vector_link
from memory_service.services.structured_store import save_memory_record, upsert_session_record
from memory_service.services.vector_store import (
    save_session_archive_vector,
    save_session_summary_vector,
    save_structured_memory_vector,
)
from memory_service.summarizer import (
    build_transcript,
    extract_preference_candidates,
    summarize_messages,
)

router = APIRouter(tags=["sessions"])


@router.post("/session/archive/chunk")
async def archive_session_chunk(
    req: SessionArchiveChunkRequest,
    db: Session = Depends(get_db),
):
    """
    Archive overflowed short-term messages into vector memory.
    """
    if not req.messages:
        return {
            "success": True,
            "message": "No messages to archive.",
            "archived_messages": 0,
        }

    transcript = build_transcript(req.messages)
    summary = summarize_messages(req.messages)

    session_record = upsert_session_record(
        db=db,
        session_id=req.session_id,
        started_at=req.session_started_at,
        ended_at=None,
        summary=None,
        message_count=len(req.messages),
    )

    existing_link = get_vector_link(
        db=db,
        owner_type="session_record",
        owner_public_id=session_record.session_id,
        vector_kind="session_archive",
    )

    point_id = save_session_archive_vector(
        session_id=req.session_id,
        transcript=transcript,
        summary=summary,
        linked_record_id=session_record.id,
        session_started_at=req.session_started_at,
        session_ended_at=req.messages[-1].timestamp if req.messages else None,
        chunk_reason=req.chunk_reason,
        point_id=existing_link.qdrant_point_id if existing_link else None,
    )

    if existing_link is None:
        create_vector_link(
            db=db,
            owner_type="session_record",
            owner_public_id=session_record.session_id,
            owner_id=session_record.id,
            qdrant_collection=SESSION_COLLECTION,
            qdrant_point_id=point_id,
            vector_kind="session_archive",
        )

    return {
        "success": True,
        "message": "Session chunk archived.",
        "point_id": point_id,
        "session_record_id": session_record.id,
        "archived_messages": len(req.messages),
        "summary": summary,
    }


@router.post("/session/archive/finalize")
async def finalize_session_archive(
    req: SessionFinalizeRequest,
    db: Session = Depends(get_db),
):
    """
    Finalize a session.

    Saves:
    - session metadata row
    - archived transcript chunk vector
    - final summary vector
    - extracted preference candidates as durable memory
    """
    if not req.messages:
        return {
            "success": True,
            "message": "Session ended with no messages.",
            "summary_saved": False,
            "preference_candidates_saved": [],
        }

    transcript = build_transcript(req.messages)
    summary = summarize_messages(req.messages)

    session_record = upsert_session_record(
        db=db,
        session_id=req.session_id,
        started_at=req.session_started_at,
        ended_at=req.session_ended_at,
        summary=summary,
        message_count=len(req.messages),
    )

    existing_archive_link = get_vector_link(
        db=db,
        owner_type="session_record",
        owner_public_id=session_record.session_id,
        vector_kind="session_archive",
    )
    transcript_point_id = save_session_archive_vector(
        session_id=req.session_id,
        transcript=transcript,
        summary=summary,
        linked_record_id=session_record.id,
        session_started_at=req.session_started_at,
        session_ended_at=req.session_ended_at,
        chunk_reason="session_end",
        point_id=existing_archive_link.qdrant_point_id if existing_archive_link else None,
    )
    if existing_archive_link is None:
        create_vector_link(
            db=db,
            owner_type="session_record",
            owner_public_id=session_record.session_id,
            owner_id=session_record.id,
            qdrant_collection=SESSION_COLLECTION,
            qdrant_point_id=transcript_point_id,
            vector_kind="session_archive",
        )

    existing_summary_link = get_vector_link(
        db=db,
        owner_type="session_record",
        owner_public_id=session_record.session_id,
        vector_kind="session_summary",
    )
    summary_point_id = save_session_summary_vector(
        session_id=req.session_id,
        summary=summary,
        linked_record_id=session_record.id,
        session_started_at=req.session_started_at,
        session_ended_at=req.session_ended_at,
        point_id=existing_summary_link.qdrant_point_id if existing_summary_link else None,
    )
    if existing_summary_link is None:
        create_vector_link(
            db=db,
            owner_type="session_record",
            owner_public_id=session_record.session_id,
            owner_id=session_record.id,
            qdrant_collection=SESSION_COLLECTION,
            qdrant_point_id=summary_point_id,
            vector_kind="session_summary",
        )

    preference_candidates = extract_preference_candidates(req.messages)
    saved_preferences = []

    for item in preference_candidates:
        memory_record = save_memory_record(
            db=db,
            category=item["category"],
            key=item["key"],
            value=item["value"],
            session_id=req.session_id,
            source="system",
        )

        existing_memory_link = get_vector_link(
            db=db,
            owner_type="memory_record",
            owner_public_id=memory_record.memory_id,
            vector_kind="durable_memory",
        )
        vector_point_id = save_structured_memory_vector(
            category=memory_record.category,
            key=memory_record.key,
            value=memory_record.value,
            memory_id=memory_record.memory_id,
            record_id=memory_record.id,
            session_id=memory_record.session_id,
            document_id=memory_record.document_id,
            source=memory_record.source,
            point_id=existing_memory_link.qdrant_point_id if existing_memory_link else None,
        )

        if existing_memory_link is None:
            create_vector_link(
                db=db,
                owner_type="memory_record",
                owner_public_id=memory_record.memory_id,
                owner_id=memory_record.id,
                qdrant_collection=STRUCTURED_COLLECTION,
                qdrant_point_id=vector_point_id,
                vector_kind="durable_memory",
            )

        saved_preferences.append(
            {
                "id": memory_record.id,
                "memory_id": memory_record.memory_id,
                "category": memory_record.category,
                "key": memory_record.key,
                "value": memory_record.value,
            }
        )

    return {
        "success": True,
        "message": "Session finalized and archived.",
        "session_record_id": session_record.id,
        "summary_saved": True,
        "transcript_point_id": transcript_point_id,
        "summary_point_id": summary_point_id,
        "preference_candidates_saved": saved_preferences,
    }