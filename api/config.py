"""Runtime configuration via environment variables."""

from __future__ import annotations

import os
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore")

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "info"

    # CORS
    cors_origins: str = "http://localhost:5173,http://localhost:3000"
    cors_origin_regex: str = r"^https://([a-z0-9-]+\.)*ngrok-free\.app$"

    # Ollama
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "mistral"
    ollama_timeout: float = 60.0

    # Data
    jobs_path: str = "jobs.json"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
