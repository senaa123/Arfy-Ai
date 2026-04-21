from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class OCRImageRequest(BaseModel):
    """
    OCR request for one image file.

    Phase 2 Version B design:
    - document_service sends a rendered page image or a normal image file
    - OCR service returns extracted text only
    """

    image_path: str


class OCRImageResponse(BaseModel):
    """
    OCR response for one image file.
    """

    success: bool
    message: str

    text: str = ""
    image_path: Optional[str] = None

    metadata: Dict[str, Any] = Field(default_factory=dict)