# document_service/pdf_pipeline.py

import shutil
from pathlib import Path

from document_service.clients.ocr_client import run_remote_ocr
from document_service.identity import (
    build_content_hash,
    build_local_snapshot_id,
    build_portable_document_id,
    build_source_ref,
)
from document_service.schemas import ExtractedDocument


def _render_pdf_page_to_image(
    pdf_path: str,
    page_index: int,
    output_dir: Path,
) -> str:
    """
    Render one PDF page to an image for OCR.

    Requires PyMuPDF (fitz).
    """
    try:
        import fitz  # PyMuPDF
    except Exception as e:
        raise RuntimeError(
            "PyMuPDF is not installed. Install it to OCR PDF pages."
        ) from e

    output_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(pdf_path)
    try:
        page = doc.load_page(page_index)
        pix = page.get_pixmap()
        output_path = output_dir / f"page_{page_index + 1}.png"
        pix.save(str(output_path))
        return str(output_path.resolve())
    finally:
        doc.close()


def extract_pdf_document(
    file_path: str,
    enable_ocr: bool = True,
    pdf_ocr_min_chars: int = 30,
) -> ExtractedDocument:
    """
    Extract a PDF using a hybrid strategy.

    Handles all 3 cases:
    1. text PDF -> direct text extraction only
    2. scanned PDF -> OCR for all weak/empty pages
    3. mixed PDF -> direct extraction for some pages, OCR for others

    Phase 4 change:
    - document identity is portable
    - temp OCR page dir uses a local-only snapshot id
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if not path.is_file():
        raise ValueError(f"Path is not a file: {file_path}")

    if path.suffix.lower() != ".pdf":
        raise ValueError("extract_pdf_document only accepts .pdf files.")

    try:
        from pypdf import PdfReader
    except Exception as e:
        raise RuntimeError(
            "pypdf is not installed. Install it to read PDFs."
        ) from e

    reader = PdfReader(file_path)
    page_count = len(reader.pages)

    page_texts: list[str] = []
    ocr_used = False
    ocr_pages: list[int] = []
    ocr_required_pages: list[int] = []
    ocr_failed_pages: list[int] = []
    ocr_failure_messages: list[str] = []

    # This temp folder is local runtime state only.
    local_snapshot_id = build_local_snapshot_id(file_path)
    rendered_pages_dir = path.parent / f".arfy_pdf_pages_{local_snapshot_id}"

    try:
        for page_index, page in enumerate(reader.pages):
            page_number = page_index + 1
            extracted_text = (page.extract_text() or "").strip()

            # Strong enough text page: use direct extraction only.
            if len(extracted_text) >= pdf_ocr_min_chars:
                page_texts.append(extracted_text)
                continue

            # Weak or empty page
            if not enable_ocr:
                page_texts.append(extracted_text)
                continue

            ocr_required_pages.append(page_number)

            rendered_image_path = _render_pdf_page_to_image(
                pdf_path=file_path,
                page_index=page_index,
                output_dir=rendered_pages_dir,
            )

            ocr_result = run_remote_ocr(rendered_image_path)
            ocr_text = (ocr_result.get("text") or "").strip()

            if ocr_result.get("success") and ocr_text:
                page_texts.append(ocr_text)
                ocr_used = True
                ocr_pages.append(page_number)
            else:
                ocr_failed_pages.append(page_number)
                ocr_failure_messages.append(
                    ocr_result.get("message", f"OCR failed for page {page_number}.")
                )
                # Keep weak direct extraction only for debugging context,
                # but fail the ingest later so we do not silently accept a bad PDF.
                page_texts.append(extracted_text)
    finally:
        # Rendered OCR pages are temp local runtime artifacts only.
        shutil.rmtree(rendered_pages_dir, ignore_errors=True)

    if ocr_failed_pages:
        failed_pages_text = ", ".join(str(page) for page in ocr_failed_pages)
        failure_reason = ocr_failure_messages[0]
        raise RuntimeError(
            "OCR was required for PDF pages "
            f"{failed_pages_text}, but it failed. {failure_reason}"
        )

    merged_text = "\n\n".join(text for text in page_texts if text.strip()).strip()
    content_hash = build_content_hash(merged_text)
    document_id = build_portable_document_id(
        file_name=path.name,
        extension=".pdf",
        text=merged_text,
    )

    metadata = {
        "source_path": str(path.resolve()),
        "size_bytes": path.stat().st_size,
        "page_count": page_count,
        "ocr_required_pages": ocr_required_pages,
        "ocr_pages": ocr_pages,
        "pdf_ocr_min_chars": pdf_ocr_min_chars,
    }

    return ExtractedDocument(
        document_id=document_id,
        source_ref=build_source_ref(file_path),
        content_hash=content_hash,
        local_file_path=str(path.resolve()),
        file_name=path.name,
        extension=".pdf",
        text=merged_text,
        metadata=metadata,
        ocr_used=ocr_used,
    )