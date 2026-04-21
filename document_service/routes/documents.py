# document_service/routes/documents.py

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from document_service.schemas import DocumentIngestRequest, DocumentIngestResponse
from document_service.workflows import ingest_document_flow

router = APIRouter(tags=["documents"])


@router.post("/documents/ingest", response_model=DocumentIngestResponse)
async def ingest_document(req: DocumentIngestRequest):
    """
    Ingest one document file.

    Phase 4B:
    - the HTTP route lives here
    - the real ingest workflow lives in document_service.workflows
    - endpoint behavior stays the same
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