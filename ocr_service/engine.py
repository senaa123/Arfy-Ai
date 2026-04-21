import os
from pathlib import Path

from dotenv import load_dotenv

from ocr_service.preprocess import preprocess_image_for_ocr

env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(env_path)


def run_ocr_on_image(image_path: str) -> tuple[str, dict]:
    """
    Run OCR on a single image.

    Returns:
    - extracted text
    - metadata dict

    OCR is isolated here so the rest of the system does not care
    which OCR engine is being used.
    """
    processed_path = preprocess_image_for_ocr(image_path)

    try:
        from PIL import Image
    except Exception as e:
        raise RuntimeError(
            "Pillow is not installed. OCR service cannot read images."
        ) from e

    try:
        import pytesseract

        # Prefer an explicit override, otherwise let PATH resolve the install so
        # OCR service stays portable across local machines.
        configured_cmd = (os.getenv("TESSERACT_CMD") or "").strip()
        if configured_cmd:
            pytesseract.pytesseract.tesseract_cmd = configured_cmd
    except Exception as e:
        raise RuntimeError(
            "pytesseract is not installed. OCR service cannot run OCR."
        ) from e

    try:
        with Image.open(processed_path) as image:
            text = pytesseract.image_to_string(image)
    except pytesseract.TesseractNotFoundError as e:
        raise RuntimeError(
            "Tesseract OCR executable is not installed or not on PATH."
        ) from e

    return text.strip(), {
        "processed_path": processed_path,
    }
