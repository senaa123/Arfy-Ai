"""
Text-like document extraction.

This module handles:
- plain text-like files
- a thin image -> OCR-service adapter to preserve existing behavior
  without introducing a dedicated extractors/image.py module

Important:
- This does NOT do local OCR.
- It only delegates image OCR to document_service.clients.ocr_client,
  which then calls the separate OCR service.
"""

from __future__ import annotations

from pathlib import Path

from document_service.clients.ocr_client import run_remote_ocr
from document_service.identity import (
    build_content_hash,
    build_portable_document_id,
    build_source_ref,
)
from document_service.schemas import ExtractedDocument

# Keep the supported text-like set aligned with the current logic.
TEXT_EXTENSIONS = {
    ".txt",
    ".md",
    ".py",
    ".json",
    ".yaml",
    ".yml",
    ".log",
}

# Keep image support so existing logic is not lost, but do not create
# a separate image extractor module in this pass.
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tiff"}


def is_text_file(file_path: str | Path) -> bool:
    """Return True if the file is one of the supported text-like types."""
    return Path(file_path).suffix.lower() in TEXT_EXTENSIONS


def is_image_file(file_path: str | Path) -> bool:
    """
    Return True if the file is a supported image type.

    These files still route to the OCR service, not to any local OCR engine.
    """
    return Path(file_path).suffix.lower() in IMAGE_EXTENSIONS


def _read_plain_text_file(file_path: str | Path) -> str:
    """
    Read common text-based files safely.

    We keep the current forgiving behavior:
    - utf-8
    - ignore decoding errors
    """
    return Path(file_path).read_text(encoding="utf-8", errors="ignore").strip()


def extract_text_document(file_path: str, enable_ocr: bool = True) -> ExtractedDocument:
    """
    Extract a plain text-like file into the normalized ExtractedDocument shape.

    OCR is not used here, but we keep the parameter for a consistent extractor signature.
    """
    _ = enable_ocr  # kept for signature consistency across extractors

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if not path.is_file():
        raise ValueError(f"Path is not a file: {file_path}")

    extension = path.suffix.lower()
    if extension not in TEXT_EXTENSIONS:
        raise ValueError(f"Unsupported text-like file type: {extension}")

    text = _read_plain_text_file(path)
    content_hash = build_content_hash(text)
    document_id = build_portable_document_id(
        file_name=path.name,
        extension=extension,
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
        extension=extension,
        text=text,
        metadata=metadata,
        ocr_used=False,
    )


def extract_image_document_via_ocr_service(
    file_path: str,
    enable_ocr: bool = True,
) -> ExtractedDocument:
    """
    Preserve the existing image-file ingest behavior without introducing
    a separate image extractor module.

    This is still a thin adapter only:
    - validate image type
    - call the OCR service client
    - return normalized ExtractedDocument
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if not path.is_file():
        raise ValueError(f"Path is not a file: {file_path}")

    if not is_image_file(path):
        raise ValueError(f"Unsupported image file type: {path.suffix.lower()}")

    if not enable_ocr:
        raise ValueError("OCR is disabled, so image files cannot be processed.")

    ocr_result = run_remote_ocr(str(path))
    if not isinstance(ocr_result, dict):
        raise RuntimeError("OCR client returned an invalid response.")

    if not ocr_result.get("success"):
        raise RuntimeError(ocr_result.get("message", "OCR failed."))

    text = (ocr_result.get("text") or "").strip()
    content_hash = build_content_hash(text)
    document_id = build_portable_document_id(
        file_name=path.name,
        extension=path.suffix.lower(),
        text=text,
    )

    metadata = {
        "source_path": str(path.resolve()),
        "size_bytes": path.stat().st_size,
        "ocr_mode": "image_file",
    }

    return ExtractedDocument(
        document_id=document_id,
        source_ref=build_source_ref(file_path),
        content_hash=content_hash,
        local_file_path=str(path.resolve()),
        file_name=path.name,
        extension=path.suffix.lower(),
        text=text,
        metadata=metadata,
        ocr_used=True,
    )
