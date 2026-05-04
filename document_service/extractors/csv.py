"""
CSV extraction.

This module exists so CSV logic is explicit and does not get buried
inside generic text extraction.

Current preserved behavior:
- read CSV safely
- convert each row into a readable plain-text line
- join columns with ' | '
"""

from __future__ import annotations

import csv
from pathlib import Path

from document_service.identity import (
    build_content_hash,
    build_portable_document_id,
    build_source_ref,
)
from document_service.schemas import ExtractedDocument


def _read_csv_as_text(file_path: str | Path) -> str:
    """
    Convert CSV rows into a readable plain-text form.

    Example row:
    name,age,city
    becomes:
    name | age | city
    """
    lines: list[str] = []

    with open(file_path, "r", encoding="utf-8", errors="ignore", newline="") as f:
        reader = csv.reader(f)
        for row in reader:
            # Keep the existing readable representation.
            lines.append(" | ".join(cell.strip() for cell in row))

    return "\n".join(lines).strip()


def extract_csv_document(file_path: str, enable_ocr: bool = True) -> ExtractedDocument:
    """
    Extract CSV into the normalized ExtractedDocument shape.

    OCR is not used here, but the parameter stays for consistent extractor signatures.
    """
    _ = enable_ocr

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if not path.is_file():
        raise ValueError(f"Path is not a file: {file_path}")

    if path.suffix.lower() != ".csv":
        raise ValueError(f"Expected .csv file, got: {path.suffix.lower()}")

    text = _read_csv_as_text(path)
    content_hash = build_content_hash(text)
    document_id = build_portable_document_id(
        file_name=path.name,
        extension=".csv",
        text=text,
    )

    metadata = {
        "source_path": str(path.resolve()),
        "size_bytes": path.stat().st_size,
    }

    return ExtractedDocument(
        document_id=document_id,
        source_ref=build_source_ref(file_path),
        content_hash=content_hash,
        local_file_path=str(path.resolve()),
        file_name=path.name,
        extension=".csv",
        text=text,
        metadata=metadata,
        ocr_used=False,
    )
