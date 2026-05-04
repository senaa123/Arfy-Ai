# agent_service/brain.py

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
    Format a list of memory items into readable text.

    Phase 3C improvement:
    - document chunk hits become easier for the LLM to understand
    """
    if not memories:
        return "None."

    lines = []
    for m in memories:
        category = m.get("category") if isinstance(m, dict) else m.category
        key = m.get("key") if isinstance(m, dict) else m.key
        value = m.get("value") if isinstance(m, dict) else m.value
        source_layer = m.get("source_layer") if isinstance(m, dict) else m.source_layer
        memory_kind = m.get("memory_kind") if isinstance(m, dict) else m.memory_kind
        file_name = m.get("file_name") if isinstance(m, dict) else m.file_name
        chunk_index = m.get("chunk_index") if isinstance(m, dict) else m.chunk_index

        if memory_kind == "document_chunk" and file_name is not None and chunk_index is not None:
            line = f"- [document_chunk] {file_name} chunk {chunk_index}: {value}"
        else:
            line = f"- [{category}] {key}: {value}"

        if source_layer:
            line += f" (source_layer={source_layer})"

        lines.append(line)

    return "\n".join(lines)


def format_memory_context(memory_context: dict | None) -> dict:
    """
    Convert the richer memory context into LLM-friendly text blocks.

    Why this exists:
    - the agent should now understand exact vs document vs semantic memory
    - this makes routing and final replies more grounded
    """
    memory_context = memory_context or {}

    exact = memory_context.get("exact", [])
    documents = memory_context.get("documents", [])
    semantic = memory_context.get("semantic", [])
    merged = memory_context.get("merged", [])

    return {
        "exact_memories": format_memories(exact),
        "document_memories": format_memories(documents),
        "semantic_memories": format_memories(semantic),
        "merged_memories": format_memories(merged),
    }


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

    if any(term in lower for term in weather_terms):
        return True

    if ("how will" in lower or "what will" in lower or "how was" in lower or "what was" in lower):
        if any(term in lower for term in time_terms):
            return True

    return False

#Document upload
def looks_like_document_upload_request(text: str) -> bool:
    """
    Detect requests where the desktop should open a file picker and send the
    selected file to document_service.
    """
    lower = text.lower().strip()

    direct_phrases = [
        "upload a document",
        "upload document",
        "upload a file",
        "ingest a document",
        "ingest document",
        "ingest a file",
        "import a document",
        "add a document",
    ]
    if any(phrase in lower for phrase in direct_phrases):
        return True
    
    upload_terms = ["upload", "ingest", "import", "add"]
    document_terms = ["document", "file", "pdf", "docx", "csv", "image", "text file"]

    return any(term in lower for term in upload_terms) and any(
        term in lower for term in document_terms
    )

# rag
def _candidate_document_ids(memories: List[MemoryItem]) -> list[str]:
    """
    Collect stable document ids from retrieved memory items.

    We keep this helper simple and deterministic so the router can hand likely
    document_ids to rag_service without inventing new state.
    """
    ordered: list[str] = []
    seen: set[str] = set()

    for memory in memories:
        doc_id = memory.get("document_id") if isinstance(memory, dict) else memory.document_id
        if not doc_id:
            continue

        doc_id = str(doc_id).strip()
        if doc_id and doc_id not in seen:
            seen.add(doc_id)
            ordered.append(doc_id)

    return ordered


def looks_like_document_question(text: str, memories: List[MemoryItem]) -> bool:
    """
    Detect questions that should go to rag_service.

    Why this exists:
    - document-grounded answering should route to the dedicated RAG capability
    - we want a deterministic fallback even if the router LLM is unavailable
    """
    lower = text.lower().strip()
    document_ids = _candidate_document_ids(memories)

    # Strong explicit document/file references.
    direct_terms = [
        "document",
        "pdf",
        "file",
        "note",
        "notes",
        "slide",
        "slides",
        "lecture",
        "report",
        "paper",
        "chapter",
    ]

    question_terms = [
        "summarize",
        "summary",
        "explain",
        "what does",
        "what is in",
        "what's in",
        "tell me about",
    ]

    if any(term in lower for term in direct_terms) and any(term in lower for term in question_terms):
        return True

    # Follow-up style document questions become plausible when we already have
    # known document ids in retrieved memory context.
    if document_ids:
        followup_terms = [
            "summarize this",
            "explain this",
            "what does it say",
            "what's it about",
            "what is it about",
            "what does this say",
        ]
        if any(term in lower for term in followup_terms):
            return True

    return False


def llm_route(
    user_text: str,
    memories: List[MemoryItem],
    history: List[SessionMessage],
    memory_context: dict | None = None,
) -> RouteDecision:
    """
    Ask the router model to classify the request.

    Phase 3B change:
    - pass richer memory context, not just merged memory
    """
    memory_blocks = format_memory_context(memory_context)
    history_text = format_history(history)

    messages = [
        SystemMessage(content=ROUTER_PROMPT),
        HumanMessage(
            content=(
                f"User message: {user_text}\n\n"
                f"Recent session history:\n{history_text}\n\n"
                f"Exact memory:\n{memory_blocks['exact_memories']}\n\n"
                f"Document memory:\n{memory_blocks['document_memories']}\n\n"
                f"Semantic memory:\n{memory_blocks['semantic_memories']}\n\n"
                "Return JSON with keys: intent, confidence, extracted_data, tool_name, action.\n"
                "If action is not needed, action should be null."
            )
        ),
    ]

    try:
        raw = router_llm.invoke(messages)
        return parse_route_decision(user_text, raw.content, memories)
    except Exception:
        # Keep the agent alive when the external router model is unavailable.
        return parse_route_decision(user_text, "", memories)


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

    # Weather
    if looks_like_weather_request(user_text):
        location = extract_location_from_text_or_memory(user_text, memories)
        return RouteDecision(
            intent="weather",
            confidence=0.9,
            extracted_data={"location": location},
            tool_name="weather",
        )

    # Document-grounded Q&A
    if "document_qa" in combined or "rag_ask" in combined or looks_like_document_question(user_text, memories):
        return RouteDecision(
            intent="document_qa",
            confidence=0.9,
            extracted_data={
                "question": user_text,
                "document_ids": _candidate_document_ids(memories),
            },
            tool_name="rag_ask",
        )
    
        # Document upload / ingest
    if looks_like_document_upload_request(user_text):
        return RouteDecision(
            intent="document_upload",
            confidence=0.94,
            action={
                "type": "pick_and_ingest_document",
                "payload": {
                    "enable_ocr": True,
                    "persist": True,
                    "pdf_ocr_min_chars": 30,
                    "chunk_size": 1200,
                    "chunk_overlap": 200,
                    "index_chunks_to_vector": True,
                },
            },
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
    if "search" in user_lower or "look up" in user_lower or "find on the web" in user_lower:
        return RouteDecision(
            intent="search",
            confidence=0.88,
            extracted_data={"query": user_text},
            tool_name="search",
        )

    # Remember
    if "remember" in user_lower or "remember that" in user_lower:
        value = (
            user_text.replace("remember that", "")
            .replace("remember", "")
            .strip()
        )
        return RouteDecision(
            intent="remember",
            confidence=0.95,
            tool_name="memory_save",
            extracted_data={
                "category": "profile_fact",
                "key": "user_note",
                "value": value,
            },
        )

    # Default chat
    return RouteDecision(
        intent="chat",
        confidence=0.6,
        extracted_data={},
        action=None,
        tool_name=None,
    )


def build_final_response(
    user_text: str,
    intent: str,
    tool_used: str,
    tool_result: dict,
    action: dict | None,
    memories: List[MemoryItem],
    history: List[SessionMessage],
    memory_context: dict | None = None,
) -> str:
    """
    Generate the final assistant response.

    Phase 3B change:
    - richer memory context is available to the final response prompt
    - exact/document memory can now be surfaced more clearly

    Phase 4 RAG hook:
    - when rag_service already returned a grounded answer, return it directly
      instead of paraphrasing it through the main chat model
    """
    if tool_used == "weather" and isinstance(tool_result, dict):
        return build_weather_response(user_text, tool_result)

    if tool_used == "memory_save" and isinstance(tool_result, dict):
        return build_memory_save_response(tool_result)

    if tool_used == "rag_ask" and isinstance(tool_result, dict):
        grounded_answer = str(tool_result.get("answer", "")).strip()
        grounded_message = str(tool_result.get("message", "")).strip()

        if grounded_answer:
            return grounded_answer
        if grounded_message:
            return grounded_message
        return "I couldn't find enough grounded evidence to answer that reliably."

    if action:
        return build_action_response(action)

    if isinstance(tool_result, dict) and tool_result.get("success") is False:
        message = str(tool_result.get("message", "")).strip()
        if message:
            return message

    memory_blocks = format_memory_context(memory_context)

    trimmed_history = history[-4:] if history else []
    history_text = format_history(trimmed_history)

    prompt = FINAL_RESPONSE_PROMPT.format(
        user_text=user_text,
        history=history_text,
        intent=intent,
        tool_used=tool_used,
        tool_result=tool_result,
        action=action,
        exact_memories=memory_blocks["exact_memories"],
        document_memories=memory_blocks["document_memories"],
        semantic_memories=memory_blocks["semantic_memories"],
        merged_memories=memory_blocks["merged_memories"],
    )

    try:
        response = main_llm.invoke([
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ])
        return response.content.strip()
    except Exception:
        fallback_message = _fallback_response_text(intent, tool_result)
        if fallback_message:
            return fallback_message

        return (
            "I couldn't reach my language model just now, but I'm still here and "
            "can keep helping with memory, documents, search, weather, and actions."
        )


def build_memory_save_response(tool_result: dict) -> str:
    """
    Deterministic confirmation after saving memory.
    """
    success = tool_result.get("success", False)
    message = str(tool_result.get("message", "")).strip()

    if success:
        return message or "Okay, I remembered that."

    return message or "I couldn't save that memory."


def build_action_response(action: dict) -> str:
    """
    Build deterministic spoken text for desktop actions.
    """
    action_type = action.get("type", "")
    payload = action.get("payload", {}) or {}

    if action_type == "open_app":
        app_name = payload.get("app_name", "that app")
        return f"I'm opening {app_name} for you."

    if action_type == "close_app":
        app_name = payload.get("app_name", "that app")
        return f"I'm closing {app_name} for you."

    if action_type == "spotify_play_song":
        song_name = payload.get("song_name", "that song")
        return f"I'm going to play {song_name} on Spotify."

    if action_type == "spotify_play_playlist":
        playlist_name = payload.get("playlist_name", "that playlist")
        return f"I'm going to play the {playlist_name} playlist on Spotify."
    
    if action_type == "pick_and_ingest_document":
        return (
            "I'm opening the file picker. Choose the document you want me to "
            "send to the document service."
        )

    return "Okay, I'm doing that now."


def build_weather_response(user_text: str, tool_result: dict) -> str:
    """
    Generate a richer natural weather summary.
    """
    message = str(tool_result.get("message", "")).strip()

    # Weather tool responses already contain a readable summary, so keep that as
    # the graceful fallback when the tool or LLM path is unavailable.
    if tool_result.get("success") is False:
        return message or "I couldn't get the weather right now."

    prompt = WEATHER_RESPONSE_PROMPT.format(
        user_text=user_text,
        tool_result=tool_result,
    )

    try:
        response = main_llm.invoke([
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ])
        return response.content.strip()
    except Exception:
        return message or "I couldn't turn that weather result into a reply just now."


def _fallback_response_text(intent: str, tool_result: dict) -> str:
    """
    Reuse direct tool output whenever the final-response LLM is unavailable.
    """
    if isinstance(tool_result, dict):
        message = str(tool_result.get("message", "")).strip()
        if message:
            return message

    if intent == "chat":
        return "I'm here with you. I couldn't generate a full reply just now."

    return ""


def extract_location_from_text_or_memory(user_text: str, memories: List[MemoryItem]) -> str:
    """
    Try to find a weather location from text first, then memory.
    """
    lower = user_text.lower()

    if " in " in lower:
        candidate = user_text.lower().split(" in ", 1)[1].strip(" ?.,!")
        if candidate:
            return candidate.title()

    for memory in memories:
        if memory.key in {"usual_location", "location", "preferred_city"}:
            if str(memory.value).strip():
                return str(memory.value).strip()

    return "Malabe"


def extract_app_name(user_text: str) -> str | None:
    """
    Extract app name from simple open/close commands.
    """
    lower = user_text.lower().strip()

    for prefix in ["open ", "close ", "open app ", "close app "]:
        if lower.startswith(prefix):
            return user_text[len(prefix):].strip(" .!?")

    return None


def extract_song_name(user_text: str) -> str | None:
    """
    Extract song name from simple play requests.
    """
    lower = user_text.lower().strip()

    if lower.startswith("play "):
        return user_text[5:].strip(" .!?")

    return None


def extract_playlist_name(user_text: str) -> str | None:
    """
    Extract playlist name from simple playlist requests.
    """
    lower = user_text.lower().strip()

    if lower.startswith("play ") and " playlist" in lower:
        name = lower.replace("play ", "", 1).replace(" playlist", "").strip(" .!?")
        return name.title()

    return None