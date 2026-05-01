"""
Workflow package exports.

Keeping this export means imports like:
from document_service.workflows import ingest_document_flow

still work cleanly after the refactor.
"""

from . import ingest as _ingest


extract_pdf_document = _ingest.extract_pdf_document
extract_non_pdf_document = _ingest.extract_non_pdf_document
register_document_metadata = _ingest.register_document_metadata
register_document_chunks = _ingest.register_document_chunks
persist_document = _ingest.persist_document


def ingest_document_flow(req):
    """
    Compatibility wrapper for the split workflow package.

    Tests and older callers used to patch attributes on
    document_service.workflows directly when this logic lived in one flat module.
    Sync the package-level aliases back into ingest.py before each call so the
    refactor keeps working with those patch points.
    """
    _ingest.extract_pdf_document = extract_pdf_document
    _ingest.extract_non_pdf_document = extract_non_pdf_document
    _ingest.register_document_metadata = register_document_metadata
    _ingest.register_document_chunks = register_document_chunks
    _ingest.persist_document = persist_document
    return _ingest.ingest_document_flow(req)


__all__ = [
    "ingest_document_flow",
    "extract_pdf_document",
    "extract_non_pdf_document",
    "register_document_metadata",
    "register_document_chunks",
    "persist_document",
]
