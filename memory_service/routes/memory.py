# memory_service/routes/memory.py

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from memory_service.dependencies import get_db
from memory_service.qdrant_store import STRUCTURED_COLLECTION
from memory_service.schemas import MemoryContextRequest, MemoryRetrieveRequest, MemorySaveRequest
from memory_service.services.linker import create_vector_link, get_vector_link
from memory_service.services.memory_policy import should_write_structured_to_vector
from memory_service.services.retrieval import build_memory_context
from memory_service.services.structured_store import list_all_memories, save_memory_record
from memory_service.services.vector_store import save_structured_memory_vector

router = APIRouter(tags=["memory"])


@router.post("/memory/save")
async def save_memory(req: MemorySaveRequest, db: Session = Depends(get_db)):
    """
    Save one durable memory into the structured layer.

    Optionally also mirror it into vector memory for semantic recall.

    Phase 4:
    - return memory_id as the portable public id
    - vector link lookup uses memory_id instead of local row id only

    Phase 4B:
    - this logic moved out of main.py only
    - endpoint path and behavior stay the same
    """
    record = save_memory_record(
        db=db,
        category=req.category,
        key=req.key,
        value=str(req.value),
        session_id=req.session_id,
        document_id=req.document_id,
        source=req.source,
    )

    vector_point_id = None
    vector_warning = None

    if should_write_structured_to_vector(req.category, req.write_to_vector):
        try:
            existing_link = get_vector_link(
                db=db,
                owner_type="memory_record",
                owner_public_id=record.memory_id,
                vector_kind="durable_memory",
            )

            vector_point_id = save_structured_memory_vector(
                category=record.category,
                key=record.key,
                value=record.value,
                memory_id=record.memory_id,
                record_id=record.id,
                session_id=record.session_id,
                document_id=record.document_id,
                source=record.source,
                point_id=existing_link.qdrant_point_id if existing_link else None,
            )

            if existing_link is None:
                create_vector_link(
                    db=db,
                    owner_type="memory_record",
                    owner_public_id=record.memory_id,
                    owner_id=record.id,
                    qdrant_collection=STRUCTURED_COLLECTION,
                    qdrant_point_id=vector_point_id,
                    vector_kind="durable_memory",
                )
        except Exception as e:
            vector_warning = str(e)

    return {
        "success": True,
        "id": record.id,
        "memory_id": record.memory_id,
        "vector_point_id": vector_point_id,
        "message": "Memory saved successfully.",
        "vector_warning": vector_warning,
    }


@router.post("/memory/context")
async def memory_context(req: MemoryContextRequest, db: Session = Depends(get_db)):
    """
    Main retrieval endpoint used by the agent.
    """
    return build_memory_context(
        db=db,
        query=req.query,
        exact_limit=req.exact_limit,
        semantic_limit=req.semantic_limit,
    )


@router.post("/memory/retrieve")
async def retrieve_memory(req: MemoryRetrieveRequest, db: Session = Depends(get_db)):
    """
    Backward-compatible retrieval endpoint.
    """
    context = build_memory_context(
        db=db,
        query=req.query,
        exact_limit=min(3, req.limit),
        semantic_limit=req.limit,
    )

    return {"memories": context["merged"][: req.limit]}


@router.get("/memory/all")
async def get_all_memory(db: Session = Depends(get_db)):
    """
    Return all durable structured memories.
    """
    rows = list_all_memories(db)

    return {
        "memories": [
            {
                "id": row.id,
                "memory_id": row.memory_id,
                "category": row.category,
                "key": row.key,
                "value": row.value,
                "session_id": row.session_id,
                "document_id": row.document_id,
                "source": row.source,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "updated_at": row.updated_at.isoformat() if row.updated_at else None,
            }
            for row in rows
        ]
    }