import os
from pathlib import Path

import requests
from dotenv import load_dotenv

from agent_service.plugins.base import ToolContext, ToolPlugin, ToolSpec

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(env_path)

RAG_SERVICE_URL = os.getenv("RAG_SERVICE_URL")


def _collect_candidate_document_ids(context: ToolContext) -> list[str]:
    """
    Collect likely document ids for RAG narrowing.

    Priority:
    1. explicit document_ids extracted by the router
    2. document_ids found in retrieved memory context

    We keep the logic conservative and deduplicated.
    """
    explicit = context.extracted_data.get("document_ids", [])
    ordered: list[str] = []
    seen: set[str] = set()

    for value in explicit or []:
        doc_id = str(value).strip()
        if doc_id and doc_id not in seen:
            seen.add(doc_id)
            ordered.append(doc_id)

    for memory in context.memories:
        doc_id = getattr(memory, "document_id", None)
        memory_kind = getattr(memory, "memory_kind", None)
        if not doc_id:
            continue
        if memory_kind not in {"document_meta", "document_chunk", None}:
            continue

        doc_id = str(doc_id).strip()
        if doc_id and doc_id not in seen:
            seen.add(doc_id)
            ordered.append(doc_id)

    return ordered


class RagAskToolPlugin(ToolPlugin):
    """
    HTTP plugin for the separate rag_service.

    The agent remains the orchestrator. It does not perform retrieval or answer
    synthesis itself for document-grounded questions.
    """

    spec = ToolSpec(
        name="rag_ask",
        description="Ask the separate rag_service to answer from document chunks.",
        transport="http",
        supported_intents=["document_qa"],
        enabled=True,
        timeout_seconds=45,
    )

    def execute(self, context: ToolContext) -> dict:
        question = str(context.extracted_data.get("question") or context.user_text).strip()
        document_ids = _collect_candidate_document_ids(context)
        top_k = int(context.extracted_data.get("top_k", 8) or 8)
        final_k = int(context.extracted_data.get("final_k", 4) or 4)

        if not question:
            return {
                "grounded": False,
                "answer": "I need a question before I can search the document evidence.",
                "message": "rag_ask requires a non-empty question.",
            }

        try:
            response = requests.post(
                f"{RAG_SERVICE_URL}/rag/ask",
                json={
                    "question": question,
                    "document_ids": document_ids,
                    "top_k": top_k,
                    "final_k": final_k,
                    "session_id": context.session_id,
                },
                timeout=self.spec.timeout_seconds,
            )

            payload = {}
            try:
                payload = response.json()
            except Exception:
                payload = {}

            if response.ok:
                return payload

            detail_message = payload.get("message") or payload.get("detail")

            return {
                "grounded": False,
                "answer": payload.get(
                    "answer",
                    detail_message or f"RAG service returned HTTP {response.status_code}.",
                ),
                "message": detail_message or f"RAG service returned HTTP {response.status_code}.",
            }

        except requests.Timeout:
            return {
                "grounded": False,
                "answer": "The document-answering service took too long to respond.",
                "message": "RAG service timed out.",
            }
        except requests.RequestException as e:
            return {
                "grounded": False,
                "answer": "I couldn't reach the document-answering service right now.",
                "message": f"Could not reach RAG service: {e}",
            }
        except Exception as e:
            return {
                "grounded": False,
                "answer": "Something unexpected went wrong while asking the document-answering service.",
                "message": f"Unexpected RAG plugin error: {e}",
            }
