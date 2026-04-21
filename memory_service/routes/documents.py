# memory_service/routes/documents.py

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from memory_service.dependencies import get_db
from memory_service.models import DocumentRecord
from memory_service.qdrant_store import DOCUMENT_COLLECTION
from memory_service.schemas import (
    DocumentChunkBatchRegisterRequest,
    DocumentChunkBatchRegisterResponse,
    DocumentMetaSaveRequest,
)
from memory_service.services.linker import create_vector_link, get_vector_link
from memory_service.services.structured_store import (
    get_document_record_by_document_id,
    list_document_chunk_records,
    upsert_document_chunk_record,
    upsert_document_record,
)
from memory_service.services.vector_store import save_document_chunk_vector

router = APIRouter(tags=["documents"])


@router.post("/documents/register")
async def register_document_meta(
    req: DocumentMetaSaveRequest,
    db: Session = Depends(get_db),
):
    """
    Save document metadata into structured memory.

    Phase 4:
    - document_id is the portable shared id
    - source_ref/content_hash are sync-safe metadata
    - local_file_path is stored as local-only metadata

    Phase 4B:
    - route moved out of main.py only
    - document storage ownership stays in memory_service
    """
    record = upsert_document_record(
        db=db,
        document_id=req.document_id,
        source_ref=req.source_ref,
        content_hash=req.content_hash,
        file_name=req.file_name,
        local_file_path=req.local_file_path,
        extension=req.extension,
        text_length=req.text_length,
        chunk_count=req.chunk_count,
        ocr_used=req.ocr_used,
    )

    return {
        "success": True,
        "id": record.id,
        "document_id": record.document_id,
        "source_ref": record.source_ref,
        "content_hash": record.content_hash,
        "message": "Document metadata registered.",
    }


@router.post("/documents/chunks/register", response_model=DocumentChunkBatchRegisterResponse)
async def register_document_chunks(
    req: DocumentChunkBatchRegisterRequest,
    db: Session = Depends(get_db),
):
    """
    Register a batch of document chunks.

    Phase 3C purpose:
    - create structured chunk rows
    - optionally index them into vector memory
    - create vector links for each indexed chunk
    """
    document_record = get_document_record_by_document_id(
        db=db,
        document_id=req.document_id,
    )

    if document_record is None:
        return DocumentChunkBatchRegisterResponse(
            success=False,
            message=(
                "Document metadata row not found. "
                "Register document metadata before chunk registration."
            ),
            document_id=req.document_id,
            registered_count=0,
            indexed_count=0,
            failed_count=len(req.chunks),
        )

    registered_count = 0
    indexed_count = 0
    failed_count = 0

    for chunk in req.chunks:
        try:
            chunk_record = upsert_document_chunk_record(
                db=db,
                chunk_id=chunk.chunk_id,
                document_id=req.document_id,
                chunk_index=chunk.chunk_index,
                text=chunk.text,
                start_char=chunk.start_char,
                end_char=chunk.end_char,
                indexed_to_vector=req.index_to_vector,
            )
            registered_count += 1

            if req.index_to_vector:
                existing_link = get_vector_link(
                    db=db,
                    owner_type="document_chunk_record",
                    owner_public_id=chunk_record.chunk_id,
                    vector_kind="document_chunk",
                )

                point_id = save_document_chunk_vector(
                    document_id=req.document_id,
                    chunk_id=chunk_record.chunk_id,
                    chunk_record_id=chunk_record.id,
                    file_name=req.file_name,
                    extension=req.extension,
                    chunk_index=chunk_record.chunk_index,
                    text=chunk_record.text,
                    start_char=chunk_record.start_char,
                    end_char=chunk_record.end_char,
                    point_id=existing_link.qdrant_point_id if existing_link else None,
                )

                if existing_link is None:
                    create_vector_link(
                        db=db,
                        owner_type="document_chunk_record",
                        owner_public_id=chunk_record.chunk_id,
                        owner_id=chunk_record.id,
                        qdrant_collection=DOCUMENT_COLLECTION,
                        qdrant_point_id=point_id,
                        vector_kind="document_chunk",
                    )

                indexed_count += 1

        except Exception:
            # Fail-soft per chunk so one bad chunk does not kill the whole batch
            failed_count += 1
            continue

    success = failed_count == 0
    message = (
        "Document chunks registered successfully."
        if success
        else "Document chunks registered with some failures."
    )

    return DocumentChunkBatchRegisterResponse(
        success=success,
        message=message,
        document_id=req.document_id,
        registered_count=registered_count,
        indexed_count=indexed_count,
        failed_count=failed_count,
    )


@router.get("/documents/all")
async def list_documents(db: Session = Depends(get_db)):
    """
    Return all registered document metadata rows.
    """
    rows = db.query(DocumentRecord).order_by(DocumentRecord.created_at.desc()).all()

    return {
        "documents": [
            {
                "id": row.id,
                "document_id": row.document_id,
                "source_ref": row.source_ref,
                "content_hash": row.content_hash,
                "file_name": row.file_name,
                "local_file_path": row.local_file_path,
                "extension": row.extension,
                "text_length": row.text_length,
                "chunk_count": row.chunk_count,
                "ocr_used": row.ocr_used,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]
    }


@router.get("/documents/{document_id}/chunks")
async def list_document_chunks(
    document_id: str,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """
    Return structured chunk rows for one document.

    Useful for debugging Phase 3C.
    """
    rows = list_document_chunk_records(
        db=db,
        document_id=document_id,
        limit=limit,
    )

    return {
        "document_id": document_id,
        "chunks": [
            {
                "id": row.id,
                "chunk_id": row.chunk_id,
                "chunk_index": row.chunk_index,
                "document_id": row.document_id,
                "text_preview": row.text[:200],
                "start_char": row.start_char,
                "end_char": row.end_char,
                "indexed_to_vector": row.indexed_to_vector,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ],
    }