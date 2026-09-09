"""
Backend Configuration Management.
Leverages pydantic-settings to validate environment variables with secure defaults.
"""

from typing import List, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application Settings."""
    APP_NAME: str = "AegisOps - Autonomous AI Operations Center"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # CORS
    CORS_ORIGINS: Union[str, List[str]] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
    ]

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/aegisops"
    DATABASE_URL_SYNC: str = "postgresql://postgres:postgres@localhost:5432/aegisops"
    DB_FALLBACK_SQLITE: bool = True

    # AI & LLM settings
    LLM_PROVIDER: str = "mock"
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    LLM_MODEL_NAME: str = "gpt-4o-mini"
    ANOMALY_DETECTION_CONTAMINATION: float = 0.05

    # Monitoring & Telemetry
    METRICS_POLL_INTERVAL_SECONDS: float = 2.0
    LOG_LEVEL: str = "INFO"

    @field_validator("CORS_ORIGINS", mode="before")
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
