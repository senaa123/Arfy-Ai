import requests
from typing import Optional
from memory_client import retrieve_memory

AGENT_URL = "http://localhost:8001" #Agent addres
TIMEOUT = 30 # Time wait for the agent response

def ask_agent(text: str, session_id: str ="senaa_01")-> Optional[dict]:
    try:
        # get relevant memories
        memories = retrieve_memory(text, limit=3)

        #request
        response = requests.post(
            f"{AGENT_URL}/agent/ask",
            json={
                "text": text,
                "session_id": session_id,
                "memories": memories
            },
            timeout=TIMEOUT
        )
        if response.status_code == 200:
            return response.json() #convert response
        else:
            print(f"Agent error: {response.status_code}")
            return None
    except requests.exceptions.ConnectionError:
        print("Agent service not reachable — is it running?")
        return None
    except requests.exceptions.Timeout:
        print("Agent service timed out")
        return None
    except Exception as e:
        print(f"Agent client error: {e}")
        return None
    
def reset_session(session_id: str = "senaa_01") -> bool:
    #clear conversation history
    try:
        response = requests.post(
            f"{AGENT_URL}/agent/rest",
            json={"session_id":session_id},
            timeout=5
        )
        return response.status_code == 200
    except:
        return False
    
def is_agent_alive()->bool:
    """
    Check if Agent Service is running.
    Called on startup so Arfy can warn if agent is offline.
    
    Returns True if alive, False if not reachable.
    """
    try:
        response = requests.get(
            f"{AGENT_URL}/health",
            timeout=3 #short time out
        )
        return response.status_code == 200
    except:
        return False