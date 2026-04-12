import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams
from sentence_transformers import SentenceTransformer

# Load env
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(env_path)

COLLECTION_NAME = os.getenv("QDRANT_COLLECTION")
QDRANT_PATH = os.getenv("QDRANT_PATH")

# Local Qdrant client
client = QdrantClient(path=QDRANT_PATH)

# Embedding model
model = SentenceTransformer("all-MiniLM-L6-v2")


def embed_text(text: str):
    """
    Convert text into an embedding vector.
    """
    return model.encode(text).tolist()


def ensure_collection():
    """
    Create the Qdrant collection if it does not already exist.
    """
    collections = client.get_collections().collections
    existing_names = [c.name for c in collections]

    if COLLECTION_NAME not in existing_names:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(
                size=384,
                distance=Distance.COSINE,
            ),
        )


def _now_iso() -> str:
    """
    Return current UTC time as ISO string.
    """
    return datetime.now(timezone.utc).isoformat()


def _parse_iso(ts: str | None):
    """
    Safely parse an ISO timestamp string.

    Always return a timezone-aware datetime in UTC.
    This prevents naive/aware subtraction errors.
    """
    if not ts:
        return None

    try:
        # Normalize trailing Z
        cleaned = ts.replace("Z", "+00:00")
        dt = datetime.fromisoformat(cleaned)

        # If parsed datetime has no timezone, assume UTC
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        return dt.astimezone(timezone.utc)

    except Exception:
        return None


def _recency_bonus(created_at: str | None) -> float:
    """
    Add a small recency boost so fresher relevant memories rank slightly higher.
    """
    dt = _parse_iso(created_at)
    if dt is None:
        return 0.0

    now = datetime.now(timezone.utc)
    age_days = (now - dt).total_seconds() / 86400

    if age_days <= 1:
        return 0.15
    if age_days <= 7:
        return 0.10
    if age_days <= 30:
        return 0.05
    return 0.0


def generate_qdrant_id() -> str:
    """
    Generate a valid UUID string for Qdrant point ids.

    We use UUID strings for ALL Qdrant points to avoid id-format issues
    in local Qdrant mode.
    """
    return str(uuid4())


def upsert_memory_point(
    point_id: str,
    category: str,
    key: str,
    value: str,
    metadata: dict | None = None,
):
    """
    Store one memory point in Qdrant.

    point_id must be a valid UUID string.
    """
    ensure_collection()

    metadata = metadata or {}

    text_for_embedding = f"{category} {key} {value}"
    vector = embed_text(text_for_embedding)

    payload = {
        "category": category,
        "key": key,
        "value": value,
        "created_at": metadata.get("created_at", _now_iso()),
        "session_id": metadata.get("session_id"),
        "memory_kind": metadata.get("memory_kind", "durable_memory"),
        "chunk_reason": metadata.get("chunk_reason"),
        "summary": metadata.get("summary"),
        "transcript": metadata.get("transcript"),
        "session_started_at": metadata.get("session_started_at"),
        "session_ended_at": metadata.get("session_ended_at"),
        "sqlite_id": metadata.get("sqlite_id"),
    }

    client.upsert(
        collection_name=COLLECTION_NAME,
        points=[
            PointStruct(
                id=point_id,
                vector=vector,
                payload=payload,
            )
        ],
    )


def upsert_session_archive(
    session_id: str,
    transcript: str,
    summary: str,
    session_started_at: str | None = None,
    session_ended_at: str | None = None,
    chunk_reason: str = "overflow",
):
    """
    Save archived session chat into Qdrant.
    """
    point_id = generate_qdrant_id()

    upsert_memory_point(
        point_id=point_id,
        category="session_history",
        key=session_id,
        value=summary,
        metadata={
            "created_at": _now_iso(),
            "session_id": session_id,
            "memory_kind": "session_archive",
            "chunk_reason": chunk_reason,
            "summary": summary,
            "transcript": transcript,
            "session_started_at": session_started_at,
            "session_ended_at": session_ended_at,
        },
    )

    return point_id


def upsert_session_summary(
    session_id: str,
    summary: str,
    session_started_at: str | None = None,
    session_ended_at: str | None = None,
    sqlite_id: int | None = None,
):
    """
    Save a final session summary into Qdrant.
    """
    point_id = generate_qdrant_id()

    upsert_memory_point(
        point_id=point_id,
        category="session_summary",
        key=session_id,
        value=summary,
        metadata={
            "created_at": _now_iso(),
            "session_id": session_id,
            "memory_kind": "session_summary",
            "chunk_reason": "session_end",
            "summary": summary,
            "session_started_at": session_started_at,
            "session_ended_at": session_ended_at,
            "sqlite_id": sqlite_id,
        },
    )

    return point_id


def semantic_search(query: str, limit: int = 5):
    """
    Search memories semantically using vector similarity, then rerank slightly
    using recency.
    """
    ensure_collection()
    vector = embed_text(query)

    raw_results = client.query_points(
        collection_name=COLLECTION_NAME,
        query=vector,
        limit=max(limit * 3, limit),
        with_payload=True,
    ).points

    reranked = []
    for point in raw_results:
        payload = point.payload or {}
        created_at = payload.get("created_at")
        adjusted_score = float(point.score) + _recency_bonus(created_at)

        reranked.append(
            {
                "id": point.id,
                "score": adjusted_score,
                "raw_score": point.score,
                "category": payload.get("category"),
                "key": payload.get("key"),
                "value": payload.get("value"),
                "session_id": payload.get("session_id"),
                "created_at": created_at,
                "memory_kind": payload.get("memory_kind"),
                "chunk_reason": payload.get("chunk_reason"),
                "summary": payload.get("summary"),
                "transcript": payload.get("transcript"),
                "sqlite_id": payload.get("sqlite_id"),
            }
        )

    reranked.sort(key=lambda x: x["score"], reverse=True)

    memories = []
    for item in reranked[:limit]:
        memories.append(
            {
                "id": item["id"],
                "score": item["score"],
                "category": item["category"],
                "key": item["key"],
                "value": item["summary"] or item["value"],
                "session_id": item["session_id"],
                "created_at": item["created_at"],
                "memory_kind": item["memory_kind"],
                "chunk_reason": item["chunk_reason"],
                "sqlite_id": item["sqlite_id"],
            }
        )

    return memories