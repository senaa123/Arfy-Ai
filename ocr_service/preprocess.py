from pathlib import Path


def preprocess_image_for_ocr(image_path: str) -> str:
    """
    Optional preprocessing hook before OCR.

    For now we keep this very light:
    - validate that the file exists
    - return the same path

    Later you can add:
    - grayscale conversion
    - thresholding
    - denoising
    - deskewing

    We isolate this in its own file so OCR logic stays clean.
    """
    path = Path(image_path)

    if not path.exists():
        raise FileNotFoundError(f"Image file not found: {image_path}")

    if not path.is_file():
        raise ValueError(f"Path is not a file: {image_path}")

    return str(path.resolve())