from typing import List

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq

from agent_service.config import GROQ_API_KEY, GROQ_MODEL_MAIN, GROQ_MODEL_ROUTER
from agent_service.models import MemoryItem, RouteDecision, SessionMessage
from agent_service.prompts import (
    FINAL_RESPONSE_PROMPT,
    ROUTER_PROMPT,
    SYSTEM_PROMPT,
    WEATHER_RESPONSE_PROMPT,
)

# Fast router model
router_llm = ChatGroq(
    api_key=GROQ_API_KEY,
    model=GROQ_MODEL_ROUTER,
    temperature=0,
)

# Main response model
main_llm = ChatGroq(
    api_key=GROQ_API_KEY,
    model=GROQ_MODEL_MAIN,
    temperature=0.2,
)


def format_memories(memories: List[MemoryItem]) -> str:
    """
    Format retrieved long-term memories into readable text.
    """
    if not memories:
        return "No relevant memories."

    return "\n".join(
        f"- [{m.category}] {m.key}: {m.value}"
        for m in memories
    )


def format_history(history: List[SessionMessage]) -> str:
    """
    Format the live short-term chat history for the LLM.
    """
    if not history:
        return "No recent session history."

    return "\n".join(
        f"- {msg.role.title()}: {msg.content}"
        for msg in history
    )


def is_confirmation_text(text: str) -> bool:
    """
    Return True for clear confirmation messages.
    """
    lower = text.lower().strip()

    confirmations = {
        "yes",
        "yes please",
        "do that",
        "okay",
        "ok",
        "sure",
        "go ahead",
        "please do",
        "yes do that",
    }
    return lower in confirmations


def is_rejection_text(text: str) -> bool:
    """
    Return True for clear rejection/cancel messages.
    """
    lower = text.lower().strip()

    rejections = {
        "no",
        "no thanks",
        "cancel",
        "not now",
        "don't",
        "do not",
    }
    return lower in rejections


def looks_like_weather_request(text: str) -> bool:
    """
    Detect real weather-related requests from the CURRENT user text only.
    """
    lower = text.lower().strip()

    weather_terms = [
        "weather",
        "forecast",
        "temperature",
        "rain",
        "rainy",
        "sunny",
        "cloudy",
        "humidity",
        "windy",
        "storm",
    ]

    time_terms = [
        "today",
        "tomorrow",
        "yesterday",
        "this week",
        "last week",
        "next week",
        "this weekend",
        "last weekend",
        "next monday",
        "last monday",
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
    ]

    # Direct weather words
    if any(term in lower for term in weather_terms):
        return True

    # Forecast-style questions only if they mention weather-like meaning
    if ("how will" in lower or "what will" in lower or "how was" in lower or "what was" in lower):
        if any(term in lower for term in time_terms):
            return True

    return False


def llm_route(
    user_text: str,
    memories: List[MemoryItem],
    history: List[SessionMessage],
) -> RouteDecision:
    """
    Ask the router model to classify the request.
    """
    memory_text = format_memories(memories)
    history_text = format_history(history)

    messages = [
        SystemMessage(content=ROUTER_PROMPT),
        HumanMessage(
            content=(
                f"User message: {user_text}\n\n"
                f"Recent session history:\n{history_text}\n\n"
                f"Relevant memories:\n{memory_text}\n\n"
                "Return JSON with keys: intent, confidence, extracted_data, tool_name, action.\n"
                "If action is not needed, action should be null."
            )
        ),
    ]

    raw = router_llm.invoke(messages)
    return parse_route_decision(user_text, raw.content, memories)


def parse_route_decision(
    user_text: str,
    raw_text: str,
    memories: List[MemoryItem],
) -> RouteDecision:
    """
    Fallback rule-based parser for the router output.
    """
    router_text = raw_text.lower()
    user_lower = user_text.lower()
    combined = f"{router_text}\n{user_lower}"

# Weather / forecast / past weather / week/weekend weather
# IMPORTANT:
# Only use the CURRENT user text here.
# Do NOT use router_text/history text for weather detection,
# otherwise unrelated follow-ups can get forced into the weather route.
    if looks_like_weather_request(user_text):
        location = extract_location_from_text_or_memory(user_text, memories)
        return RouteDecision(
            intent="weather",
            confidence=0.9,
            extracted_data={"location": location},
            tool_name="weather",
        )

    # Spotify playlist
    if (
        "spotify_play_playlist" in combined
        or ("playlist" in user_lower and "play" in user_lower)
    ):
        playlist_name = extract_playlist_name(user_text)
        if playlist_name:
            return RouteDecision(
                intent="spotify_play_playlist",
                confidence=0.92,
                action={
                    "type": "spotify_play_playlist",
                    "payload": {"playlist_name": playlist_name},
                },
            )

    # Spotify song
    if (
        "spotify_play_song" in combined
        or (
            "play" in user_lower
            and "playlist" not in user_lower
            and any(word in user_lower for word in ["song", "music", "spotify", "play "])
        )
    ):
        song_name = extract_song_name(user_text)
        if song_name:
            return RouteDecision(
                intent="spotify_play_song",
                confidence=0.88,
                action={
                    "type": "spotify_play_song",
                    "payload": {"song_name": song_name},
                },
            )

    # Open app
    if "open_app" in combined or "open app" in combined or "open " in user_lower:
        app_name = extract_app_name(user_text)
        if app_name:
            return RouteDecision(
                intent="open_app",
                confidence=0.9,
                action={
                    "type": "open_app",
                    "payload": {"app_name": app_name},
                },
            )

    # Close app
    if "close_app" in combined or "close app" in combined or "close " in user_lower:
        app_name = extract_app_name(user_text)
        if app_name:
            return RouteDecision(
                intent="close_app",
                confidence=0.9,
                action={
                    "type": "close_app",
                    "payload": {"app_name": app_name},
                },
            )

    # Search
    if "search" in combined:
        return RouteDecision(
            intent="search",
            confidence=0.85,
            extracted_data={"query": user_text},
            tool_name="search",
        )

    # Remember
    if "remember" in combined:
        return RouteDecision(
            intent="remember",
            confidence=0.85,
            extracted_data={
                "category": "facts",
                "key": "user_note",
                "value": user_text,
            },
            tool_name="memory_save",
        )

    return RouteDecision(
        intent="chat",
        confidence=0.7,
    )


def build_final_response(
    user_text: str,
    intent: str,
    tool_used: str,
    tool_result: dict,
    action: dict | None,
    memories: List[MemoryItem],
    history: List[SessionMessage],
) -> str:
    """
    Generate the final assistant response.
    """
    if tool_used == "weather" and isinstance(tool_result, dict):
        return build_weather_response(user_text, tool_result)

    memory_text = format_memories(memories)
    history_text = format_history(history)

    prompt = FINAL_RESPONSE_PROMPT.format(
        user_text=user_text,
        intent=intent,
        tool_used=tool_used,
        tool_result=tool_result,
        action=action,
        memories=memory_text,
        history=history_text,
    )

    response = main_llm.invoke([
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=prompt),
    ])
    return response.content.strip()


def build_weather_response(user_text: str, tool_result: dict) -> str:
    """
    Let the LLM turn structured weather data into a natural weather report.
    Falls back to the tool-generated message if the model is unavailable.
    """
    fallback = str(tool_result.get("message", "")).strip()
    if not tool_result.get("success", False):
        return fallback or "I couldn't build the weather report right now."

    prompt = WEATHER_RESPONSE_PROMPT.format(
        user_text=user_text,
        tool_result=format_weather_tool_result(tool_result),
    )

    try:
        response = main_llm.invoke([
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ])
        content = response.content.strip()
        if content:
            return content
    except Exception:  # noqa: BLE001
        pass

    return fallback or "I couldn't build the weather report right now."


def format_weather_tool_result(tool_result: dict) -> str:
    """
    Build a compact, explicit weather brief for the LLM so it can sound
    natural without hallucinating from a huge raw payload.
    """
    lines = []

    for key in [
        "kind",
        "location",
        "target_date",
        "start_date",
        "end_date",
        "description",
        "temperature_c",
        "average_temp_c",
        "high_temp_c",
        "low_temp_c",
        "feels_like_c",
        "humidity_percent",
        "wind_speed_kmh",
        "wind_gusts_kmh",
        "rain_mm",
        "precipitation_mm",
        "rain_chance_percent",
        "rain_coverage_percent",
        "sunrise",
        "sunset",
    ]:
        value = tool_result.get(key)
        if value is not None:
            lines.append(f"{key}: {value}")

    hourly_rows = tool_result.get("hourly_breakdown") or []
    if hourly_rows:
        lines.append("hourly_breakdown:")
        for row in hourly_rows[:6]:
            row_parts = []
            for key in [
                "clock",
                "description",
                "temperature_c",
                "feels_like_c",
                "humidity_percent",
                "wind_speed_kmh",
                "rain_mm",
                "precipitation_mm",
                "rain_chance_percent",
            ]:
                value = row.get(key)
                if value is not None:
                    row_parts.append(f"{key}={value}")
            if row_parts:
                lines.append("- " + ", ".join(row_parts))

    per_day = tool_result.get("per_day") or []
    if per_day:
        lines.append("per_day:")
        for item in per_day[:7]:
            day_parts = [f"date={item.get('date')}"]
            weather_items = item.get("weather") or []
            if weather_items and isinstance(weather_items[0], dict):
                description = weather_items[0].get("description")
                if description:
                    day_parts.append(f"description={description}")

            for section, keys in [
                ("temp", ["day", "max", "min"]),
                ("feels_like", ["day", "max", "min"]),
                ("humidity", ["mean"]),
                ("wind", ["mean_kmh", "gusts_max_kmh"]),
                ("precipitation", ["rain_mm", "chance_max_percent", "coverage_percent"]),
                ("astronomy", ["sunrise", "sunset"]),
            ]:
                data = item.get(section) or {}
                for key in keys:
                    value = data.get(key)
                    if value is not None:
                        day_parts.append(f"{section}.{key}={value}")

            lines.append("- " + ", ".join(day_parts))

    if fallback := str(tool_result.get("message", "")).strip():
        lines.append(f"tool_message: {fallback}")

    return "\n".join(lines)


def extract_location_from_text_or_memory(text: str, memories: List[MemoryItem]) -> str:
    """
    Priority:
    1. explicit location in text
    2. current location in memory
    3. home town / city in memory
    4. fallback default
    """
    lower = text.lower()

    for marker in [" in ", " at "]:
        if marker in lower:
            part = lower.split(marker, 1)[1].strip()

            # Clean trailing punctuation
            part = part.strip(" ?.,!")

            if part:
                return part.title()

    for mem in memories:
        key = mem.key.lower().strip()
        if key in {"current_location", "location"}:
            return str(mem.value).strip().title()

    for mem in memories:
        key = mem.key.lower().strip()
        if key in {"home_town", "hometown", "city", "home_city"}:
            return str(mem.value).strip().title()

    return "Malabe"


def extract_app_name(text: str) -> str:
    """
    Extract known app names from text.
    """
    lower = text.lower()
    known_apps = ["chrome", "spotify", "notepad", "calculator", "vscode", "explorer"]

    for app in known_apps:
        if app in lower:
            return app
    return ""


def extract_playlist_name(text: str) -> str:
    """
    Extract playlist name from user text.
    """
    lower = text.lower().strip()

    if "playlist" not in lower:
        return ""

    cleaned = lower.replace("spotify", "").strip()

    if "play my " in cleaned and " playlist" in cleaned:
        return cleaned.split("play my ", 1)[1].split(" playlist", 1)[0].strip()

    if "play " in cleaned and " playlist" in cleaned:
        return cleaned.split("play ", 1)[1].split(" playlist", 1)[0].strip()

    if "my playlist" in cleaned:
        return "my"

    return "playlist"


def extract_song_name(text: str) -> str:
    """
    Extract the song name from user text.
    """
    lower = text.lower().strip()
    cleaned = lower.replace("spotify", "").replace("song", "").replace("music", "").strip()

    if cleaned.startswith("play "):
        return cleaned[5:].strip()

    return ""
