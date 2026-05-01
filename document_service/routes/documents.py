"""
Thin document routes.

This file should stay small:
- receive the request
- call the workflow
- forward the normalized response

Do not put extraction/chunking/persistence logic here.
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from document_service.schemas import DocumentIngestRequest, DocumentIngestResponse
from document_service.workflows import ingest_document_flow

router = APIRouter()


@router.post("/documents/ingest", response_model=DocumentIngestResponse)
async def ingest_document(req: DocumentIngestRequest):
    """
    Ingest a document through the service pipeline.
    """
    try:
        return ingest_document_flow(req)
    except Exception as e:
        return JSONResponse(
            status_code=400,
            content=DocumentIngestResponse(
                success=False,
                message=str(e),
            ).model_dump(),
        )
