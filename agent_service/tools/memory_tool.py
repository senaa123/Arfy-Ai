import os
from pathlib import Path
from typing import List

import requests
from dotenv import load_dotenv

from agent_service.models import SessionMessage

# Load env from agent_service/.env
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(env_path)

MEMORY_SERVICE_URL = os.getenv("MEMORY_SERVICE_URL")


def save_memory(category: str, key: str, value: str) -> dict:
    """
    Save a structured durable memory item.
    """
    try:
        response = requests.post(
            f"{MEMORY_SERVICE_URL}/memory/save",
            json={
                "category": category,
                "key": key,
                "value": value,
            },
            timeout=10,
        )
        response.raise_for_status()

        return {
            "success": True,
            "message": f"Saved memory: {key} = {value}",
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to save memory: {e}",
        }


def get_recent_action_history(limit: int = 10) -> list:
    """
    Return recent executed actions for safety repeat-guard checks.
    """
    try:
        response = requests.get(
            f"{MEMORY_SERVICE_URL}/memory/history",
            params={"limit": limit},
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("history", [])

    except Exception:
        return []


def archive_session_chunk(
    session_id: str,
    messages: List[SessionMessage],
    session_started_at: str | None = None,
    chunk_reason: str = "overflow",
) -> dict:
    """
    Archive overflowed short-term messages into vector memory.
    """
    if not messages:
        return {"success": True, "message": "No overflow messages to archive."}

    try:
        response = requests.post(
            f"{MEMORY_SERVICE_URL}/session/archive/chunk",
            json={
                "session_id": session_id,
                "messages": [m.model_dump() for m in messages],
                "session_started_at": session_started_at,
                "chunk_reason": chunk_reason,
            },
            timeout=15,
        )
        response.raise_for_status()
        return response.json()

    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to archive session chunk: {e}",
        }


def finalize_session_archive(
    session_id: str,
    messages: List[SessionMessage],
    session_started_at: str | None = None,
    session_ended_at: str | None = None,
) -> dict:
    """
    Finalize the current session:
    - archive remaining transcript
    - create a session summary
    - save summary to SQLite + vector memory
    """
    try:
        response = requests.post(
            f"{MEMORY_SERVICE_URL}/session/archive/finalize",
            json={
                "session_id": session_id,
                "messages": [m.model_dump() for m in messages],
                "session_started_at": session_started_at,
                "session_ended_at": session_ended_at,
            },
            timeout=20,
        )
        response.raise_for_status()
        return response.json()

    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to finalize session archive: {e}",
        }