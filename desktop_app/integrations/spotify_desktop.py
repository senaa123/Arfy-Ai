import os
import subprocess
import time
from pathlib import Path

import psutil
from dotenv import load_dotenv

from clients.spotify_client import wait_for_spotify_api

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(env_path)

SPOTIFY_EXE = os.getenv(
    "SPOTIFY_EXE",
    r"C:\Users\ASUS\AppData\Roaming\Spotify\Spotify.exe",
)


def is_spotify_running() -> bool:
    """
    Return True when the local Spotify desktop process is already running.
    """
    for proc in psutil.process_iter(["name"]):
        try:
            if proc.info["name"] == "Spotify.exe":
                return True
        except Exception:
            continue

    return False


def _open_spotify_process() -> None:
    """
    Launch the local Spotify desktop app in detached mode.
    """
    if not Path(SPOTIFY_EXE).exists():
        raise FileNotFoundError(f"Spotify executable not found: {SPOTIFY_EXE}")

    detached = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP

    subprocess.Popen(
        SPOTIFY_EXE,
        shell=False,
        creationflags=detached,
        close_fds=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def ensure_spotify_ready(timeout: int = 30) -> tuple[bool, str]:
    """
    Ensure the local Spotify desktop app is open before API playback calls.

    Behavior is intentionally close to the pre-split flow:
    - open Spotify if needed
    - give the desktop app a moment to come up
    - best-effort wait for the Web API to see a device
    - do not block playback forever if API readiness lags behind app startup
    """
    try:
        if not is_spotify_running():
            _open_spotify_process()
            time.sleep(5)

        api_ready = wait_for_spotify_api(timeout=timeout)
        if api_ready:
            return True, "Spotify is ready."

        return True, (
            "Spotify is open, but no active device was detected yet. "
            "Playback will still be attempted."
        )

    except Exception as e:
        return False, f"Could not prepare Spotify desktop: {e}"
