from typing import Dict, List
from datetime import datetime, timezone

SAFE_ACTIONS = {
    "open_app",
    "close_app",
    "spotify_play_playlist",
    "spotify_play_song",
    "service_health_check",
}

ALLOWED_APPS = {
    "chrome",
    "spotify",
    "notepad",
    "calculator",
    "vscode",
    "explorer",
}

ALLOWED_SERVICES = {
    "memory",
    "agent",
}


def is_safe_action(action_type: str) -> bool:
    """
    Returns True if the action is allowed.
    """
    return action_type in SAFE_ACTIONS


def validate_payload(action_type: str, payload: Dict) -> bool:
    """
    Validate the action payload before the desktop app ever sees it.
    """
    if action_type in {"open_app", "close_app"}:
        app_name = str(payload.get("app_name", "")).strip().lower()
        return app_name in ALLOWED_APPS

    if action_type == "spotify_play_playlist":
        playlist_name = str(payload.get("playlist_name", "")).strip()
        return 0 < len(playlist_name) < 200

    if action_type == "spotify_play_song":
        song_name = str(payload.get("song_name", "")).strip()
        return 0 < len(song_name) < 200

    if action_type == "service_health_check":
        service_name = str(payload.get("service_name", "")).strip().lower()
        return service_name in ALLOWED_SERVICES

    return False


def seconds_ago(iso_timestamp: str) -> float:
    """
    Convert an ISO timestamp into age in seconds.
    """
    try:
        ts = datetime.fromisoformat(iso_timestamp.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        return (now - ts).total_seconds()
    except Exception:
        return 999999


def is_repeated_action(
    action_type: str,
    history: List[dict],
    threshold_count: int = 3,
    window_seconds: int = 60,
) -> bool:
    """
    Checks if the same action happened too many times recently.
    """
    recent_same = []

    for item in history:
        if item.get("action_type") == action_type or item.get("type") == action_type:
            if seconds_ago(item.get("timestamp", "")) < window_seconds:
                recent_same.append(item)

    return len(recent_same) >= threshold_count