"""
Chunking strategy definitions.

Keep this small and simple for now.
You can later grow this without changing route or workflow code.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ChunkingStrategy:
    chunk_size: int = 800
    chunk_overlap: int = 120


def choose_chunking_strategy(
    *,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> ChunkingStrategy:
    """
    Choose the active chunking strategy.

    If the caller passes explicit values, use them.
    Otherwise fall back to conservative defaults.
    """
    size = chunk_size if chunk_size is not None else 800
    overlap = chunk_overlap if chunk_overlap is not None else 120

    # Basic safety normalization.
    size = max(1, int(size))
    overlap = max(0, int(overlap))
    overlap = min(overlap, max(0, size - 1))

    return ChunkingStrategy(chunk_size=size, chunk_overlap=overlap)
