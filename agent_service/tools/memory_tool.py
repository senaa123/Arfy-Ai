import os
from pathlib import Path
from dotenv import load_dotenv
import requests

env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(env_path)
MEMORY_SERVICE_URL = os.getenv("MEMORY_SERVICE_URL")

def save_memory(category:  str, key: str, value: str) -> dict:
    """
    Send a request to memory service to save a memory item.
    """

    try: 
        response = requests.post(
            f"{MEMORY_SERVICE_URL}/memory/save",
            json={
                "category": category,
                "key": key,
                "value": value
            },
            timeout=10
        )

        response.raise_for_status()

        return {
            "success": True,
            "message":  f"Saved memory: {key} = {value}"
        }
    
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to save memory: {e}"
        }
    
def get_recent_action_history(limit: int = 10) -> list:
        """
        Used for repeat-guard safety check
        """
        try:
            response = requests.get(
                f"{MEMORY_SERVICE_URL}/memory/history",
                params={"limit": limit},
                timeout=10
            )

            response.raise_for_status()
            data = response.json()
            return data.get("history", [])
            
        except Exception:
            return[]
    
    