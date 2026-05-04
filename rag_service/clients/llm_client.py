"""
LLM client for grounded answer generation.

This keeps provider-specific HTTP code out of the workflow and answer builder.
"""

from __future__ import annotations

import requests

from rag_service.config import settings


class LLMClient:
    """
    Minimal OpenAI-compatible chat client.

    This is intentionally small and provider-agnostic.
    """

    def __init__(self) -> None:
        self.base_url = settings.LLM_BASE_URL
        self.api_key = settings.LLM_API_KEY
        self.model = settings.LLM_MODEL
        self.chat_url = f"{self.base_url}/chat/completions"

    def generate_answer(self, *, system_prompt: str, user_prompt: str) -> str:
        """
        Generate a grounded answer from supplied evidence context.

        Raises clearly if no API key is configured.
        """
        if not self.api_key:
            raise RuntimeError("RAG_LLM_API_KEY is not configured.")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }

        response = requests.post(
            self.chat_url,
            headers=headers,
            json=payload,
            timeout=settings.REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()

        data = response.json()
        choices = data.get("choices", [])
        if not choices:
            raise RuntimeError("LLM response did not contain any choices.")

        message = choices[0].get("message", {}) or {}
        content = (message.get("content") or "").strip()
        if not content:
            raise RuntimeError("LLM returned an empty answer.")

        return content