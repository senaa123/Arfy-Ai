import os
import requests
from pathlib import Path
from dotenv import load_dotenv
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(env_path)

# Agent service base URL
AGENT_URL = os.getenv("AGENT_URL")

# Request timeout in seconds
TIMEOUT = 30

def agent_health_check() -> bool:
    """
    Check whether the agent service is running.
    """
    try:
        response = requests.get(f"{AGENT_URL}/health", timeout=5)
        response.raise_for_status()
        data = response.json()
        return data.get("status") == "ok"
    except Exception:
        return False


def ask_agent(text: str, session_id: str, memories: list | None = None) -> dict:
    """
    Send user text and relevant memories to the agent service.

    Expected response:
    {
        "response": "...",
        "action": {...} or None,
        "confidence": 0.95,
        "tool_used": "weather",
        "session_id": "senaa_01"
    }
    """
    if memories is None:
        memories = []

    try:
        response = requests.post(
            f"{AGENT_URL}/agent/ask",
            json={
                "text": text,
                "session_id": session_id,
                "memories": memories
            },
            timeout=TIMEOUT
        )
        response.raise_for_status()
        return response.json()

    except requests.Timeout:
        return {
            "response": "The agent service took too long to respond.",
            "action": None,
            "confidence": 0.0,
            "tool_used": None,
            "session_id": session_id
        }

    except requests.RequestException as e:
        return {
            "response": f"Could not reach the agent service: {e}",
            "action": None,
            "confidence": 0.0,
            "tool_used": None,
            "session_id": session_id
        }

    except Exception as e:
        return {
            "response": f"Unexpected agent error: {e}",
            "action": None,
            "confidence": 0.0,
            "tool_used": None,
            "session_id": session_id
        }


def reset_agent_session(session_id: str) -> dict:
    """
    Clear short-term session history inside agent service.
    """
    try:
        response = requests.post(
            f"{AGENT_URL}/agent/reset",
            params={"session_id": session_id},
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "session_id": session_id
        }