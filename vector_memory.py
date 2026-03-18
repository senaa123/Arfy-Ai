import atexit
import hashlib
import json
import os
import warnings
from datetime import datetime, timezone
from typing import Dict, List
from uuid import NAMESPACE_URL, UUID, uuid5

from memory import load_memory


QDRANT_PATH = os.getenv("QDRANT_PATH", os.path.join("Memory", "qdrant"))
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "arfy_memory")
QDRANT_EMBED_MODEL = os.getenv("QDRANT_EMBED_MODEL", "BAAI/bge-small-en-v1.5")
QDRANT_MEMORY_LIMIT = int(os.getenv("QDRANT_MEMORY_LIMIT", "4"))
SYNC_STATE_FILE = os.path.join("Memory", "qdrant_sync_state.json")

_client = None
_client_error = None


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _get_client():
    global _client, _client_error

    if _client_error is not None:
        return None

    if _client is None:
        try:
            from qdrant_client import QdrantClient

            os.makedirs(QDRANT_PATH, exist_ok=True)
            _client = QdrantClient(path=QDRANT_PATH)
        except Exception as exc:
            _client_error = exc
            print(f"Semantic memory disabled: {exc}")
            return None

    return _client


def _disable_semantic_memory(exc) -> None:
    global _client, _client_error

    _client_error = exc
    _close_client()
    print(f"Semantic memory disabled: {exc}")


def _close_client() -> None:
    global _client

    if _client is None:
        return

    try:
        _client.close()
    except Exception:
        pass
    finally:
        _client = None


def _load_sync_state() -> Dict[str, Dict[str, str]]:
    if not os.path.exists(SYNC_STATE_FILE):
        return {"entries": {}}

    try:
        with open(SYNC_STATE_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)
            if isinstance(data, dict) and "entries" in data:
                return data
    except Exception as exc:
        print(f"Could not read semantic memory sync state: {exc}")

    return {"entries": {}}


def _save_sync_state(state: Dict[str, Dict[str, str]]) -> None:
    os.makedirs(os.path.dirname(SYNC_STATE_FILE), exist_ok=True)
    with open(SYNC_STATE_FILE, "w", encoding="utf-8") as file:
        json.dump(state, file, indent=2)


def _fact_to_text(category: str, key: str, value) -> str:
    pretty_key = key.replace("_", " ")
    pretty_value = str(value).strip()

    if category == "personal":
        return f"Senaa's {pretty_key} is {pretty_value}."
    if category == "preferences":
        return f"Senaa prefers {pretty_key}: {pretty_value}."
    return f"{category.replace('_', ' ').title()} - {pretty_key}: {pretty_value}."


def _fact_id(category: str, key: str) -> str:
    return f"structured:{category}:{key}"


def _fact_signature(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _normalize_point_id(raw_id: str) -> str:
    try:
        return str(UUID(str(raw_id)))
    except ValueError:
        return str(uuid5(NAMESPACE_URL, str(raw_id)))


def _structured_entries(memory: Dict) -> List[Dict]:
    entries = []

    for category, values in memory.items():
        if category == "corrections":
            continue

        if isinstance(values, dict):
            for key, value in values.items():
                if value in (None, ""):
                    continue

                text = _fact_to_text(category, key, value)
                entries.append(
                    {
                        "id": _fact_id(category, key),
                        "text": text,
                        "signature": _fact_signature(text),
                        "metadata": {
                            "source": "structured_memory",
                            "category": category,
                            "key": key,
                            "embed_model": QDRANT_EMBED_MODEL,
                            "updated_at": _now_iso(),
                        },
                    }
                )
        elif values not in (None, ""):
            text = f"{category.replace('_', ' ').title()}: {values}."
            entries.append(
                {
                    "id": _fact_id("root", category),
                    "text": text,
                    "signature": _fact_signature(text),
                    "metadata": {
                        "source": "structured_memory",
                        "category": "root",
                        "key": category,
                        "embed_model": QDRANT_EMBED_MODEL,
                        "updated_at": _now_iso(),
                    },
                }
            )

    return entries


def sync_structured_memory() -> bool:
    client = _get_client()
    if client is None:
        return False

    memory = load_memory()
    entries = _structured_entries(memory)
    if not entries:
        return True

    state = _load_sync_state()
    changed = False

    for entry in entries:
        if state["entries"].get(entry["id"]) == entry["signature"]:
            continue

        try:
            # Mirror exact JSON facts into Qdrant so retrieval can stay semantic.
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", message=r"`add` method has been deprecated.*")
                client.add(
                    collection_name=QDRANT_COLLECTION,
                    documents=[entry["text"]],
                    metadata=[entry["metadata"]],
                    ids=[_normalize_point_id(entry["id"])],
                    batch_size=1,
                )
            state["entries"][entry["id"]] = entry["signature"]
            changed = True
        except Exception as exc:
            if "fastembed is not installed" in str(exc).lower():
                _disable_semantic_memory(exc)
            else:
                print(f"Semantic memory sync failed: {exc}")
            return False

    if changed:
        _save_sync_state(state)

    return True


def add_semantic_note(text: str, metadata: Dict | None = None, note_id: str | None = None) -> bool:
    client = _get_client()
    if client is None or not text.strip():
        return False

    payload = {
        "source": "semantic_note",
        "embed_model": QDRANT_EMBED_MODEL,
        "updated_at": _now_iso(),
    }
    if metadata:
        payload.update(metadata)

    memory_id = note_id or f"note:{hashlib.sha256(text.encode('utf-8')).hexdigest()[:24]}"

    try:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message=r"`add` method has been deprecated.*")
            client.add(
                collection_name=QDRANT_COLLECTION,
                documents=[text.strip()],
                metadata=[payload],
                ids=[_normalize_point_id(memory_id)],
                batch_size=1,
            )
        return True
    except Exception as exc:
        if "fastembed is not installed" in str(exc).lower():
            _disable_semantic_memory(exc)
        else:
            print(f"Semantic memory write failed: {exc}")
        return False


def search_semantic_memories(query_text: str, limit: int | None = None) -> List[Dict]:
    client = _get_client()
    if client is None or not query_text.strip():
        return []

    sync_structured_memory()

    try:
        # Query with text so the client handles embedding using the configured model.
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message=r"`query` method has been deprecated.*")
            results = client.query(
                collection_name=QDRANT_COLLECTION,
                query_text=query_text.strip(),
                limit=limit or QDRANT_MEMORY_LIMIT,
            )
    except Exception as exc:
        if "fastembed is not installed" in str(exc).lower():
            _disable_semantic_memory(exc)
        else:
            print(f"Semantic memory query failed: {exc}")
        return []

    memories = []
    for item in results:
        text = getattr(item, "document", None)
        metadata = getattr(item, "metadata", None) or {}
        score = float(getattr(item, "score", 0.0) or 0.0)

        if not text:
            text = metadata.get("document")
        if not text:
            continue

        memories.append(
            {
                "text": text,
                "score": score,
                "metadata": metadata,
            }
        )

    return memories


def get_semantic_memory_context(query_text: str, limit: int | None = None) -> str:
    memories = search_semantic_memories(query_text, limit=limit)
    if not memories:
        return "No relevant semantic memories found."

    seen = set()
    lines = []
    for memory in memories:
        text = memory["text"].strip()
        if not text or text in seen:
            continue

        seen.add(text)
        category = memory["metadata"].get("category")
        if category:
            label = category.replace("_", " ").title()
            lines.append(f"- [{label}] {text}")
        else:
            lines.append(f"- {text}")

    return "\n".join(lines) if lines else "No relevant semantic memories found."


atexit.register(_close_client)
