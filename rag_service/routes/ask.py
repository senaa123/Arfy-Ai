"""
Ask route for rag_service.

This route should stay thin:
- accept request
- call workflow
- return normalized response

It should NOT contain:
- retrieval logic
- reranking logic
- prompt-building logic
- grounding checks
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from rag_service.schemas import RagAskRequest, RagAskResponse
from rag_service.workflows import answer_question_workflow

router = APIRouter(tags=["rag"])


@router.post("/rag/ask", response_model=RagAskResponse)
def ask_rag(req: RagAskRequest) -> RagAskResponse:
    try:
        return answer_question_workflow(req)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"RAG request failed: {exc}") from exc