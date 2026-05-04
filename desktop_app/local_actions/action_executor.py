from ..clients.spotify_client import play_playlist, play_song
from ..integrations.app_control import close_app, open_app
from ..integrations.spotify_desktop import ensure_spotify_ready


SAFE_ACTIONS = {
    "open_app",
    "close_app",
    "spotify_play_song",
    "spotify_play_playlist",
}


def execute_action(action: dict) -> tuple[bool, str]:
    """
    Execute a safe action returned by the agent service.

    Returns:
    (success, message)
    """
    if not action:
        return False, "No action provided."

    action_type = action.get("type")
    payload = action.get("payload", {})

    if action_type not in SAFE_ACTIONS:
        return False, f"Blocked unknown action: {action_type}"

    try:
        if action_type == "open_app":
            success = open_app(payload.get("app_name", ""))
            return success, "App opened." if success else "Failed to open app."

        if action_type == "close_app":
            success = close_app(payload.get("app_name", ""))
            return success, "App closed." if success else "Failed to close app."

        if action_type == "spotify_play_song":
            ready, ready_message = ensure_spotify_ready()
            if not ready:
                return False, ready_message

            result = play_song(payload.get("song_name", ""))
            success = "playing" in result.lower()
            return success, result

        if action_type == "spotify_play_playlist":
            ready, ready_message = ensure_spotify_ready()
            if not ready:
                return False, ready_message

            result = play_playlist(payload.get("playlist_name", ""))
            success = "playing" in result.lower()
            return success, result

        return False, "Unknown action."

    except Exception as e:
        return False, f"execute_action error: {e}"
