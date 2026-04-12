from __future__ import annotations

import re
from collections import Counter
from typing import Dict, List

from memory_service.schemas import ChatMessage


def build_transcript(messages: List[ChatMessage]) -> str:
    """
    Convert session messages into a clean transcript block.
    """
    if not messages:
        return ""

    lines = []
    for msg in messages:
        role = "User" if msg.role == "user" else "Arfy"
        lines.append(f"{role}: {msg.content}")

    return "\n".join(lines)


def summarize_messages(messages: List[ChatMessage], max_items: int = 4) -> str:
    """
    Deterministic summary generator.
    """
    if not messages:
        return "Empty session."

    user_lines: List[str] = []
    assistant_lines: List[str] = []

    for msg in messages:
        clean_text = " ".join(msg.content.split())
        if not clean_text:
            continue

        if msg.role == "user":
            if clean_text not in user_lines:
                user_lines.append(clean_text)
        else:
            if clean_text not in assistant_lines:
                assistant_lines.append(clean_text)

    first_time = messages[0].timestamp
    last_time = messages[-1].timestamp

    summary_parts = [
        f"Session window: {first_time} to {last_time}.",
    ]

    if user_lines:
        summary_parts.append("Main user requests:")
        for item in user_lines[:max_items]:
            summary_parts.append(f"- {item}")

    if assistant_lines:
        summary_parts.append("Main assistant responses/actions:")
        for item in assistant_lines[:max_items]:
            summary_parts.append(f"- {item}")

    return "\n".join(summary_parts)


def extract_preference_candidates(messages: List[ChatMessage]) -> List[Dict[str, str]]:
    """
    Extract stable preference candidates from the ended session.

    We keep this deterministic for now.
    These are only candidate memories, not hard assumptions.
    """
    if not messages:
        return []

    user_texts = [
        " ".join(msg.content.split()).strip()
        for msg in messages
        if msg.role == "user" and msg.content.strip()
    ]

    candidates: List[Dict[str, str]] = []

    # -------------------------
    # Explicit favorite app
    # -------------------------
    for text in user_texts:
        lower = text.lower()
        match = re.search(r"\bmy favorite app is\s+([a-zA-Z0-9 _-]+)", lower)
        if match:
            app_name = match.group(1).strip().title()
            candidates.append({
                "category": "preferences",
                "key": "favorite_app",
                "value": app_name,
            })
            break

    # -------------------------
    # Repeated app preference heuristic
    # If the user mentions one app often in a session,
    # treat it as a candidate preferred app.
    # -------------------------
    known_apps = ["spotify", "chrome", "notepad", "calculator", "vscode", "explorer"]
    app_counter = Counter()

    for text in user_texts:
        lower = text.lower()
        for app in known_apps:
            if app in lower:
                app_counter[app] += 1

    if app_counter:
        app_name, count = app_counter.most_common(1)[0]
        if count >= 2 and not any(c["key"] == "favorite_app" for c in candidates):
            candidates.append({
                "category": "preferences",
                "key": "preferred_app_candidate",
                "value": app_name.title(),
            })

    # -------------------------
    # Favorite music / artist / song
    # -------------------------
    for text in user_texts:
        lower = text.lower()

        song_match = re.search(r"\bmy favorite song is\s+(.+)", lower)
        if song_match:
            candidates.append({
                "category": "preferences",
                "key": "favorite_song",
                "value": song_match.group(1).strip().title(),
            })
            break

    for text in user_texts:
        lower = text.lower()

        artist_match = re.search(r"\bmy favorite artist is\s+(.+)", lower)
        if artist_match:
            candidates.append({
                "category": "preferences",
                "key": "favorite_artist",
                "value": artist_match.group(1).strip().title(),
            })
            break

    music_counter = Counter()

    for text in user_texts:
        lower = text.lower()
        if any(word in lower for word in ["song", "music", "playlist", "spotify", "artist"]):
            music_counter["music_interest"] += 1

    if music_counter.get("music_interest", 0) >= 2:
        if not any(c["key"] in {"favorite_song", "favorite_artist"} for c in candidates):
            candidates.append({
                "category": "preferences",
                "key": "music_interest_candidate",
                "value": "User showed repeated music-related interest in this session.",
            })

    # -------------------------
    # Usual location
    # -------------------------
    for text in user_texts:
        lower = text.lower()

        match = re.search(r"\b(?:i live in|i am in|i'm in|my location is|i stay in)\s+([a-zA-Z\s]+)", lower)
        if match:
            location = match.group(1).strip().title()
            candidates.append({
                "category": "preferences",
                "key": "usual_location",
                "value": location,
            })
            break

    # -------------------------
    # Preferred response style
    # -------------------------
    for text in user_texts:
        lower = text.lower()

        if any(phrase in lower for phrase in [
            "keep it short",
            "short answer",
            "be concise",
            "make it short",
            "shorttt",
        ]):
            candidates.append({
                "category": "preferences",
                "key": "preferred_response_style",
                "value": "concise",
            })
            break

        if any(phrase in lower for phrase in [
            "explain more",
            "in detail",
            "more detail",
            "step by step",
            "line by line",
        ]):
            candidates.append({
                "category": "preferences",
                "key": "preferred_response_style",
                "value": "detailed",
            })
            break

    # Remove duplicates by (key, value)
    seen = set()
    unique_candidates = []

    for item in candidates:
        pair = (item["key"], item["value"])
        if pair not in seen:
            seen.add(pair)
            unique_candidates.append(item)

    return unique_candidates