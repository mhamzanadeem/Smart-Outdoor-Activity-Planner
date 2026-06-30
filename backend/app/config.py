"""
Application configuration loaded from environment variables.
"""
from __future__ import annotations

import logging
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralized application settings."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Weather API (OpenWeatherMap - free tier compatible)
    weather_api_key: str = Field(default="", alias="WEATHER_API_KEY")
    weather_api_base_url: str = Field(
        default="https://api.openweathermap.org/data/2.5", alias="WEATHER_API_BASE_URL"
    )

    # Open-source LLM API (e.g. Groq, Together, Ollama-compatible endpoint)
    llm_api_key: str = Field(default="", alias="LLM_API_KEY")
    llm_api_base_url: str = Field(default="https://api.groq.com/openai/v1", alias="LLM_API_BASE_URL")
    llm_model_name: str = Field(default="llama-3.1-8b-instant", alias="LLM_MODEL_NAME")
    llm_temperature: float = Field(default=0.3, alias="LLM_TEMPERATURE")

    # App
    app_env: str = Field(default="development", alias="APP_ENV")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    cors_origins: str = Field(default="http://localhost:5173", alias="CORS_ORIGINS")
    request_timeout_seconds: int = Field(default=20, alias="REQUEST_TIMEOUT_SECONDS")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


def configure_logging() -> None:
    settings = get_settings()
    logging.basicConfig(
        level=settings.log_level.upper(),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )
