import os
from dotenv import load_dotenv
from pathlib import Path
import requests

env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(env_path)

# Memory service base URL
MEMORY_URL = os.getenv("MEMORY_URL")


def memory_health_check() -> bool:
    """
    Check whether memory service is alive.
    """
    try:
        response = requests.get(f"{MEMORY_URL}/health", timeout=5)
        response.raise_for_status()
        data = response.json()
        return data.get("status") == "ok"
    except Exception:
        return False


def retrieve_memory(query: str, limit: int = 5) -> list:
    """
    Retrieve semantically relevant memories before asking the agent.
    """
    try:
        response = requests.post(
            f"{MEMORY_URL}/memory/retrieve",
            json={
                "query": query,
                "limit": limit
            },
            timeout=10
        )
        response.raise_for_status()
        return response.json().get("memories", [])
    except Exception:
        return []


def save_memory(category: str, key: str, value: str) -> dict:
    """
    Save a structured memory item to memory service.
    """
    try:
        response = requests.post(
            f"{MEMORY_URL}/memory/save",
            json={
                "category": category,
                "key": key,
                "value": value
            },
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"success": False, "message": str(e)}


def log_action(action: str, action_type: str, success: bool = True) -> dict:
    """
    Log an action that the desktop actually executed.
    """
    try:
        response = requests.post(
            f"{MEMORY_URL}/memory/action",
            json={
                "action": action,
                "type": action_type,
                "success": success
            },
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"success": False, "message": str(e)}


def get_action_history(limit: int = 10) -> list:
    """
    Retrieve recent action history.
    Useful for debugging and safety checks.
    """
    try:
        response = requests.get(
            f"{MEMORY_URL}/memory/history",
            params={"limit": limit},
            timeout=10
        )
        response.raise_for_status()
        return response.json().get("history", [])
    except Exception:
        return []