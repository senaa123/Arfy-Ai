# memory_service/services/memory_policy.py

def should_write_structured_to_vector(category: str, write_to_vector: bool) -> bool:
    """
    Decide whether a structured memory should also be pushed into vector memory.

    Rule for Phase 3A:
    - allow it by default
    - but keep the flag explicit so you can disable it later
    """
    if not write_to_vector:
        return False

    # Most durable facts are useful both as exact facts and semantic recall.
    return True


def build_structured_vector_text(category: str, key: str, value: str) -> str:
    """
    Build the semantic text that will be embedded for a structured fact.

    Example:
    - preference favorite_app Spotify
    """
    return f"{category} {key} {value}".strip()