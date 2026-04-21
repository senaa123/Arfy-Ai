# memory_service/qdrant_store.py

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from uuid import uuid4

from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams
from sentence_transformers import SentenceTransformer

# Load env from memory_service/.env
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(env_path)

STRUCTURED_COLLECTION = (
    os.getenv("QDRANT_STRUCTURED_COLLECTION")
    or os.getenv("QDRANT_COLLECTION")
    or "structured_memory"
)
SESSION_COLLECTION = os.getenv("QDRANT_SESSION_COLLECTION", "session_memory")
DOCUMENT_COLLECTION = os.getenv("QDRANT_DOCUMENT_COLLECTION", "document_memory")

QDRANT_PATH = os.getenv("QDRANT_PATH", "./qdrant_data")

_client: QdrantClient | None = None
_model: SentenceTransformer | None = None
_client_lock = Lock()
_model_lock = Lock()


def get_qdrant_client() -> QdrantClient:
    """
    Lazily initialize the local Qdrant client.
    """
    global _client

    if _client is not None:
        return _client

    with _client_lock:
        if _client is None:
            _client = QdrantClient(path=QDRANT_PATH)

    return _client


def get_embedding_model() -> SentenceTransformer:
    """
    Lazily load the embedding model from local cache only.
    """
    global _model

    if _model is not None:
        return _model

    with _model_lock:
        if _model is None:
            _model = SentenceTransformer(
                "all-MiniLM-L6-v2",
                local_files_only=True,
            )

    return _model


def embed_text(text: str):
    """
    Convert plain text into an embedding vector.
    """
    model = get_embedding_model()
    return model.encode(text).tolist()


def generate_qdrant_id() -> str:
    """
    Generate a UUID string valid for Qdrant local mode.
    """
    return str(uuid4())


def _now_iso() -> str:
    """
    Current UTC timestamp as ISO string.
    """
    return datetime.now(timezone.utc).isoformat()


def now_iso() -> str:
    """
    Public helper for payload timestamps stored in vector metadata.
    """
    return _now_iso()


def _parse_iso(ts: str | None):
    """
    Parse an ISO string into a timezone-aware datetime.
    """
    if not ts:
        return None

    try:
        cleaned = ts.replace("Z", "+00:00")
        dt = datetime.fromisoformat(cleaned)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def _recency_bonus(created_at: str | None) -> float:
    """
    Small recency bonus to make fresher memories slightly easier to recall.
    """
    dt = _parse_iso(created_at)
    if dt is None:
        return 0.0

    age_days = (datetime.now(timezone.utc) - dt).total_seconds() / 86400

    if age_days <= 1:
        return 0.15
    if age_days <= 7:
        return 0.10
    if age_days <= 30:
        return 0.05
    return 0.0


def ensure_collection(collection_name: str) -> None:
    """
    Create one collection if it does not already exist.
    """
    client = get_qdrant_client()
    collections = client.get_collections().collections
    existing_names = [c.name for c in collections]

    if collection_name not in existing_names:
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=384,
                distance=Distance.COSINE,
            ),
        )


def ensure_all_collections() -> None:
    """
    Ensure all currently-used memory collections exist.
    """
    ensure_collection(STRUCTURED_COLLECTION)
    ensure_collection(SESSION_COLLECTION)
    ensure_collection(DOCUMENT_COLLECTION)


def upsert_vector_point(
    *,
    collection_name: str,
    point_id: str,
    text_for_embedding: str,
    payload: dict,
) -> str:
    """
    Store one vector point in the requested collection.
    """
    ensure_collection(collection_name)

    vector = embed_text(text_for_embedding)
    client = get_qdrant_client()

    client.upsert(
        collection_name=collection_name,
        points=[
            PointStruct(
                id=point_id,
                vector=vector,
                payload=payload,
            )
        ],
    )

    return point_id


def query_collection(query: str, collection_name: str, limit: int = 5) -> list[dict]:
    """
    Query one collection semantically and return normalized results.

    Phase 3C change:
    - return document chunk metadata too when searching document_memory
    """
    ensure_collection(collection_name)

    vector = embed_text(query)
    client = get_qdrant_client()

    raw_results = client.query_points(
        collection_name=collection_name,
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
                "id": str(point.id),
                "score": adjusted_score,
                "raw_score": float(point.score),
                "collection_name": collection_name,
                "category": payload.get("category"),
                "key": payload.get("key"),
                "value": payload.get("value"),
                "public_id": payload.get("public_id"),
                "session_id": payload.get("session_id"),
                "document_id": payload.get("document_id"),
                "created_at": created_at,
                "memory_kind": payload.get("memory_kind"),
                "chunk_reason": payload.get("chunk_reason"),
                "summary": payload.get("summary"),
                "transcript": payload.get("transcript"),
                "linked_record_id": payload.get("linked_record_id"),
                "source": payload.get("source"),
                "file_name": payload.get("file_name"),
                "source_ref": payload.get("source_ref"),
                "content_hash": payload.get("content_hash"),
                "extension": payload.get("extension"),
                "chunk_index": payload.get("chunk_index"),
                "start_char": payload.get("start_char"),
                "end_char": payload.get("end_char"),
            }
        )

    reranked.sort(key=lambda item: item["score"], reverse=True)
    return reranked[:limit]