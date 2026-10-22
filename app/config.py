from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed configuration loaded from environment variables (and .env if present)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://supportdesk:supportdesk@localhost:5432/supportdesk"
    redis_url: str = "redis://localhost:6379/0"
    agent_api_key: str = Field(min_length=16)
    ai_provider: Literal["auto", "anthropic", "rules"] = "auto"
    anthropic_api_key: str = ""
    ai_model: str = "claude-haiku-5-5"
    queue_name: str = "triage"

    @field_validator("database_url")
    @classmethod
    def use_psycopg_driver(cls, url: str) -> str:
        """Hosting platforms hand out postgres:// URLs; SQLAlchemy needs the driver named."""
        for prefix in ("postgres://", "postgresql://"):
            if url.startswith(prefix):
                return "postgresql+psycopg://" + url[len(prefix) :]
        return url


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
