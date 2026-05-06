"""FastAPI dependencies."""

from __future__ import annotations

from typing import Optional

from fastapi import Depends

from api.config import Settings, get_settings
from services.ollama_client import OllamaClient


def get_ollama(settings: Settings = Depends(get_settings)) -> OllamaClient:
    return OllamaClient(
        base_url=settings.ollama_url,
        model=settings.ollama_model,
        timeout=settings.ollama_timeout,
    )


async def get_ollama_or_none(
    settings: Settings = Depends(get_settings),
) -> Optional[OllamaClient]:
    """Returns the client if Ollama is alive, else None — letting callers fall back gracefully."""
    client = OllamaClient(
        base_url=settings.ollama_url,
        model=settings.ollama_model,
        timeout=settings.ollama_timeout,
    )
    if await client.is_alive():
        return client
    return None
