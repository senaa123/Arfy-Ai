"""
Grounded answer builder for Phase 3 RAG.

Responsibilities:
- build a strict evidence-only prompt
- label evidence blocks consistently (E1, E2, ...)
- call the LLM client
- return normalized citations for the same evidence blocks

Important:
- this module does not retrieve chunks
- this module does not judge grounding
- it only answers from already-selected evidence
"""

from __future__ import annotations

from rag_service.clients import LLMClient
from rag_service.config import settings
from rag_service.grounding import build_citations
from rag_service.schemas import RagCitation, RetrievedChunk


def _format_evidence_block(
    *,
    chunks: list[RetrievedChunk],
    citations: list[RagCitation],
) -> str:
    """
    Turn evidence chunks into a structured prompt block.

    Each block is labeled with the citation label so the model can refer to it
    directly inside the answer, e.g. [E1], [E2].
    """
    chunk_by_id = {chunk.chunk_id: chunk for chunk in chunks}
    blocks: list[str] = []

    for citation in citations:
        chunk = chunk_by_id.get(citation.chunk_id)
        if chunk is None:
            continue

        block = (
            f"[{citation.label}]\n"
            f"document_id: {citation.document_id}\n"
            f"chunk_id: {citation.chunk_id}\n"
            f"file_name: {citation.file_name or ''}\n"
            f"source_ref: {citation.source_ref or ''}\n"
            f"pages: {citation.pages}\n"
            f"chunk_index: {citation.chunk_index}\n"
            f"text:\n{chunk.text}\n"
        )
        blocks.append(block)

    return "\n".join(blocks).strip()


def _clean_generated_answer(answer: str) -> str:
    """
    Normalize the final answer text lightly.

    We keep this minimal so we do not accidentally rewrite evidence content.
    """
    cleaned = " ".join((answer or "").split()).strip()
    return cleaned


def build_grounded_answer(question: str, chunks: list[RetrievedChunk]) -> tuple[str, list[RagCitation]]:
    """
    Build a grounded answer strictly from the supplied evidence chunks.

    Phase 3 behavior:
    - only the first bounded evidence set is sent to the model
    - citations and prompt evidence labels stay aligned
    """
    if not chunks:
        raise RuntimeError("Cannot build grounded answer without evidence chunks.")

    # Keep the answer context bounded and aligned with returned citations.
    answer_chunks = chunks[: settings.ANSWER_MAX_CONTEXT_CHUNKS]
    citations = build_citations(answer_chunks)

    if not citations:
        raise RuntimeError("No citations could be built from the selected evidence.")

    evidence_block = _format_evidence_block(
        chunks=answer_chunks,
        citations=citations,
    )

    system_prompt = (
        "You are a grounded retrieval answering assistant.\n"
        "Answer only from the provided evidence blocks.\n"
        "Do not invent facts.\n"
        "When you make a factual claim, cite one or more evidence labels inline, "
        "for example [E1] or [E1][E2].\n"
        "Do not mention any evidence label that was not provided.\n"
        "If the evidence is insufficient, say so clearly.\n"
        "If the evidence conflicts, mention the conflict instead of guessing.\n"
        "Keep the answer clear and concise.\n"
    )

    user_prompt = (
        f"Question:\n{question}\n\n"
        f"Evidence:\n{evidence_block}\n\n"
        "Write a grounded answer using only the evidence above."
    )

    client = LLMClient()
    answer = client.generate_answer(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
    )

    return _clean_generated_answer(answer), citations