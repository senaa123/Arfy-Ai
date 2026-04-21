# document_service/storage.py

import json
from pathlib import Path

from document_service.schemas import DocumentChunk, ExtractedDocument

# Local persistence root
DATA_DIR = Path(__file__).resolve().parent / "data"


def persist_document(
    document: ExtractedDocument,
    chunks: list[DocumentChunk],
) -> str:
    """
    Persist extracted document artifacts locally.

    Stores:
    - metadata.json
    - document.txt
    - chunks.json

    Phase 4 note:
    - document_id is now a portable content-based/shared identity
    - local_file_path is stored only as local metadata
    """
    document_dir = DATA_DIR / document.document_id
    document_dir.mkdir(parents=True, exist_ok=True)

    metadata_payload = {
        "document_id": document.document_id,
        "source_ref": document.source_ref,
        "content_hash": document.content_hash,
        "local_file_path": document.local_file_path,
        "file_name": document.file_name,
        "extension": document.extension,
        "ocr_used": document.ocr_used,
        "metadata": document.metadata,
        "text_length": len(document.text),
        "chunk_count": len(chunks),
    }

    (document_dir / "metadata.json").write_text(
        json.dumps(metadata_payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    (document_dir / "document.txt").write_text(
        document.text,
        encoding="utf-8",
    )

    chunk_payload = [chunk.model_dump() for chunk in chunks]
    (document_dir / "chunks.json").write_text(
        json.dumps(chunk_payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return str(document_dir.resolve())