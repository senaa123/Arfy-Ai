"""
Central configuration for rag_service.

Why this file exists:
- keeps service URLs in one place
- keeps model settings in one place
- keeps retrieval thresholds in one place
- makes the rest of the code easier to read and maintain
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(env_path)


@dataclass(frozen=True)
class Settings:
    # Service identity
    SERVICE_NAME: str = "rag_service"
    SERVICE_HOST: str = os.getenv("RAG_SERVICE_HOST", "127.0.0.1")
    SERVICE_PORT: int = int(os.getenv("RAG_SERVICE_PORT", "8004"))

    # Memory service connection
    MEMORY_SERVICE_BASE_URL: str = os.getenv(
        "MEMORY_SERVICE_BASE_URL",
        "http://127.0.0.1:8000",
    ).rstrip("/")
    MEMORY_SEARCH_CHUNKS_PATH: str = os.getenv(
        "MEMORY_SEARCH_CHUNKS_PATH",
        "/memory/search/chunks",
    )

    # LLM connection
    # This is written as an OpenAI-compatible endpoint so it can work with
    # Groq/OpenAI-compatible backends by changing env vars only.
    LLM_BASE_URL: str = os.getenv(
        "RAG_LLM_BASE_URL",
        "https://api.groq.com/openai/v1",
    ).rstrip("/")
    LLM_API_KEY: str = os.getenv("RAG_LLM_API_KEY") or os.getenv("GROQ_API_KEY", "")
    LLM_MODEL: str = os.getenv("RAG_LLM_MODEL") or os.getenv(
        "GROQ_MODEL_MAIN",
        "llama-3.3-70b-versatile",
    )

    # Retrieval settings
    DEFAULT_TOP_K: int = int(os.getenv("RAG_DEFAULT_TOP_K", "8"))
    DEFAULT_FINAL_K: int = int(os.getenv("RAG_DEFAULT_FINAL_K", "4"))
    MIN_GROUNDED_SCORE: float = float(os.getenv("RAG_MIN_GROUNDED_SCORE", "0.18"))
    MIN_CONTEXT_CHARS: int = int(os.getenv("RAG_MIN_CONTEXT_CHARS", "200"))

    #Self-healing  RAD settings
    ENABLE_REPAIR_RETRY: bool = os.getenv("RAG_ENABLE_REPAIR_RETRY", "true").lower() == "true"
    REPAIR_TOP_K_MULTIPLIER: int = int(os.getenv("RAG_REPAIR_TOP_K_MULTIPLIER", "2"))
    REPAIR_MAX_TOP_K: int = int(os.getenv("RAG_REPAIR_MAX_TOP_K", "16"))
    REPAIR_FINAL_K_EXTRA: int = int(os.getenv("RAG_REPAIR_FINAL_K_EXTRA", "2"))
    REPAIR_MAX_FINAL_K: int = int(os.getenv("RAG_REPAIR_MAX_FINAL_K", "6"))

    # Neighbor expansion settings
    NEIGHBOR_EXPANSION_WINDOW: int = int(os.getenv("RAG_NEIGHBOR_EXPANSION_WINDOW", "1"))
    NEIGHBOR_EXPANSION_MAX_CHUNKS: int = int(os.getenv("RAG_NEIGHBOR_EXPANSION_MAX_CHUNKS", "6"))

    # Generation settings
    ANSWER_MAX_CONTEXT_CHUNKS: int = int(os.getenv("RAG_ANSWER_MAX_CONTEXT_CHUNKS", "4"))
    REQUEST_TIMEOUT_SECONDS: float = float(os.getenv("RAG_REQUEST_TIMEOUT_SECONDS", "30"))

        # Phase 3 citation / evidence formatting settings
    MAX_RETURNED_CITATIONS: int = int(os.getenv("RAG_MAX_RETURNED_CITATIONS", "4"))
    CITATION_SNIPPET_CHARS: int = int(os.getenv("RAG_CITATION_SNIPPET_CHARS", "160"))


settings = Settings()
