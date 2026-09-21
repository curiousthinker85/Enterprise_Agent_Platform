from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central, typed configuration for the API and model gateway."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Enterprise Agent Platform"
    app_version: str = "0.1.0"
    environment: Literal["dev", "staging", "prod"] = "dev"
    log_level: str = "INFO"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    default_llm_provider: str = "openai"
    default_llm_model: str = "gpt-4o-mini"
    default_llm_api_key: str | None = None
    default_llm_api_base: str | None = None
    default_llm_api_version: str | None = None

    llm_temperature: float = 0.1
    llm_max_tokens: int | None = 1024
    request_timeout_seconds: int = 60
    database_url: str = "sqlite:///./app.db"
    upload_storage_path: str = "storage/uploads"
    vector_storage_path: str = "storage/vector_db"
    auth_secret_key: str = "change-this-development-secret-before-production"
    auth_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440


@lru_cache
def get_settings() -> Settings:
    return Settings()
