"""
AI Stock Analyzer - Application Configuration
Menggunakan Pydantic Settings untuk membaca environment variables dari file .env
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Konfigurasi utama aplikasi.
    Semua nilai akan dibaca dari environment variables atau file .env.
    """

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True, extra="ignore"
    )

    # ----- Application -----
    APP_NAME: str = "AI Stock Analyzer"
    APP_ENV: str = "development"
    DEBUG: bool = True

    # ----- Database (PostgreSQL) -----
    DATABASE_URL: str
    SYNC_DATABASE_URL: str

    # ----- Security (JWT) -----
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 jam
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ----- Anthropic AI -----
    AI_PROVIDER: Literal["anthropic", "gemini"] = "anthropic"
    ANTHROPIC_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"
    AI_MODEL_OPERATIONAL: str = "claude-sonnet-4-6"
    AI_MODEL_STRATEGIC: str = "claude-opus-4-6"

    # ----- Redis (Celery Broker + Cache) -----
    REDIS_URL: str = "redis://localhost:6379/0"

    # ----- Market Data -----
    ALPACA_API_KEY: str = ""
    ALPACA_SECRET_KEY: str = ""
    MARKET_DATA_PROVIDER: Literal["yahoo", "eodhd"] = "yahoo"
    EODHD_API_KEY: str = ""
    EOD_PUBLICATION_DELAY_MINUTES: int | None = Field(default=None, ge=0, le=1440)
    MARKET_CALENDAR_VERIFIED: bool = False
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""
    APP_PUBLIC_URL: str = "http://localhost:3000"

    # ----- CORS -----
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse string CORS origins menjadi list."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]


@lru_cache
def get_settings() -> Settings:
    """
    Menggunakan lru_cache agar Settings hanya dibuat sekali selama lifecycle aplikasi.
    """
    return Settings()


# Ekspor instance settings untuk diimpor di modul lain
settings = get_settings()
