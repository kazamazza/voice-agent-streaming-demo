from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Pydantic v2 style settings config
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Core
    redis_url: str = "redis://localhost:6379/0"
    log_level: str = "INFO"

    # LLM wiring (for later milestones)
    llm_provider: str = "stub"  # "stub" | "openai"
    openai_api_key: str = ""
