"""Validated, environment-backed settings for local development."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, HttpUrl, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Validated local service configuration."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", frozen=True)

    app_env: Literal["development", "test", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    ollama_base_url: HttpUrl = HttpUrl("http://127.0.0.1:11434")
    ollama_model: str = Field(default="qwen3:4b-instruct", min_length=1)
    qdrant_url: HttpUrl = HttpUrl("http://127.0.0.1:6333")
    embedding_model: str = Field(default="intfloat/multilingual-e5-small", min_length=1)
    rag_collection: str = Field(default="synthetic_policies_e5_small_v1", min_length=1)
    rag_min_score: float = Field(default=0.805, ge=0, le=1)
    rag_chunk_target_chars: int = Field(default=650, ge=200, le=4000)
    rag_chunk_overlap_chars: int = Field(default=80, ge=0, le=500)
    rag_top_k: int = Field(default=5, ge=1, le=10)
    database_url: SecretStr | None = None
    demo_api_token: SecretStr | None = None
    max_question_chars: int = Field(default=4000, ge=1, le=20000)
    request_timeout_seconds: int = Field(default=30, ge=1, le=120)


@lru_cache
def get_settings() -> Settings:
    """Load settings once per process; clear cache when changing environment in tests."""

    return Settings()
