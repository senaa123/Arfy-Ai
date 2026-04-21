# document_service/workflows.py

from pathlib import Path

from document_service.chunking import chunk_text
from document_service.clients.memory_client import (
    register_document_chunks,
    register_document_metadata,
)
from document_service.extractors import extract_non_pdf_document
from document_service.pdf_pipeline import extract_pdf_document
from document_service.schemas import DocumentIngestRequest, DocumentIngestResponse
from document_service.storage import persist_document


def ingest_document_flow(req: DocumentIngestRequest) -> DocumentIngestResponse:
    """
    Run the full document ingest workflow.

    Why this file exists in Phase 4B:
    - the ingest flow is document-service business logic
    - it is bigger than a simple route handler
    - main.py should stay bootstrap-only
    - routes should stay focused on HTTP concerns only

    Phase 3C:
    - register metadata
    - register chunks
    - optionally index chunk vectors

    Phase 4:
    - document identity is portable
    - local file path is treated as local-only metadata
    """
    path = Path(req.file_path)

    if path.suffix.lower() == ".pdf":
        extracted = extract_pdf_document(
            file_path=req.file_path,
            enable_ocr=req.enable_ocr,
            pdf_ocr_min_chars=req.pdf_ocr_min_chars,
        )
    else:
        extracted = extract_non_pdf_document(
            file_path=req.file_path,
            enable_ocr=req.enable_ocr,
        )

    chunks = chunk_text(
        text=extracted.text,
        chunk_size=req.chunk_size,
        chunk_overlap=req.chunk_overlap,
        chunk_id_namespace=extracted.document_id,
    )

    persisted_dir = None
    if req.persist:
        persisted_dir = persist_document(extracted, chunks)

    # Step 1: register document metadata
    memory_sync_result = register_document_metadata(
        document_id=extracted.document_id,
        source_ref=extracted.source_ref,
        content_hash=extracted.content_hash,
        file_name=extracted.file_name,
        local_file_path=extracted.local_file_path,
        extension=extracted.extension,
        text_length=len(extracted.text),
        chunk_count=len(chunks),
        ocr_used=extracted.ocr_used,
    )

    # Step 2: register chunks only if metadata registration succeeded
    chunk_sync_result = {
        "success": False,
        "message": "Skipped chunk registration because document metadata registration failed.",
        "registered_count": 0,
        "indexed_count": 0,
    }

    if memory_sync_result.get("success", False):
        chunk_sync_result = register_document_chunks(
            document_id=extracted.document_id,
            file_name=extracted.file_name,
            extension=extracted.extension,
            chunks=[chunk.model_dump() for chunk in chunks],
            index_to_vector=req.index_chunks_to_vector,
        )

    preview = extracted.text[:300] if extracted.text else ""

    return DocumentIngestResponse(
        success=True,
        message="Document ingested successfully.",
        document_id=extracted.document_id,
        source_ref=extracted.source_ref,
        content_hash=extracted.content_hash,
        local_file_path=extracted.local_file_path,
        file_name=extracted.file_name,
        extension=extracted.extension,
        text_length=len(extracted.text),
        chunk_count=len(chunks),
        ocr_used=extracted.ocr_used,
        preview=preview,
        persisted_dir=persisted_dir,
        memory_registered=memory_sync_result.get("success", False),
        memory_register_message=memory_sync_result.get("message"),
        chunks_registered=chunk_sync_result.get("registered_count", 0),
        chunks_indexed=chunk_sync_result.get("indexed_count", 0),
        chunk_register_message=chunk_sync_result.get("message"),
        metadata=extracted.metadata,
    )