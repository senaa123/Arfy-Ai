# document_service/clients/memory_client.py

import os
from pathlib import Path

import requests
from dotenv import load_dotenv

# Load env from document_service/.env
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(env_path)

MEMORY_SERVICE_URL = os.getenv("MEMORY_SERVICE_URL", "http://127.0.0.1:8000")


def register_document_metadata(
    *,
    document_id: str,
    source_ref: str,
    content_hash: str,
    file_name: str,
    local_file_path: str,
    extension: str,
    text_length: int,
    chunk_count: int,
    ocr_used: bool,
    timeout: int = 15,
) -> dict:
    """
    Register document metadata in memory_service.

    Phase 4 change:
    - source_ref and content_hash are portable/shared metadata
    - local_file_path is explicitly local-only metadata
    """
    try:
        response = requests.post(
            f"{MEMORY_SERVICE_URL}/documents/register",
            json={
                "document_id": document_id,
                "source_ref": source_ref,
                "content_hash": content_hash,
                "file_name": file_name,
                "local_file_path": local_file_path,
                "extension": extension,
                "text_length": text_length,
                "chunk_count": chunk_count,
                "ocr_used": ocr_used,
            },
            timeout=timeout,
        )
        response.raise_for_status()
        return response.json()

    except requests.Timeout:
        return {
            "success": False,
            "message": "Memory service timed out while registering document metadata.",
        }
    except requests.RequestException as e:
        return {
            "success": False,
            "message": f"Could not reach memory service: {e}",
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Unexpected document metadata sync error: {e}",
        }


def register_document_chunks(
    *,
    document_id: str,
    file_name: str,
    extension: str,
    chunks: list[dict],
    index_to_vector: bool = True,
    timeout: int = 30,
) -> dict:
    """
    Register document chunks in memory_service.

    Phase 3C rule remains unchanged:
    - document_service owns chunk creation
    - memory_service owns shared chunk storage and indexing
    """
    try:
        response = requests.post(
            f"{MEMORY_SERVICE_URL}/documents/chunks/register",
            json={
                "document_id": document_id,
                "file_name": file_name,
                "extension": extension,
                "index_to_vector": index_to_vector,
                "chunks": chunks,
            },
            timeout=timeout,
        )
        response.raise_for_status()
        return response.json()

    except requests.Timeout:
        return {
            "success": False,
            "message": "Memory service timed out while registering document chunks.",
            "document_id": document_id,
            "registered_count": 0,
            "indexed_count": 0,
            "failed_count": len(chunks),
        }
    except requests.RequestException as e:
        return {
            "success": False,
            "message": f"Could not reach memory service: {e}",
            "document_id": document_id,
            "registered_count": 0,
            "indexed_count": 0,
            "failed_count": len(chunks),
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Unexpected document chunk sync error: {e}",
            "document_id": document_id,
            "registered_count": 0,
            "indexed_count": 0,
            "failed_count": len(chunks),
        }