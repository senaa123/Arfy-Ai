from __future__ import annotations


def clean_transcript(text: str) -> str:
    """
    Clean ASR output before passing it to routing / tools.

    Args:
        text: Raw transcript from ASR.

    Returns:
        str: Cleaned transcript. Empty string means "ignore".
    """
    if not text:
        return ""

    text = text.strip()
    lower = text.lower()

    # Common junk phrases that sometimes appear in ASR
    junk_phrases = {
        "thank you",
        "thanks for watching",
        "you",
        "uh",
        "um",
        "hmm",
    }

    if lower in junk_phrases:
        return ""

    # Sometimes the wake word leaks into the transcript.
    wakeword_variants = [
        "hey ar fy",
        "hi arfy",
        "okay arfy",
        "ok arfy",
    ]

    for phrase in wakeword_variants:
        if lower.startswith(phrase):
            text = text[len(phrase):].strip(" ,.!?")
            break

    # If after cleanup nothing meaningful remains, ignore it
    if len(text.strip()) < 2:
        return ""

    return text.strip()