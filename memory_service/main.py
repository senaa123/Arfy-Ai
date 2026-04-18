from fastapi import Depends, FastAPI
from sqlalchemy.orm import Session

from memory_service.db import Base, SessionLocal, engine
from memory_service.models import ActionRecord, MemoryRecord, SummaryRecord
from memory_service.qdrant_store import (
    generate_qdrant_id,
    semantic_search,
    upsert_memory_point,
    upsert_session_archive,
    upsert_session_summary,
)
from memory_service.schemas import (
    ActionLogRequest,
    MemoryRetrieveRequest,
    MemorySaveRequest,
    SessionArchiveChunkRequest,
    SessionFinalizeRequest,
)
from memory_service.summarizer import (
    build_transcript,
    summarize_messages,
    extract_preference_candidates,
)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Arfy Memory Service")


def get_db():
    """
    Provide a database session for each request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def save_structured_memory(
    db: Session,
    category: str,
    key: str,
    value: str,
) -> dict:
    """
    Internal helper to save structured memory into SQLite and Qdrant.
    """
    record = MemoryRecord(
        category=category,
        key=key,
        value=str(value),
    )

    db.add(record)
    db.commit()
    db.refresh(record)

    upsert_memory_point(
        point_id=generate_qdrant_id(),
        category=category,
        key=key,
        value=str(value),
        metadata={
            "created_at": record.created_at.isoformat() if record.created_at else None,
            "memory_kind": "durable_memory",
            "sqlite_id": record.id,
        },
    )

    return {
        "id": record.id,
        "category": category,
        "key": key,
        "value": value,
    }


@app.get("/health")
async def health():
    """
    Health check endpoint.
    """
    return {"status": "ok", "service": "memory"}


@app.post("/memory/save")
async def save_memory(req: MemorySaveRequest, db: Session = Depends(get_db)):
    """
    Save exact structured durable memory to SQLite
    and also to Qdrant for semantic retrieval.
    """
    saved = save_structured_memory(
        db=db,
        category=req.category,
        key=req.key,
        value=str(req.value),
    )

    return {
        "success": True,
        "id": saved["id"],
        "message": "Memory saved successfully.",
    }


@app.post("/memory/retrieve")
async def retrieve_memory(req: MemoryRetrieveRequest):
    """
    Retrieve memories semantically from Qdrant.
    """
    memories = semantic_search(req.query, limit=req.limit)
    return {"memories": memories}


@app.get("/memory/all")
async def get_all_memory(db: Session = Depends(get_db)):
    """
    Return all structured durable memories from SQLite.
    """
    rows = db.query(MemoryRecord).all()

    return {
        "memories": [
            {
                "id": r.id,
                "category": r.category,
                "key": r.key,
                "value": r.value,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]
    }


@app.post("/memory/action")
async def log_action(req: ActionLogRequest, db: Session = Depends(get_db)):
    """
    Save action execution history into SQLite.
    """
    record = ActionRecord(
        action=req.action,
        type=req.type,
        success=req.success,
    )

    db.add(record)
    db.commit()
    db.refresh(record)

    return {
        "success": True,
        "message": "Action logged.",
    }


@app.get("/memory/history")
async def get_history(limit: int = 10, db: Session = Depends(get_db)):
    """
    Return recent action history for safety checks.
    """
    rows = (
        db.query(ActionRecord)
        .order_by(ActionRecord.timestamp.desc())
        .limit(limit)
        .all()
    )

    return {
        "history": [
            {
                "action": r.action,
                "type": r.type,
                "success": r.success,
                "timestamp": r.timestamp.isoformat() if r.timestamp else None,
            }
            for r in rows
        ]
    }


@app.post("/session/archive/chunk")
async def archive_session_chunk(req: SessionArchiveChunkRequest):
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

    point_id = upsert_session_archive(
        session_id=req.session_id,
        transcript=transcript,
        summary=summary,
        session_started_at=req.session_started_at,
        session_ended_at=req.messages[-1].timestamp if req.messages else None,
        chunk_reason=req.chunk_reason,
    )

    return {
        "success": True,
        "message": "Session chunk archived.",
        "point_id": point_id,
        "archived_messages": len(req.messages),
        "summary": summary,
    }


@app.post("/session/archive/finalize")
async def finalize_session_archive(
    req: SessionFinalizeRequest,
    db: Session = Depends(get_db),
):
    """
    Finalize an ended session.

    Saves:
    - archived transcript to Qdrant
    - final summary to SQLite
    - final summary to Qdrant
    - extracted preference candidates into durable memory
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

    # Save summary in SQLite
    summary_record = SummaryRecord(
        session_id=req.session_id,
        summary=summary,
    )
    db.add(summary_record)
    db.commit()
    db.refresh(summary_record)

    # Save final transcript chunk to Qdrant
    transcript_point_id = upsert_session_archive(
        session_id=req.session_id,
        transcript=transcript,
        summary=summary,
        session_started_at=req.session_started_at,
        session_ended_at=req.session_ended_at,
        chunk_reason="session_end",
    )

    # Save final session summary to Qdrant too
    summary_point_id = upsert_session_summary(
        session_id=req.session_id,
        summary=summary,
        session_started_at=req.session_started_at,
        session_ended_at=req.session_ended_at,
        sqlite_id=summary_record.id,
    )

    # Extract stable preference candidates from this session
    preference_candidates = extract_preference_candidates(req.messages)
    saved_preferences = []

    for item in preference_candidates:
        saved = save_structured_memory(
            db=db,
            category=item["category"],
            key=item["key"],
            value=item["value"],
        )
        saved_preferences.append(saved)

    return {
        "success": True,
        "message": "Session finalized and summarized.",
        "session_id": req.session_id,
        "summary_id": summary_record.id,
        "summary_point_id": summary_point_id,
        "transcript_point_id": transcript_point_id,
        "summary": summary,
        "preference_candidates_saved": saved_preferences,
    }