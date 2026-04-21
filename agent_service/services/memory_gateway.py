# agent_service/services/memory_gateway.py

import os
from pathlib import Path

import requests
from dotenv import load_dotenv

# Load env from agent_service/.env
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(env_path)

MEMORY_SERVICE_URL = os.getenv("MEMORY_SERVICE_URL")


def retrieve_memory_context(
    query: str,
    *,
    exact_limit: int = 3,
    semantic_limit: int = 5,
) -> dict:
    """
    Retrieve a richer memory context packet from memory_service.

    Expected shape:
    {
        "query": "...",
        "exact": [...],
        "documents": [...],
        "semantic": [...],
        "merged": [...]
    }
    """
    try:
        response = requests.post(
            f"{MEMORY_SERVICE_URL}/memory/context",
            json={
                "query": query,
                "exact_limit": exact_limit,
                "semantic_limit": semantic_limit,
            },
            timeout=10,
        )
        response.raise_for_status()
        return response.json()

    except Exception:
        # Fail soft so the agent still works without memory
        return {
            "query": query,
            "exact": [],
            "documents": [],
            "semantic": [],
            "merged": [],
        }


def retrieve_relevant_memories(query: str, limit: int = 5) -> list:
    """
    Backward-compatible helper that returns the merged memory list.

    Existing graph/tool code still expects a flat memory list.
    """
    context = retrieve_memory_context(
        query,
        exact_limit=min(3, limit),
        semantic_limit=limit,
    )
    return context.get("merged", [])


def get_exact_memories(context: dict) -> list:
    """
    Convenience helper for future exact-fact-sensitive flows.
    """
    return context.get("exact", [])


def get_document_memories(context: dict) -> list:
    """
    Convenience helper for document metadata hits.
    """
    return context.get("documents", [])


def get_semantic_memories(context: dict) -> list:
    """
    Convenience helper for semantic memory hits.
    """
    return context.get("semantic", [])