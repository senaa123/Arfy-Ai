"""
PDF extractor wrapper.

Important:
- We intentionally keep the real PDF/OCR fallback logic in pdf_pipeline.py
  because that file already contains the proven fail-fast OCR-required behavior,
  temp cleanup, and page-level OCR routing that passed the Phase 2/4B checks.

This file only gives the PDF logic a cleaner home for the new extractor layout.
"""

from document_service.pdf_pipeline import extract_pdf_document

__all__ = ["extract_pdf_document"]