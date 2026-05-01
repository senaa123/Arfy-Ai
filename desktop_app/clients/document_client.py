# desktop_app/clients/document_client.py

import os
from pathlib import Path

import requests
from dotenv import load_dotenv

# Load desktop .env so the client can resolve DOCUMENT_SERVICE_URL locally.
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(env_path)

DOCUMENT_SERVICE_URL = os.getenv("DOCUMENT_SERVICE_URL", "http://127.0.0.1:8002")
INGEST_TIMEOUT = 120


def ingest_document(
    *,
    file_path: str,
    enable_ocr: bool = True,
    persist: bool = True,
    pdf_ocr_min_chars: int = 30,
    chunk_size: int = 1200,
    chunk_overlap: int = 200,
    index_chunks_to_vector: bool = True,
) -> dict:
    """
    Send a desktop-selected local file path directly to document_service.

    Phase 1 desktop -> document_service upload path:
    - desktop owns the native picker
    - desktop sends the selected local path
    - document_service reuses its existing /documents/ingest flow

    This is intentionally path-based for now because both services are
    running locally in the same machine-first architecture.
    """
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
            timeout=INGEST_TIMEOUT,
        )

        payload = {}
        try:
            payload = response.json()
        except Exception:
            payload = {}

        if response.ok:
            return payload

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
            "message": "Document service timed out while ingesting the file.",
        }

    except requests.RequestException as e:
        return {
            "success": False,
            "message": f"Could not reach document service: {e}",
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"Unexpected document client error: {e}",
        }
