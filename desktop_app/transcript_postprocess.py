from __future__ import annotations

import re


def apply_corrections(text: str) -> str:
    """
    Apply small custom ASR corrections for names/apps commonly used in Arfy.

    Why:
    - Whisper may hear 'arfi' instead of 'arfy'
    - 'vs code' and 'visual studio code' can be normalized to one command form
    """
    if not text:
        return ""

    corrections = {
        "arfi": "arfy",
        "ar fi": "arfy",
        "hey ar fi": "hey arfy",
        "sena": "senaa",
        "vs code": "vscode",
        "visual studio code": "vscode",
    }

    fixed = text

    for wrong, right in corrections.items():
        fixed = re.sub(rf"\b{re.escape(wrong)}\b", right, fixed, flags=re.IGNORECASE)

    return fixed


def _strip_leading_wakeword(text: str) -> str:
    """
    Remove wake-word phrases if Whisper includes them in the command.

    Example:
    'hey arfy open spotify' -> 'open spotify'
    """
    lower = text.lower().strip()

    wakeword_variants = [
        "hey arfy",
        "hey ar fi",
        "hi arfy",
        "okay arfy",
        "ok arfy",
        "arfy",
        "jarvis",
    ]

    for phrase in wakeword_variants:
        if lower.startswith(phrase):
            return text[len(phrase):].strip(" ,.!?:;-")

    return text


def _is_low_content(text: str) -> bool:
    """
    Decide whether the transcript is too weak / useless / hallucinated.

    Rejected examples:
    - empty output
    - filler sounds
    - just wake word
    - 1-character junk
    - subtitle/music/applause hallucination-type tokens
    - repeated same token many times
    """
    lower = text.lower().strip()

    junk_phrases = {
        "thank you",
        "thanks for watching",
        "you",
        "uh",
        "um",
        "hmm",
        "huh",
        "hmm hmm",
        "mmm",
        "ah",
        "oh",
        "hm",
    }

    hallucination_patterns = {
        "subtitle",
        "subtitles",
        "captions",
        "music",
        "applause",
        "foreign",
    }

    if not lower:
        return True

    if lower in junk_phrases:
        return True

    if lower in {"arfy", "hey arfy", "jarvis"}:
        return True

    if len(lower) < 2:
        return True

    # Remove punctuation and check again
    if len(re.sub(r"[^a-z0-9]", "", lower)) < 2:
        return True

    if lower in hallucination_patterns:
        return True

    # Example: "no no no" / "um um um"
    tokens = [t for t in re.split(r"\s+", lower) if t]
    if len(tokens) >= 3 and len(set(tokens)) == 1:
        return True

    return False


def clean_transcript(text: str) -> str:
    """
    Clean ASR output before passing it to the assistant router / tool layer.

    Steps:
    1. apply custom corrections
    2. remove leading wake word
    3. normalize whitespace
    4. reject low-content outputs
    """
    if not text:
        return ""

    text = apply_corrections(text).strip()
    text = _strip_leading_wakeword(text)

    # Collapse repeated internal spaces
    text = re.sub(r"\s+", " ", text).strip()

    if _is_low_content(text):
        return ""

    return text


def postprocess_transcript(text: str) -> str:
    """
    Main entrypoint used by speech.py.

    Keep one canonical function so all transcript cleanup goes through one place.
    """
    return clean_transcript(text)