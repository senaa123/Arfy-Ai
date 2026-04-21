# ocr_service/routes/ocr.py

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ocr_service.engine import run_ocr_on_image
from ocr_service.schemas import OCRImageRequest, OCRImageResponse

router = APIRouter(tags=["ocr"])


@router.post("/ocr/image", response_model=OCRImageResponse)
async def ocr_image(req: OCRImageRequest):
    """
    OCR one image file and return plain text.

    Phase 4B:
    - route moved out of main.py only
    - OCR execution still belongs to engine.py
    """
    try:
        text, metadata = run_ocr_on_image(req.image_path)

        return OCRImageResponse(
            success=True,
            message="OCR completed successfully.",
            text=text,
            image_path=req.image_path,
            metadata=metadata,
        )

    except Exception as e:
        return JSONResponse(
            status_code=400,
            content=OCRImageResponse(
                success=False,
                message=str(e),
                text="",
                image_path=req.image_path,
            ).model_dump(),
        )