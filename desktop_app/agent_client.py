import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(env_path)

AGENT_URL = os.getenv("AGENT_URL")
TIMEOUT = 30
HEALTH_TIMEOUT = 2
HEALTH_RETRIES = 3


def agent_health_check() -> bool:
    """
    Check whether the agent service is running.
    """
    for attempt in range(HEALTH_RETRIES):
        try:
            response = requests.get(f"{AGENT_URL}/health", timeout=HEALTH_TIMEOUT)
            response.raise_for_status()
            data = response.json()
            return data.get("status") == "ok"
        except Exception:
            if attempt < HEALTH_RETRIES - 1:
                time.sleep(0.5)

    return False


def ask_agent(text: str, session_id: str, memories: list | None = None) -> dict:
    """
    Send user text and retrieved memories to the agent service.
    """
    if memories is None:
        memories = []

    try:
        response = requests.post(
            f"{AGENT_URL}/agent/ask",
            json={
                "text": text,
                "session_id": session_id,
                "memories": memories,
            },
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        return response.json()

    except requests.Timeout:
        return {
            "response": "The agent service took too long to respond.",
            "action": None,
            "confidence": 0.0,
            "tool_used": None,
            "session_id": session_id,
        }

    except requests.RequestException as e:
        return {
            "response": f"Could not reach the agent service: {e}",
            "action": None,
            "confidence": 0.0,
            "tool_used": None,
            "session_id": session_id,
        }

    except Exception as e:
        return {
            "response": f"Unexpected agent error: {e}",
            "action": None,
            "confidence": 0.0,
            "tool_used": None,
            "session_id": session_id,
        }


def reset_agent_session(session_id: str) -> dict:
    """
    Force-reset a session in the agent service.
    """
    try:
        response = requests.post(
            f"{AGENT_URL}/agent/reset",
            params={"session_id": session_id},
            timeout=10,
        )
        response.raise_for_status()
        return response.json()

    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "session_id": session_id,
        }


def end_agent_session(session_id: str) -> dict:
    """
    Gracefully end a live session.

    This triggers:
    - final archive
    - session summary generation
    - RAM cleanup inside agent service
    """
    try:
        response = requests.post(
            f"{AGENT_URL}/agent/session/end",
            params={"session_id": session_id},
            timeout=20,
        )
        response.raise_for_status()
        return response.json()

    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "session_id": session_id,
        }
