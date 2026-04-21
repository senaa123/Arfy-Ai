import os
from pathlib import Path

import requests
from dotenv import load_dotenv

from agent_service.plugins.base import ToolContext, ToolPlugin, ToolSpec

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(env_path)

DOCUMENT_SERVICE_URL = os.getenv("DOCUMENT_SERVICE_URL", "http://127.0.0.1:8002")


class DocumentIngestToolPlugin(ToolPlugin):
    """
    HTTP plugin for the separate document service.

    The agent does not handle PDFs or OCR directly.
    It only forwards document-ingest requests.
    """

    spec = ToolSpec(
        name="document_ingest",
        description="Ingest documents through the separate document service.",
        transport="http",
        supported_intents=[],
        enabled=True,
        timeout_seconds=60,
    )

    def execute(self, context: ToolContext) -> dict:
        file_path = context.extracted_data.get("file_path")
        enable_ocr = context.extracted_data.get("enable_ocr", True)
        persist = context.extracted_data.get("persist", True)
        pdf_ocr_min_chars = context.extracted_data.get("pdf_ocr_min_chars", 30)
        chunk_size = context.extracted_data.get("chunk_size", 1200)
        chunk_overlap = context.extracted_data.get("chunk_overlap", 200)
        index_chunks_to_vector = context.extracted_data.get("index_chunks_to_vector", True)

        if not file_path:
            return {
                "success": False,
                "message": "document_ingest requires 'file_path' in extracted_data.",
            }

        try:
            response = requests.post(
                f"{DOCUMENT_SERVICE_URL}/documents/ingest",
                json={
                    "file_path": file_path,
                    "enable_ocr": enable_ocr,
                    "persist": persist,
                    "pdf_ocr_min_chars": pdf_ocr_min_chars,
                    "chunk_size": chunk_size,
                    "chunk_overlap": chunk_overlap,
                    "index_chunks_to_vector": index_chunks_to_vector,
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

            # Preserve the upstream document-service message so the agent
            # returns the real failure reason instead of a generic HTTP error.
            return {
                "success": False,
                "message": payload.get(
                    "message",
                    f"Document service returned HTTP {response.status_code}.",
                ),
            }

        except requests.Timeout:
            return {
                "success": False,
                "message": "Document service timed out.",
            }
        except requests.RequestException as e:
            return {
                "success": False,
                "message": f"Could not reach document service: {e}",
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Unexpected document plugin error: {e}",
            }
