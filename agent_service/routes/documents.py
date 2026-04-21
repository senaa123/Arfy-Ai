# agent_service/routes/documents.py

from fastapi import APIRouter
from starlette.concurrency import run_in_threadpool

from agent_service.models import AgentDocumentIngestRequest, AgentDocumentIngestResponse
from agent_service.plugins.executor import execute_registered_tool

router = APIRouter(tags=["documents"])


@router.post("/agent/document/ingest", response_model=AgentDocumentIngestResponse)
async def agent_document_ingest(req: AgentDocumentIngestRequest):
    """
    Manual test endpoint for the extracted document service.

    Phase 3B change:
    - now also returns whether document metadata registered into memory_service

    Phase 4B:
    - moved out of main.py so document-related testing stays isolated
    """
    tool_used, tool_result = await run_in_threadpool(
        execute_registered_tool,
        session_id=req.session_id,
        user_text=f"Ingest document at {req.file_path}",
        tool_name="document_ingest",
        intent=None,
        extracted_data={
            "file_path": req.file_path,
            "enable_ocr": req.enable_ocr,
            "persist": req.persist,
            "pdf_ocr_min_chars": req.pdf_ocr_min_chars,
            "chunk_size": req.chunk_size,
            "chunk_overlap": req.chunk_overlap,
            "index_chunks_to_vector": req.index_chunks_to_vector,
        },
        memories=[],
        history=[],
    )

    if not isinstance(tool_result, dict):
        return AgentDocumentIngestResponse(
            success=False,
            message="Document tool returned an invalid response.",
            tool_used=tool_used or "document_ingest",
        )

    return AgentDocumentIngestResponse(
        success=tool_result.get("success", False),
        message=tool_result.get("message", "No message returned."),
        tool_used=tool_used or "document_ingest",
        document_id=tool_result.get("document_id"),
        source_ref=tool_result.get("source_ref"),
        content_hash=tool_result.get("content_hash"),
        local_file_path=tool_result.get("local_file_path"),
        file_name=tool_result.get("file_name"),
        extension=tool_result.get("extension"),
        text_length=tool_result.get("text_length", 0),
        chunk_count=tool_result.get("chunk_count", 0),
        ocr_used=tool_result.get("ocr_used", False),
        preview=tool_result.get("preview"),
        persisted_dir=tool_result.get("persisted_dir"),
        memory_registered=tool_result.get("memory_registered", False),
        memory_register_message=tool_result.get("memory_register_message"),
        chunks_registered=tool_result.get("chunks_registered", 0),
        chunks_indexed=tool_result.get("chunks_indexed", 0),
        chunk_register_message=tool_result.get("chunk_register_message"),
        metadata=tool_result.get("metadata", {}),
    )