import os
from pathlib import Path

import requests
from dotenv import load_dotenv

# Load env from document_service/.env
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(env_path)

OCR_SERVICE_URL = os.getenv("OCR_SERVICE_URL", "http://127.0.0.1:8003")


def run_remote_ocr(image_path: str, timeout: int = 30) -> dict:
    """
    Call OCR service for a single image.

    document_service owns the routing decision.
    OCR service only does OCR work.
    """
    try:
        response = requests.post(
            f"{OCR_SERVICE_URL}/ocr/image",
            json={"image_path": image_path},
            timeout=timeout,
        )

        payload = {}
        try:
            payload = response.json()
        except Exception:
            payload = {}

        if response.ok:
            return payload

        # Keep OCR-runtime failures readable for document_service instead of
        # collapsing them into a generic requests exception.
        return {
            "success": False,
            "message": payload.get(
                "message",
                f"OCR service returned HTTP {response.status_code}.",
            ),
            "text": payload.get("text", ""),
            "metadata": payload.get("metadata", {}),
        }

    except requests.Timeout:
        return {
            "success": False,
            "message": "OCR service timed out.",
            "text": "",
        }
    except requests.RequestException as e:
        return {
            "success": False,
            "message": f"Could not reach OCR service: {e}",
            "text": "",
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Unexpected OCR client error: {e}",
            "text": "",
        }
