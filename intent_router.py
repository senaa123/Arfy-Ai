import re
from apps import open_app, close_app
from spotify import (play_song, play_playlist, pause_music,
                     resume_music, next_song, previous_song)

# ─────────────────────────────────────────
# KEYWORD MAPS
# ─────────────────────────────────────────

OPEN_KEYWORDS = ["open", "launch", "start", "run", "load"]
CLOSE_KEYWORDS = ["close", "shut", "exit", "kill", "terminate", "quit"]

PAUSE_KEYWORDS = ["pause", "stop music", "hold music", "mute music"]
RESUME_KEYWORDS = ["resume", "continue", "unpause", "play again"]
NEXT_KEYWORDS = ["next song", "next track", "skip", "skip song"]
PREV_KEYWORDS = ["previous song", "previous track", "go back", "last song"]

PLAY_SONG_KEYWORDS = ["play song", "play the song", "play track"]
PLAY_PLAYLIST_KEYWORDS = ["play playlist", "play the playlist"]
PLAY_KEYWORDS = ["play"]

KNOWN_APPS = [
    "chrome", "spotify", "notepad", "calculator",
    "vscode", "vs code", "file explorer", "explorer"
]

# ─────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────

def clean(text):
    return text.lower().strip()

def contains(text, keywords):
    return any(kw in text for kw in keywords)

def extract_after(text, keywords):
    """Extract words after a keyword"""
    for kw in sorted(keywords, key=len, reverse=True):
        if kw in text:
            after = text.split(kw, 1)[-1].strip()
            # clean punctuation
            after = re.sub(r'[^\w\s]', '', after).strip()
            if after:
                return after
    return None

def find_app(text):
    """Find app name in text"""
    for app in KNOWN_APPS:
        if app in text:
            return app
    return None

# ─────────────────────────────────────────
# ROUTER
# ─────────────────────────────────────────

def route_intent(text: str):
    """
    Try to handle command locally.
    Returns response string if handled.
    Returns None if should go to LLM.
    """
    t = clean(text)

    # ── CLOSE APP ──────────────────────────
    if contains(t, CLOSE_KEYWORDS):
        app = find_app(t)
        if app:
            if close_app(app):
                return f"Closing {app}."
            return f"Couldn't close {app}."

    # ── OPEN APP ───────────────────────────
    if contains(t, OPEN_KEYWORDS):
        app = find_app(t)
        if app:
            if open_app(app):
                return f"Opening {app}."
            return f"Couldn't open {app}."

    # ── PAUSE MUSIC ────────────────────────
    if contains(t, PAUSE_KEYWORDS):
        return pause_music()

    # ── RESUME MUSIC ───────────────────────
    if contains(t, RESUME_KEYWORDS):
        return resume_music()

    # ── NEXT SONG ──────────────────────────
    if contains(t, NEXT_KEYWORDS):
        return next_song()

    # ── PREVIOUS SONG ──────────────────────
    if contains(t, PREV_KEYWORDS):
        return previous_song()

    # ── PLAY PLAYLIST ──────────────────────
    if contains(t, PLAY_PLAYLIST_KEYWORDS):
        name = extract_after(t, PLAY_PLAYLIST_KEYWORDS)
        if name:
            return play_playlist(name)

    # ── PLAY SONG (explicit) ───────────────
    if contains(t, PLAY_SONG_KEYWORDS):
        name = extract_after(t, PLAY_SONG_KEYWORDS)
        if name:
            return play_song(name)

    # ── PLAY (generic) ─────────────────────
    if contains(t, PLAY_KEYWORDS):
        # check if it's a playlist
        if "playlist" in t:
            name = extract_after(t, ["playlist"])
            if name:
                return play_playlist(name)
        # otherwise treat as song
        name = extract_after(t, PLAY_KEYWORDS)
        if name:
            return play_song(name)

    # ── NO MATCH → send to LLM ─────────────
    return None