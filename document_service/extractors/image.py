"""
Thin image extractor.

Image ingest stays as an OCR-service adapter only.
No local OCR implementation belongs in document_service.
"""

from __future__ import annotations

from document_service.extractors.text import extract_image_document_via_ocr_service


def extract_image_document(file_path: str, enable_ocr: bool = True):
    return extract_image_document_via_ocr_service(
        file_path=file_path,
        enable_ocr=enable_ocr,
    )


__all__ = ["extract_image_document"]
