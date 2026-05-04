"""
Document ingest orchestration.

This file is the main coordinator for document_service ingestion.

Responsibilities:
- choose the correct extractor
- chunk the extracted text
- optionally persist
- optionally register metadata/chunks with memory service
- return the stable response shape expected by the existing agent path
"""

from __future__ import annotations

from pathlib import Path

from document_service.chunking import build_chunks, choose_chunking_strategy
from document_service.clients.memory_client import (
    register_document_chunks,
    register_document_metadata,
)
from document_service.extractors import (
    extract_pdf_document,
    extract_non_pdf_document,
)
from document_service.schemas import DocumentIngestRequest, DocumentIngestResponse
from document_service.storage import persist_document


def _extract_document_by_type(file_path: str, enable_ocr: bool, pdf_ocr_min_chars: int):
    """
    Route the file to the right extractor.

    Important:
    - PDF goes through pdf_pipeline.py via extractors/pdf.py
    - images still go through the OCR service client path
    - no local OCR engine is used here
    """
    path = Path(file_path)

    # Fail early with a clear message if the desktop sends an invalid path.
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if not path.is_file():
        raise ValueError(f"Path is not a file: {file_path}")
    
    extension = path.suffix.lower()

    if extension == ".pdf":
        # Pass through the existing PDF pipeline logic unchanged.
        try:
            return extract_pdf_document(
                file_path=file_path,
                enable_ocr=enable_ocr,
                min_text_chars=pdf_ocr_min_chars,
            )
        except TypeError:
            # In case your current pdf_pipeline signature differs slightly.
            try:
                return extract_pdf_document(
                    file_path=file_path,
                    enable_ocr=enable_ocr,
                    pdf_ocr_min_chars=pdf_ocr_min_chars,
                )
            except TypeError:
                try:
                    return extract_pdf_document(
                        file_path=file_path,
                        enable_ocr=enable_ocr,
                    )
                except TypeError:
                    return extract_pdf_document(file_path, enable_ocr=enable_ocr)

    try:
        return extract_non_pdf_document(file_path=file_path, enable_ocr=enable_ocr)
    except TypeError:
        return extract_non_pdf_document(file_path, enable_ocr=enable_ocr)


def ingest_document_flow(
    req: DocumentIngestRequest,
) -> DocumentIngestResponse:
    """
    Main ingest workflow used by the route.

    Returns the stable response shape expected by the existing agent-side
    document ingest endpoint.
    """
    extracted_document = _extract_document_by_type(
        file_path=req.file_path,
        enable_ocr=req.enable_ocr,
        pdf_ocr_min_chars=req.pdf_ocr_min_chars,
    )

    strategy = choose_chunking_strategy(
        chunk_size=req.chunk_size,
        chunk_overlap=req.chunk_overlap,
    )

    chunks = build_chunks(
        extracted_document.text,
        strategy,
        chunk_id_namespace=extracted_document.document_id,
    )

    # Preserve simple page metadata when it is already knowable without adding
    # a new parsing/indexing boundary. Multi-page chunk-to-page mapping is still
    # intentionally out of scope here.
    if extracted_document.extension.lower() == ".pdf":
        page_count = int((extracted_document.metadata or {}).get("page_count") or 0)
        if page_count == 1:
            for chunk in chunks:
                chunk.pages = [1]
    elif (extracted_document.metadata or {}).get("ocr_mode") == "image_file":
        for chunk in chunks:
            chunk.pages = [1]

    persisted_dir = None
    if req.persist:
        persisted_dir = persist_document(extracted_document, chunks)

    memory_sync_result = register_document_metadata(
        document_id=extracted_document.document_id,
        source_ref=extracted_document.source_ref,
        content_hash=extracted_document.content_hash,
        file_name=extracted_document.file_name,
        local_file_path=extracted_document.local_file_path,
        extension=extracted_document.extension,
        text_length=len(extracted_document.text),
        chunk_count=len(chunks),
        ocr_used=extracted_document.ocr_used,
    )

    chunk_sync_result = {
        "success": False,
        "message": "Skipped chunk registration because document metadata registration failed.",
        "registered_count": 0,
        "indexed_count": 0,
    }

    if memory_sync_result.get("success", False):
        chunk_sync_result = register_document_chunks(
            document_id=extracted_document.document_id,
            file_name=extracted_document.file_name,
            extension=extracted_document.extension,
            chunks=[chunk.model_dump() for chunk in chunks],
            index_to_vector=req.index_chunks_to_vector,
        )

    preview = extracted_document.text[:300].strip()
    if preview and len(extracted_document.text) > 300:
        preview += "..."

    return DocumentIngestResponse(
        success=True,
        message="Document ingested successfully.",
        document_id=extracted_document.document_id,
        source_ref=extracted_document.source_ref,
        content_hash=extracted_document.content_hash,
        local_file_path=extracted_document.local_file_path,
        file_name=extracted_document.file_name,
        extension=extracted_document.extension,
        text_length=len(extracted_document.text or ""),
        chunk_count=len(chunks),
        ocr_used=bool(getattr(extracted_document, "ocr_used", False)),
        preview=preview,
        persisted_dir=persisted_dir,
        memory_registered=memory_sync_result.get("success", False),
        memory_register_message=memory_sync_result.get("message"),
        chunks_registered=chunk_sync_result.get("registered_count", 0),
        chunks_indexed=chunk_sync_result.get("indexed_count", 0),
        chunk_register_message=chunk_sync_result.get("message"),
        metadata=getattr(extracted_document, "metadata", {}) or {},
    )
