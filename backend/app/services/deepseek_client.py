import json
from typing import Any

import httpx

from app.config import Settings


class LLMNotConfiguredError(RuntimeError):
    pass


class DeepSeekClient:
    def __init__(self, settings: Settings) -> None:
        self.base_url = settings.deepseek_base_url.rstrip("/")
        self.model = settings.deepseek_model
        self.api_key = settings.deepseek_api_key

    def chat_json(self, messages: list[dict[str, str]], *, timeout: int) -> dict[str, Any]:
        if not self.api_key:
            raise LLMNotConfiguredError("DEEPSEEK_API_KEY is not configured")

        url = f"{self.base_url}/chat/completions"
        response = httpx.post(
            url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "messages": messages,
                "response_format": {"type": "json_object"},
            },
            timeout=timeout,
        )
        response.raise_for_status()
        body = response.json()
        choices = body.get("choices")
        if not isinstance(choices, list) or not choices:
            raise ValueError("DeepSeek response did not contain choices")
        content = choices[0].get("message", {}).get("content")
        if not isinstance(content, str):
            raise ValueError("DeepSeek response content was not a string")
        parsed = json.loads(content)
        if not isinstance(parsed, dict):
            raise ValueError("DeepSeek JSON response must be an object")
        return parsed
