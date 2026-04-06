# decides what the user probably wants.
import re
from typing import List, Optional
from models import RouteDecision, AgentAction, MemoryItem


def classify_request(text: str, memories: Optional[List[MemoryItem]] = None) -> RouteDecision:
    """
    Very simple rule base router.
    It checks the user text and decides:
    - is it weather?
    - is it opening an app?
    - is it remembering something?
    - is it general chat?
    """
    if memories is None:
        memories = []

    user_text = text.strip().lower()

    #Remembering something
    if user_text.startswith("remember") or  "remember that" in user_text:
        value = user_text.replace("remember that", "").replace("remember", "").strip()

        return RouteDecision(
            intent="remember",
            confidence=0.95,
            tool_name="memory_save",
            extracted_data={
                "category": "facts",
                "key": "user_note",
                "value": value
            }
        )
    # Weather

    if "weather" in user_text or "temperature" in user_text:
        location = extract_location_from_text_or_memory(user_text, memories)

        return RouteDecision(
            intent="weather",
            confidence=0.95,
            tool_name="weather",
            extracted_data={"location": location}
        )
    
    # search

    if user_text.startswith("search ") or user_text.startswith("look up "):
        query = user_text.replace("search", "", 1).replace("look up", "", 1).strip()

        return RouteDecision(
            intent="search",
            confidence=0.92,
            tool_name="search",
            extracted_data={"query": query}
        )
    
    # open app
    
    if user_text.startswith("open "):
        app_name = user_text.replace("open", "", 1).strip()

        return RouteDecision(
            intent="open_app",
            confidence=0.96,
            action=AgentAction(
                type="open_app",
                payload={"app_name": app_name}
            )
        )
    
    # close app
    
    if user_text.startswith("close "):
        app_name = user_text.replace("close", "", 1).strip()

        return RouteDecision(
            intent="close_app",
            confidence=0.96,
            action=AgentAction(
                type="close_app",
                payload={"app_name": app_name}
            )
        )
    
    #Spotify playlist
    if "play " in user_text and "playlist" in user_text:
        playlist_name = user_text.replace("play", "", 1).replace("playlist", "").strip()

        return RouteDecision(
            intent="spotify_play",
            confidence=0.92,
            action=AgentAction(
                type="spotify_play_playlist",
                payload={"playlist_name": playlist_name}
            )
        )
    
    #Spotify song
    if user_text.startswith("play "):
        song_name = user_text.replace("play", "", 1).strip()

        return RouteDecision(
            intent="spotify_play",
            confidence=0.88,
            action=AgentAction(
                type="spotify_play_song",
                payload={"song_name": song_name}
            )
        )
    
    # default fallback
    
    return RouteDecision(
        intent="chat",
        confidence=0.65,
        action=None,
        tool_name=None,
        extracted_data={}
    )

def extract_location_from_text_or_memory(text: str, memories: List[MemoryItem]) -> str:
    """
    Get location in this order:

    1. Explicit location from the user's text
       Example: 'weather in Colombo'
    2. Current location from memory
       Example key: current_location or location
    3. Home/home town/city from memory
    4. Default fallback
    """

    #Explicit location in user text
    match = re.search(r"(?:in|at)\s+([a-zA-Z\s]+)", text.lower())
    if match:
        return match.group(1).strip().title()
    
    #If no location
    for mem in memories:
        key = mem.key.lower().strip()

        # Prefer current location first
        if key in {"current_location", "location"}:
            return str(mem.value).strip().title()
    
    #If current location unable to find
    for mem in memories:
        key = mem.key.lower().strip()

        if key in {"home_town", "hometown", "city", "home_city"}:
            return str(mem.value).strip().title()
    
    #Final fallback
    return "Ratnapura"