from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session

from memory_service.db import Base, engine, SessionLocal
from memory_service.models import MemoryRecord, ActionRecord
from memory_service.schemas import MemorySaveRequest, MemoryRetrieveRequest, ActionLogRequest
from memory_service.qdrant_store import upsert_memory_point, semantic_search

# Create DB tables on startup
Base.metadata.create_all(bind=engine)

# Create FastAPI instance
app = FastAPI(title="Arfy Memory Service")


def get_db():
    """
    Create and provide a database session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/health")
async def health():
    """
    Simple health check endpoint.
    """
    return {"status": "ok", "service": "memory"}


@app.post("/memory/save")
async def save_memory(req: MemorySaveRequest, db: Session = Depends(get_db)):
    """
    Save exact structured memory to SQLite.
    Also push the same memory into Qdrant for semantic search.
    """
    record = MemoryRecord(
        category=req.category,
        key=req.key,
        value=str(req.value)
    )

    db.add(record)
    db.commit()
    db.refresh(record)

    upsert_memory_point(
        point_id=record.id,
        category=req.category,
        key=req.key,
        value=str(req.value)
    )

    return {
        "success": True,
        "id": record.id,
        "message": "Memory saved successfully."
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
    Return all structured memory rows from SQLite.
    """
    rows = db.query(MemoryRecord).all()

    return {
        "memories": [
            {
                "id": r.id,
                "category": r.category,
                "key": r.key,
                "value": r.value,
                "created_at": r.created_at.isoformat() if r.created_at else None
            }
            for r in rows
        ]
    }


@app.post("/memory/action")
async def log_action(req: ActionLogRequest, db: Session = Depends(get_db)):
    """
    Save action history into SQLite.
    """
    record = ActionRecord(
        action=req.action,
        type=req.type,
        success=req.success
    )

    db.add(record)
    db.commit()
    db.refresh(record)

    return {
        "success": True,
        "message": "Action logged."
    }


@app.get("/memory/history")
async def get_history(limit: int = 10, db: Session = Depends(get_db)):
    """
    Return recent action history.
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
                "timestamp": r.timestamp.isoformat() if r.timestamp else None
            }
            for r in rows
        ]
    }