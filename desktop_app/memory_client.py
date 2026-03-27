import requests
from typing import Optional

MEMORY_URL = "http://localhost:8002"
TIMEOUT = 10

def save_memory(category: str, key: str, value: str) -> bool:
    """
    Save a single memory to the Memory Service.
    Memory is organized into categories
    """
    try:
        response = requests.post(
            f"{MEMORY_URL}/memory/save",
            json={
                "category": category,
                "key": key,
                "value": value
            },
            timeout=TIMEOUT
        )
        return response.status_code == 200
    
    except Exception as e:
        print(f"Memmory save error: {e}")
        return False

def retrive_memory(query: str, limit: int = 3) -> list:
     """
    Find memories related to a query using semantic search.
    This is the smart part — uses Qdrant to find similar memories
    even if the exact words don't match.

    Example:
    retrieve_memory("what music does senaa like", limit=3)
    → finds: music_genre=rock, music_playlist=vibe
    
    Even though query doesn't say "rock" or "vibe" exactly,
    Qdrant finds them because the meaning is similar.
    """
     try:
         response = requests.post(
             f"{MEMORY_URL}/memory/retrieve",
             json={
                 "query": query, 
                 "limit": limit #max no of memories to return
             },
             timeout=TIMEOUT
         )
         if response.status_code==200:
             return response.json().get("memories", [])
         return []
     except Exception as e:
         print(f"memory retrieve error: {e}")
         return False

def get_all_memory() -> dict:
    """
    Load ALL memories as a dictionary.
    Used when full context is needed — like building system prompt.
    """
    try:
        response = requests.post(
            f"{MEMORY_URL}/memory/all",
            timeout=TIMEOUT
        )
        if response.status_code==200:
            return response.json()
        return {}
    except Exception as e:
        print(f"Memory load error: {e}")
        return {}
    
def log_action(action: str, action_type: str, success: bool) -> bool:
    """
    Record an action that was executed.
    This builds up Arfy's action history so she can:
    - remember what she did recently
    - avoid repeating the same action
    - learn usage patterns
    """
    try:
        response = requests.post(
            f"{MEMORY_URL}/memory/action",
            json={
                "action": action,
                "type": action_type, #category: spotify,app, system
                "success": success

            },
            timeout=TIMEOUT
        )
        return response.status_code==200
    except Exception as e:
        print(f"Action log error: {e}")
        return False

def get_action_history(limit: int = 10) -> list:
    """
    Get the most recent actions Arfy performed.
    Used by safety guards to check if same action is repeating.
    """
    try:
        response = requests.get(
            f"{MEMORY_URL}/memory/history",
            params={"limit": limit},  # how many recent actions to fetch
            timeout=TIMEOUT
        )
        if response.status_code==200:
            return response.son().get("history", [])
        return []
    except Exception as e:
        print(f"History featch error: {e}")
        return []
    
def is_memory_alive() -> bool:
    """
    Quick check if Memory Service is running.
    Called on startup alongside agent check.
    """
    try:
        response = requests.get(
            f"{MEMORY_URL}/health",
            timeout=3
        )
        return response.status_code==200
    except:
        return False



    
             
    




