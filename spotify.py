import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os
from dotenv import load_dotenv
import subprocess
import time
load_dotenv()

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=os.getenv("SPOTIFY_CLIENT_ID"),
    client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
    redirect_uri="http://127.0.0.1:8888/callback",
    scope="user-modify-playback-state user-read-playback-state playlist-read-private"
))

def ensure_spotify_open():
    subprocess.Popen(r'"C:\Users\ASUS\AppData\Roaming\Spotify\Spotify.exe"', shell=True)
    time.sleep(8) 


def play_song(query):
    ensure_spotify_open()
    try:
        # search for the song
        results = sp.search(q=query, limit=1, type="track")
        tracks = results["tracks"]["items"]

        if not tracks:
            return f"Couldn't find {query}"

        track = tracks[0]
        track_uri = track["uri"]
        track_name = track["name"]
        artist = track["artists"][0]["name"]

        
        devices = sp.devices()
        if not devices["devices"]:
            return "No active Spotify device found."

        device_id = devices["devices"][0]["id"]
        sp.start_playback(device_id=device_id, uris=[track_uri])
        return f"Playing {track_name} by {artist}"

    except Exception as e:
        print(f"Spotify error: {e}")
        return "Couldn't play the song, make sure Spotify is open."

def pause_music():
    try:
        sp.pause_playback()
        return "Music paused."
    except Exception as e:
        return "Couldn't pause."
    
def resume_music():
    try:
        sp.start_playback()
        return "Resuming music."
    except Exception as e:
        return "Couldn't resume music."

def next_song():
    try:
        sp.next_track()
        return "Skipping to next song."
    except Exception as e:
        return "Couldn't skip."
def previous_song():
    try:
        sp.previous_track()
        return "Going back to previous song."
    except Exception as e:
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
        
        devices = sp.devices()
        if not devices["devices"]:
            return "No active Spotify device found."

        device_id = devices["devices"][0]["id"]
        sp.start_playback(device_id=device_id, context_uri=matched["uri"])
        return f"Playing {matched['name']} playlist!"
    
    except Exception as e:
        print(f"Spotify error: {e}")
        return "Couldn't play the playlist, make sure Spotify is open."