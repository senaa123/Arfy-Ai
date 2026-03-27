from apps import open_app, close_app
from spotify import (
    play_song, play_playlist,
    pause_music, resume_music,
    next_song, previous_song
)
from memory_client import log_action

# ─────────────────────────────────────────
# SAFETY — only these actions are allowed
# agent cannot ask desktop to do anything
# outside this list
# ─────────────────────────────────────────

SAFE_ACTIONS = [
    "speak_only",          # just speak, no OS action needed
    "open_app",            # open an application
    "close_app",           # close an application
    "spotify_play_song",   # play a specific song
    "spotify_play_playlist", # play a playlist
    "spotify_pause",       # pause music
    "spotify_resume",      # resume music
    "spotify_next",        # skip to next song
    "spotify_previous",    # go to previous song
]

# ─────────────────────────────────────────
# REPEAT GUARD
# tracks the last action to prevent
# the same action firing multiple times
# ─────────────────────────────────────────

_last_action = {"type":None, "count":0}

def _is_repeated(action_type: str, max_repeats:int = 3) -> bool:
    """
    Check if the same action is being called too many times in a row.
    """
    if _last_action["type"]== action_type:
        # same action increase counter
        _last_action["count"] += 1
        if _last_action["count"]>max_repeats:
            print(f"[Safety] Blocked repeated action: {action_type}")
            return True # block toomany repeats
    else:
        # different action — reset counter
        _last_action["type"] = action_type
        _last_action["count"] = 1
    
    return False

def execute_action(action: dict) -> str:
    """
    Execute a structured action returned by the Agent Service.

    Steps:
    1. Check if action is in SAFE_ACTIONS list
    2. Check if action is being repeated too many times
    3. Execute the action locally
    4. Log the action to Memory Service
    5. Return result string

    The agent DECIDES what to do.
    This file EXECUTES it locally.
    Clear separation — agent never touches the OS directly.
    """

    if not action:
        return "No action"
    
    action_type = action.get("type", "")
    payload = action.get("payload", {}) #axtra data needed for the acction

    # SAFETY CHECK 1 — block unknown actions 
    # if agent returns something not in our safe list
    # we refuse to execute it — security measure
    if action_type not in SAFE_ACTIONS:
        print(f"[Safety] Blocked unknown action: {action_type}")
        return f"Blocked: {action_type}"
    
    # SAFETY CHECK 2 — block repeated actions 
    # prevents agent from calling same action in a loop
    if _is_repeated(action_type):
        return "Action skipped — repeated too many times"
    
    #Execute

    try:
        if action_type=="apeak_only":
             # agent just wants to respond with text
            return "OK"
        elif action_type == "open_app":
            # get app name from payload
            app_name = payload.get("app_name", "")
            success = open_app(app_name)
            # log what happened to memory service
            log_action(f"opened {app_name}", "app", success)
            return f"Opened {app_name}" if success else f"Failed to open {app_name}"

        elif action_type == "close_app":
            app_name = payload.get("app_name", "")
            success = close_app(app_name)
            log_action(f"closed {app_name}", "app", success)
            return f"Closed {app_name}" if success else f"Failed to close {app_name}"

        elif action_type == "spotify_play_song":
            # get song name from payload and play it
            song = payload.get("song_name", "")
            result = play_song(song)
            log_action(f"played song {song}", "spotify", True)
            return result

        elif action_type == "spotify_play_playlist":
            playlist = payload.get("playlist_name", "")
            result = play_playlist(playlist)
            log_action(f"played playlist {playlist}", "spotify", True)
            return result

        elif action_type == "spotify_pause":
            result = pause_music()
            log_action("paused music", "spotify", True)
            return result

        elif action_type == "spotify_resume":
            result = resume_music()
            log_action("resumed music", "spotify", True)
            return result

        elif action_type == "spotify_next":
            result = next_song()
            log_action("skipped to next song", "spotify", True)
            return result

        elif action_type == "spotify_previous":
            result = previous_song()
            log_action("went to previous song", "spotify", True)
            return result
    except Exception as e:

        print(f"Action execution error: {e}")
        # log the failure to memory service
        log_action(f"failed {action_type}", "error", False)
        return f"Error executing {action_type}"
    
    return "Done"
        
