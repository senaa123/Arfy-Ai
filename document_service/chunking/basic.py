"""
Basic text chunking.

Preserves the existing downstream-facing behavior:
- light text normalization before chunking
- overlapping chunks with deterministic chunk ids when namespaced
- DocumentChunk records that storage/memory registration already expect
"""

from __future__ import annotations

import hashlib
import re
import uuid

from document_service.schemas import DocumentChunk

from .strategies import ChunkingStrategy


def normalize_text(text: str) -> str:
    """
    Light cleanup before chunking.
    """
    text = re.sub(r"\r\n?", "\n", text or "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def chunk_text(
    text: str,
    chunk_size: int = 1200,
    chunk_overlap: int = 200,
    chunk_id_namespace: str | None = None,
) -> list[DocumentChunk]:
    """
    Split text into overlapping chunks for later retrieval/indexing.
    """
    cleaned = normalize_text(text)

    if not cleaned:
        return []

    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size")

    chunks: list[DocumentChunk] = []
    start = 0
    step = chunk_size - chunk_overlap
    text_length = len(cleaned)
    chunk_index = 0

    while start < text_length:
        end = min(start + chunk_size, text_length)

        if end < text_length:
            last_space = cleaned.rfind(" ", start, end)
            if last_space > start + 200:
                end = last_space

        chunk_value = cleaned[start:end].strip()

        if chunk_value:
            if chunk_id_namespace:
                text_hash = hashlib.sha1(chunk_value.encode("utf-8")).hexdigest()
                chunk_id = str(
                    uuid.uuid5(
                        uuid.NAMESPACE_URL,
                        f"{chunk_id_namespace}:{chunk_index}:{start}:{end}:{text_hash}",
                    )
                )
            else:
                chunk_id = str(uuid.uuid4())

            chunks.append(
                DocumentChunk(
                    chunk_id=chunk_id,
                    chunk_index=chunk_index,
                    text=chunk_value,
                    start_char=start,
                    end_char=end,
                )
            )
            chunk_index += 1

        start += step

    return chunks


def build_chunks(
    text: str,
    strategy: ChunkingStrategy,
    *,
    chunk_id_namespace: str | None = None,
) -> list[DocumentChunk]:
    """
    Build chunk records using the selected strategy.
    """
    return chunk_text(
        text=text,
        chunk_size=strategy.chunk_size,
        chunk_overlap=strategy.chunk_overlap,
        chunk_id_namespace=chunk_id_namespace,
    )
