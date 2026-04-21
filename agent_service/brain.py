from typing import List

from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

from agent_service.config import GROQ_API_KEY, GROQ_MODEL_MAIN, GROQ_MODEL_ROUTER
from agent_service.prompts import SYSTEM_PROMPT, ROUTER_PROMPT, FINAL_RESPONSE_PROMPT
from agent_service.models import MemoryItem, RouteDecision

# Router model: fast intent classification
router_llm = ChatGroq(
    api_key=GROQ_API_KEY,
    model=GROQ_MODEL_ROUTER,
    temperature=0
)

# Main model: response generation
main_llm = ChatGroq(
    api_key=GROQ_API_KEY,
    model=GROQ_MODEL_MAIN,
    temperature=0.2
)


def format_memories(memories: List[MemoryItem]) -> str:
    """
    Turn memory objects into readable text.
    """
    if not memories:
        return "No relevant memories."

    return "\n".join(
        f"- [{m.category}] {m.key}: {m.value}" for m in memories
    )


def llm_route(user_text: str, memories: List[MemoryItem]) -> RouteDecision:
    """
    Uses the router LLM to classify the user request into structured intent.
    """
    memory_text = format_memories(memories)

    messages = [
        SystemMessage(content=ROUTER_PROMPT),
        HumanMessage(
            content=(
                f"User message: {user_text}\n\n"
                f"Relevant memories:\n{memory_text}\n\n"
                "Return JSON with keys: intent, confidence, extracted_data, tool_name, action.\n"
                "If action is not needed, action should be null."
            )
        )
    ]

    raw = router_llm.invoke(messages)
    return parse_route_decision(user_text, raw.content, memories)


def parse_route_decision(user_text: str, raw_text: str, memories: List[MemoryItem]) -> RouteDecision:
    """
    Simple fallback parser for the router output.
    """
    router_text = raw_text.lower()
    user_lower = user_text.lower()
    combined = f"{router_text}\n{user_lower}"

    # Weather
    if "weather" in combined:
        location = extract_location_from_text_or_memory(user_text, memories)
        return RouteDecision(
            intent="weather",
            confidence=0.9,
            extracted_data={"location": location},
            tool_name="weather"
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
                    "payload": {"playlist_name": playlist_name}
                }
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
                    "payload": {"song_name": song_name}
                }
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
                    "payload": {"app_name": app_name}
                }
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
                    "payload": {"app_name": app_name}
                }
            )

    # Search
    if "search" in combined:
        return RouteDecision(
            intent="search",
            confidence=0.85,
            extracted_data={"query": user_text},
            tool_name="search"
        )

    # Remember
    if "remember" in combined:
        return RouteDecision(
            intent="remember",
            confidence=0.85,
            extracted_data={
                "category": "facts",
                "key": "user_note",
                "value": user_text
            },
            tool_name="memory_save"
        )

    return RouteDecision(
        intent="chat",
        confidence=0.7
    )


def build_final_response(
    user_text: str,
    intent: str,
    tool_used: str,
    tool_result: dict,
    action: dict,
    memories: List[MemoryItem]
) -> str:
    """
    Generates the final spoken reply using the main LLM.
    """
    memory_text = format_memories(memories)

    prompt = FINAL_RESPONSE_PROMPT.format(
        user_text=user_text,
        intent=intent,
        tool_used=tool_used,
        tool_result=tool_result,
        action=action,
        memories=memory_text
    )

    response = main_llm.invoke([
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=prompt)
    ])
    return response.content.strip()


def extract_location_from_text_or_memory(text: str, memories: List[MemoryItem]) -> str:
    """
    Priority:
    1. explicit location in text
    2. current location in memory
    3. home_town/city in memory
    4. fallback default
    """
    lower = text.lower()

    for marker in [" in ", " at "]:
        if marker in lower:
            part = lower.split(marker, 1)[1].strip()
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
    Extract song name from user text.
    """
    lower = text.lower().strip()
    cleaned = lower.replace("spotify", "").strip()

    prefixes = [
        "play ",
        "can you play ",
        "please play ",
    ]

    for prefix in prefixes:
        if cleaned.startswith(prefix):
            value = cleaned[len(prefix):].strip()
            if value and "playlist" not in value:
                return value

    return cleaned if cleaned else ""