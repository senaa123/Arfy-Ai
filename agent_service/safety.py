from typing import Dict

#Allowed agent actions
SAFE_ACTIONS = {
    "open_app",
    "close_app",
    "spotify_play_playlist",
    "spotify_play_song",
    "speak_only",
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
    # Validate app  action payloead
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
