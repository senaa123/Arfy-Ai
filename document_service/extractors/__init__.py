"""
Public extractor exports for document_service.

This package keeps extractor selection clean inside workflows/ingest.py.
"""

from pathlib import Path

from .pdf import extract_pdf_document
from .text import (
    TEXT_EXTENSIONS,
    IMAGE_EXTENSIONS,
    is_text_file,
    is_image_file,
    extract_text_document,
    extract_image_document_via_ocr_service,
)
from .csv import extract_csv_document
from .docx import extract_docx_document
from .image import extract_image_document


def extract_non_pdf_document(file_path: str, enable_ocr: bool = True):
    """
    Backward-compatible dispatcher for all non-PDF document types.
    """
    extension = Path(file_path).suffix.lower()

    if extension == ".csv":
        return extract_csv_document(file_path, enable_ocr=enable_ocr)

    if extension == ".docx":
        return extract_docx_document(file_path, enable_ocr=enable_ocr)

    if is_text_file(file_path):
        return extract_text_document(file_path, enable_ocr=enable_ocr)

    if is_image_file(file_path):
        return extract_image_document(file_path, enable_ocr=enable_ocr)

    raise ValueError(
        f"Unsupported file type: {extension}. "
        "Supported non-PDF types: txt, md, py, json, yaml, yml, log, csv, docx, image files."
    )

__all__ = [
    "TEXT_EXTENSIONS",
    "IMAGE_EXTENSIONS",
    "is_text_file",
    "is_image_file",
    "extract_pdf_document",
    "extract_text_document",
    "extract_image_document_via_ocr_service",
    "extract_image_document",
    "extract_csv_document",
    "extract_docx_document",
    "extract_non_pdf_document",
]
