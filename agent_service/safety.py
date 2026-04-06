from typing import Dict, List
from datetime import datetime, timezone

#Allowed agent actions
SAFE_ACTIONS = {
    "open_app",
    "close_app",
    "spotify_play_playlist",
    "spotify_play_song"
}

#Allowed apps
ALLOWED_APPS = {
    "chrome",
    "spotify",
    "notepad",
    "calculator",
    "vscode",
    "explorer",
}

def is_safe_action(action_type: str) -> bool:
    # Returns true if the action allowed
    return action_type in SAFE_ACTIONS

def validate_payload(action_type: str, payload: Dict) -> bool:
    """
    Validate the action payload before the desktop app ever sees it.
    """
    
    if action_type in {"open_app", "close_app"}:
        app_name = str(payload.get("app_name", "")).strip().lower()
        return app_name in ALLOWED_APPS
    
    # Validate spotify playlist name
    if action_type == "spotify_play_playlist":
        playlist_name = str(payload.get("playlist_name", "")).strip()
        return 0 < len(playlist_name) < 200
    
    # Validate spotify song name
    if action_type == "spotify_play_song":
        song_name = str(payload.get("song_name", "")).strip()
        return 0 < len(song_name) < 200
    
    #Speeak_only needs no special payload rules for now
    if action_type == "speak_only":
        return True
    
    return False

def seconds_ago(iso_timestamp: str) -> float:
    """
    Validate the action payload before the desktop app ever sees it.
    """

    try:
        ts = datetime.fromisoformat(iso_timestamp.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        return (now - ts).total_seconds()
    except Exception:
        return 999999
    
def is_repeated_action(action_type: str, history: List[dict], threshold_count: int = 3, window_seconds: int = 60) -> bool:
    """
    Checks if the same action happened too many times recently.
    This helps block loops like open/close/open/close.
    """
    recent_same = []

    for item in history:
        if item.get("action_type") == action_type or item.get("type") == action_type:
            if seconds_ago(item.get("timestamp", "")) < window_seconds:
                recent_same.append(item)

    return len(recent_same) >= threshold_count

