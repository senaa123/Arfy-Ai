import os
from pathlib import Path

from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer

# Load .env from memory_service folder
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
    Convert text into embedding vector.
    """
    return model.encode(text).tolist()


def ensure_collection():
    """
    Create collection if it does not exist.
    """
    collections = client.get_collections().collections
    existing_names = [c.name for c in collections]

    if COLLECTION_NAME not in existing_names:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(
                size=384,  # all-MiniLM-L6-v2 embedding size
                distance=Distance.COSINE,
            ),
        )


def upsert_memory_point(point_id: int, category: str, key: str, value: str):
    """
    Store a memory item in Qdrant.
    """
    ensure_collection()

    text_for_embedding = f"{category} {key} {value}"
    vector = embed_text(text_for_embedding)

    client.upsert(
        collection_name=COLLECTION_NAME,
        points=[
            PointStruct(
                id=point_id,
                vector=vector,
                payload={
                    "category": category,
                    "key": key,
                    "value": value,
                },
            )
        ],
    )


def semantic_search(query: str, limit: int = 5):
    """
    Search memories semantically using vector similarity.
    """
    ensure_collection()
    vector = embed_text(query)

    results = client.query_points(
        collection_name=COLLECTION_NAME,
        query=vector,
        limit=limit,
        with_payload=True,
    ).points

    memories = []
    for point in results:
        payload = point.payload or {}
        memories.append(
            {
                "id": point.id,
                "score": point.score,
                "category": payload.get("category"),
                "key": payload.get("key"),
                "value": payload.get("value"),
            }
        )

    return memories