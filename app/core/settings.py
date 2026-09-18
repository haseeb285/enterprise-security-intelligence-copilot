"""Validated, environment-backed settings for local development."""

from functools import lru_cache
from typing import Literal
from urllib.parse import urlparse

from pydantic import Field, HttpUrl, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Validated local service configuration."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", frozen=True)

    app_env: Literal["development", "test", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    ollama_base_url: HttpUrl = HttpUrl("http://127.0.0.1:11434")
    ollama_model: str = Field(default="qwen3.5:4b", min_length=1)
    llm_timeout_seconds: int = Field(default=180, ge=5, le=600)
    llm_temperature: float = Field(default=0.1, ge=0, le=2)
    llm_context_length: int = Field(default=4096, ge=512, le=16384)
    llm_max_output_tokens: int = Field(default=384, ge=16, le=2048)
    llm_keep_alive: str = Field(default="1m", min_length=1)
    qdrant_url: HttpUrl = HttpUrl("http://127.0.0.1:6333")
    embedding_model: str = Field(default="intfloat/multilingual-e5-small", min_length=1)
    rag_collection: str = Field(default="synthetic_policies_e5_small_v1", min_length=1)
    rag_min_score: float = Field(default=0.805, ge=0, le=1)
    rag_chunk_target_chars: int = Field(default=650, ge=200, le=4000)
    rag_chunk_overlap_chars: int = Field(default=80, ge=0, le=500)
    rag_top_k: int = Field(default=5, ge=1, le=10)
    database_url: SecretStr | None = None
    demo_api_token: SecretStr | None = None
    demo_read_token: SecretStr | None = None
    cors_origins: list[str] = Field(default_factory=list)
    max_question_chars: int = Field(default=4000, ge=1, le=20000)
    request_timeout_seconds: int = Field(default=30, ge=1, le=120)

    @field_validator("cors_origins")
    @classmethod
    def restricted_cors(cls, value: list[str]) -> list[str]:
        for origin in value:
            parsed = urlparse(origin)
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.netloc
                or parsed.path
                or parsed.query
                or parsed.fragment
                or parsed.username
                or parsed.password
            ):
                raise ValueError("CORS_ORIGINS must contain explicit HTTP(S) origins")
        return value


@lru_cache
def get_settings() -> Settings:
    """Load settings once per process; clear cache when changing environment in tests."""

    return Settings()
