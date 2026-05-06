"""Health, readiness, version endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from api.config import Settings, get_settings
from api.schemas import HealthResponse, ReadyResponse, VersionResponse
from services.ollama_client import OllamaClient


router = APIRouter()


@router.get("/healthz", response_model=HealthResponse, tags=["health"])
def healthz() -> HealthResponse:
    """Liveness — process is up."""
    return HealthResponse()


@router.get("/readyz", response_model=ReadyResponse, tags=["health"])
async def readyz(settings: Settings = Depends(get_settings)) -> ReadyResponse:
    """Readiness — required dependencies are reachable."""
    client = OllamaClient(
        base_url=settings.ollama_url,
        model=settings.ollama_model,
        timeout=3.0,
    )
    components: dict[str, str] = {
        "ollama": "ok" if await client.is_alive() else "unreachable",
    }
    overall = "ready" if all(v == "ok" for v in components.values()) else "degraded"
    return ReadyResponse(status=overall, components=components)


@router.get("/v1/version", response_model=VersionResponse, tags=["health"])
def version() -> VersionResponse:
    return VersionResponse(name="applica-smart-server", version="1.0.0", api="v1")
