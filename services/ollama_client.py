"""Async Ollama HTTP client with JSON-mode support and structured errors."""

from __future__ import annotations

import json as jsonlib
from typing import Any, Optional

import httpx


class OllamaError(RuntimeError):
    """Raised when Ollama is unreachable, times out, returns non-2xx, or returns malformed payload."""


class OllamaClient:
    def __init__(self, base_url: str, model: str, timeout: float = 60.0) -> None:
        self._base = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout

    async def is_alive(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=3.0) as c:
                r = await c.get(f"{self._base}/api/tags")
            return r.status_code == 200
        except (httpx.HTTPError, httpx.TimeoutException):
            return False

    async def generate(
        self,
        prompt: str,
        *,
        system: Optional[str] = None,
        temperature: float = 0.7,
        num_predict: int = 600,
        json_mode: bool = False,
    ) -> str:
        payload: dict[str, Any] = {
            "model": self._model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": num_predict},
        }
        if system:
            payload["system"] = system
        if json_mode:
            payload["format"] = "json"
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as c:
                r = await c.post(f"{self._base}/api/generate", json=payload)
            r.raise_for_status()
            data = r.json()
            return data["response"]
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            raise OllamaError(f"Ollama unreachable: {type(e).__name__}: {e}") from e
        except httpx.HTTPStatusError as e:
            raise OllamaError(f"Ollama HTTP {e.response.status_code}: {e.response.text[:200]}") from e
        except (KeyError, ValueError) as e:
            raise OllamaError(f"Ollama returned malformed payload: {e}") from e

    async def generate_json(
        self,
        prompt: str,
        *,
        system: Optional[str] = None,
        temperature: float = 0.2,
        num_predict: int = 1500,
    ) -> dict[str, Any]:
        """Generate and parse JSON. Raises OllamaError if response isn't valid JSON."""
        raw = await self.generate(
            prompt,
            system=system,
            temperature=temperature,
            num_predict=num_predict,
            json_mode=True,
        )
        try:
            return jsonlib.loads(raw)
        except jsonlib.JSONDecodeError as e:
            # try to salvage: find first `{` and last `}`
            start = raw.find("{")
            end = raw.rfind("}")
            if start != -1 and end > start:
                try:
                    return jsonlib.loads(raw[start : end + 1])
                except jsonlib.JSONDecodeError:
                    pass
            raise OllamaError(f"Ollama JSON parse failed: {e}; raw[:200]={raw[:200]!r}") from e
