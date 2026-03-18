import re
from apps import open_app, close_app
from spotify import (play_song, play_playlist, pause_music,
                     resume_music, next_song, previous_song)
from weather import (
    extract_location,
    extract_target_day,
    get_day_forecast,
    get_forecast,
    get_tomorrow_forecast,
    get_weather,
    is_forecast_question,
)


# KEYWORD MAPS

OPEN_KEYWORDS = ["open", "launch", "start", "run", "load"]
CLOSE_KEYWORDS = ["close", "shut", "exit", "kill", "terminate", "quit"]

PAUSE_KEYWORDS = ["pause", "stop music", "hold music", "mute music"]
RESUME_KEYWORDS = ["resume", "continue", "unpause", "play again"]
NEXT_KEYWORDS = ["next song", "next track", "skip", "skip song"]
PREV_KEYWORDS = ["previous song", "previous track", "go back", "last song"]

PLAY_SONG_KEYWORDS = ["play song", "play the song", "play track"]
PLAY_PLAYLIST_KEYWORDS = ["play playlist", "play the playlist"]
PLAY_KEYWORDS = ["play"]
WEATHER_KEYWORDS = ["weather", "temperature", "forecast", "rain", "sunny", "humid"]

KNOWN_APPS = [
    "chrome", "spotify", "notepad", "calculator",
    "vscode", "vs code", "file explorer", "explorer"
]


# HELPERS


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


def format_weather_response(question: str):
    """Handle weather locally so common questions don't rely on LLM tool calling."""
    if not contains(question, WEATHER_KEYWORDS):
        return None

    location = extract_location(question)
    if not location:
        return "I don't know your location yet. Tell me where you are."

    if is_forecast_question(question):
        target = extract_target_day(question)

        if target == "tomorrow":
            data = get_tomorrow_forecast(location)
            if not data:
                return "Couldn't fetch tomorrow's forecast."
            return (
                f"Tomorrow in {data['city']}: {data['min_temp']}°C to {data['max_temp']}°C, "
                f"{data['description']}, humidity {data['humidity']}%."
            )

        if target == "week":
            forecasts = get_forecast(location, days=5)
            if not forecasts:
                return "Couldn't fetch the weekly forecast."
            lines = [
                f"{day['day']}: {day['min_temp']}°C to {day['max_temp']}°C, {day['description']}"
                for day in forecasts
            ]
            return f"5-day forecast for {forecasts[0]['city']}:\n" + "\n".join(lines)

        if target == "weekend":
            forecasts = get_forecast(location, days=5)
            if not forecasts:
                return "Couldn't fetch the weekend forecast."
            weekend = [day for day in forecasts if day["day"] in ["Saturday", "Sunday"]]
            if not weekend:
                return "I couldn't find weekend data in the next few days."
            lines = [
                f"{day['day']}: {day['min_temp']}°C to {day['max_temp']}°C, {day['description']}"
                for day in weekend
            ]
            return f"Weekend forecast for {forecasts[0]['city']}:\n" + "\n".join(lines)

        if target and target != "tonight":
            data = get_day_forecast(location, target)
            if data:
                return (
                    f"{data['day']} in {data['city']}: {data['min_temp']}°C to {data['max_temp']}°C, "
                    f"{data['description']}, humidity {data['humidity']}%."
                )

    data = get_weather(location)
    if not data:
        return f"Couldn't fetch weather for {location}."

    return (
        f"Weather in {data['city']}, {data['country']}: "
        f"{data['temp']}°C, feels like {data['feels_like']}°C, "
        f"{data['description']}, humidity {data['humidity']}%, wind {data['wind']} m/s."
    )

# ROUTER

def route_intent(text: str):
    """
    Try to handle command locally.
    Returns response string if handled.
    Returns None if should go to LLM.
    """
    t = clean(text)

    # close app
    if contains(t, CLOSE_KEYWORDS):
        app = find_app(t)
        if app:
            if close_app(app):
                return f"Closing {app}."
            return f"Couldn't close {app}."

    # open app
    if contains(t, OPEN_KEYWORDS):
        app = find_app(t)
        if app:
            if open_app(app):
                return f"Opening {app}."
            return f"Couldn't open {app}."

    # weather
    weather_response = format_weather_response(t)
    if weather_response:
        return weather_response

    # pause music
    if contains(t, PAUSE_KEYWORDS):
        return pause_music()

    # resume music
    if contains(t, RESUME_KEYWORDS):
        return resume_music()

    # next song
    if contains(t, NEXT_KEYWORDS):
        return next_song()

    # previous song
    if contains(t, PREV_KEYWORDS):
        return previous_song()

    # play playlist
    if contains(t, PLAY_PLAYLIST_KEYWORDS):
        name = extract_after(t, PLAY_PLAYLIST_KEYWORDS)
        if name:
            return play_playlist(name)

    # PLAY SONG (explicit)
    if contains(t, PLAY_SONG_KEYWORDS):
        name = extract_after(t, PLAY_SONG_KEYWORDS)
        if name:
            return play_song(name)

    # PLAY (generic) 
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

    
    return None
