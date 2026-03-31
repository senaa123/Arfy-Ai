import os
import requests

MEMORY_SERVICE_URL = os.getenv("MEMORY_SERVICE_URL", "http://127.0.0.1:8002")

def save_memory(category:  str, key: str, value:  str) -> dict:
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