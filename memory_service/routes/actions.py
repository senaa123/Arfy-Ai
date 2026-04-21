# memory_service/routes/actions.py

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from memory_service.dependencies import get_db
from memory_service.schemas import ActionLogRequest
from memory_service.services.structured_store import get_recent_action_history, log_action_record

router = APIRouter(tags=["actions"])


@router.post("/memory/action")
async def log_action(req: ActionLogRequest, db: Session = Depends(get_db)):
    """
    Save a structured action log.
    """
    record = log_action_record(
        db=db,
        action=req.action,
        action_type=req.type,
        success=req.success,
        session_id=req.session_id,
        payload_json=req.payload_json,
    )

    return {
        "success": True,
        "id": record.id,
        "action_id": record.action_id,
        "message": "Action logged.",
    }


@router.get("/memory/history")
async def get_history(limit: int = 10, db: Session = Depends(get_db)):
    """
    Return recent action history for agent-side safety checks.
    """
    rows = get_recent_action_history(db, limit=limit)

    return {
        "history": [
            {
                "action": row.action,
                "type": row.type,
                "success": row.success,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]
    }