import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os
from dotenv import load_dotenv
import subprocess
import time
import psutil
load_dotenv()

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=os.getenv("SPOTIFY_CLIENT_ID"),
    client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
    redirect_uri="http://127.0.0.1:8888/callback",
    scope="user-modify-playback-state user-read-playback-state playlist-read-private"
))

def is_spotify_running():
    for proc in psutil.process_iter(['name']):
        try:
            if proc.info['name'] == 'Spotify.exe':
                return True
        except:
            pass
    return False

def wait_for_spotify_api(timeout=30):
    """Wait until Spotify API recognizes an active device"""
    print("Waiting for Spotify to be ready...")
    start = time.time()
    while time.time() - start < timeout:
        try:
            devices = sp.devices()
            if devices["devices"]:
                print(f"Spotify ready! Device: {devices['devices'][0]['name']}")
                return True
        except Exception as e:
            print(f"Waiting... {e}")
        time.sleep(2)
    print("Spotify API timeout — no device found")
    return False

def ensure_spotify_open():
    if is_spotify_running():
        print("Spotify already running.")
        wait_for_spotify_api(timeout=15)
        return
    print("Opening Spotify...")
    subprocess.Popen(r'"C:\Users\ASUS\AppData\Roaming\Spotify\Spotify.exe"', shell=True)
    time.sleep(5)
    wait_for_spotify_api(timeout=30)

def get_active_device(retries=2, wait=2):
    """Try to get active device with retries"""
    for i in range(retries):
        try:
            devices = sp.devices()
            if devices["devices"]:
                print(f"Device found: {devices['devices'][0]['name']}")
                return devices["devices"][0]["id"]
            print(f"No device found, retry {i+1}/{retries}, waiting {wait}s...")
            time.sleep(wait)
        except Exception as e:
            print(f"Device check error: {e}")
            time.sleep(wait)
    return None

def play_song(query):
    ensure_spotify_open()
    try:
        results = sp.search(q=query, limit=1, type="track")
        tracks = results["tracks"]["items"]

        if not tracks:
            return f"Couldn't find {query}"

        track = tracks[0]
        track_uri = track["uri"]
        track_name = track["name"]
        artist = track["artists"][0]["name"]

        device_id = get_active_device(retries=1, wait=2)
        if not device_id:
            return "Spotify opened but no active device found. Please click play in Spotify once manually."

        sp.start_playback(device_id=device_id, uris=[track_uri])
        return f"Playing {track_name} by {artist}"

    except Exception as e:
        print(f"Spotify error: {e}")
        return "Couldn't play the song."

def pause_music():
    try:
        sp.pause_playback()
        return "Music paused."
    except Exception as e:
        print(f"Pause error: {e}")
        return "Couldn't pause. Make sure Spotify is playing."

def resume_music():
    try:
        device_id = get_active_device(retries=2, wait=2)
        if not device_id:
            return "No active Spotify device found."
        sp.start_playback(device_id=device_id)
        return "Resuming music."
    except Exception as e:
        print(f"Resume error: {e}")
        return "Couldn't resume music."

def next_song():
    try:
        sp.next_track()
        return "Skipping to next song."
    except Exception as e:
        print(f"Next song error: {e}")
        return "Couldn't skip."

def previous_song():
    try:
        sp.previous_track()
        return "Going back to previous song."
    except Exception as e:
        print(f"Previous song error: {e}")
        return "Couldn't go back."

def play_playlist(playlist_name):
    ensure_spotify_open()
    try:
        playlists = sp.current_user_playlists(limit=50)

        matched = None
        for playlist in playlists["items"]:
            if playlist_name.lower() in playlist["name"].lower():
                matched = playlist
                break

        if not matched:
            return f"Couldn't find playlist {playlist_name}"

        device_id = get_active_device(retries=1, wait=2)
        if not device_id:
            return "Spotify opened but no active device found. Please click play in Spotify once manually."

        sp.start_playback(device_id=device_id, context_uri=matched["uri"])
        return f"Playing {matched['name']} playlist!"

    except Exception as e:
        print(f"Spotify error: {e}")
        return "Couldn't play the playlist."