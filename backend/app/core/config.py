"""
SEPEHR Backend — Core Configuration
"""

from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── App ───────────────────────────────────────────────
    APP_NAME: str = "SEPEHR"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: Literal["development", "staging", "production"] = "production"
    DEBUG: bool = False
    SECRET_KEY: str
    ALLOWED_HOSTS: list[str] = ["*"]
    CORS_ORIGINS: list[str] = []

    # ── Database ──────────────────────────────────────────
    DATABASE_URL: str
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    DB_ECHO: bool = False

    # ── Redis ─────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_POOL_SIZE: int = 50

    # ── Auth ──────────────────────────────────────────────
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # ── MinIO ─────────────────────────────────────────────
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str
    MINIO_SECRET_KEY: str
    MINIO_BUCKET_MEDIA: str = "sepehr-media"
    MINIO_BUCKET_VOICE: str = "sepehr-voice"
    MINIO_BUCKET_FILES: str = "sepehr-files"
    MINIO_SECURE: bool = False

    # ── Rate Limiting ─────────────────────────────────────
    RATE_LIMIT_AUTH: str = "10/minute"
    RATE_LIMIT_API: str = "100/minute"
    RATE_LIMIT_UPLOAD: str = "30/minute"
    RATE_LIMIT_WS: str = "200/minute"

    # ── File Uploads ──────────────────────────────────────
    MAX_IMAGE_SIZE_MB: int = 10
    MAX_VOICE_SIZE_MB: int = 25
    MAX_FILE_SIZE_MB: int = 50
    ALLOWED_IMAGE_TYPES: list[str] = ["image/jpeg", "image/png", "image/webp", "image/gif"]
    ALLOWED_AUDIO_TYPES: list[str] = ["audio/ogg", "audio/mp4", "audio/webm", "audio/mpeg"]

    # ── Celery ────────────────────────────────────────────
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # ── Security ──────────────────────────────────────────
    BCRYPT_ROUNDS: int = 12
    ARGON2_TIME_COST: int = 3
    ARGON2_MEMORY_COST: int = 65536
    ARGON2_PARALLELISM: int = 4

    # ── Pagination ────────────────────────────────────────
    DEFAULT_PAGE_SIZE: int = 30
    MAX_PAGE_SIZE: int = 100

    # ── WebSocket ─────────────────────────────────────────
    WS_HEARTBEAT_INTERVAL: int = 30
    WS_MAX_CONNECTIONS_PER_USER: int = 5

    # ── Admin ─────────────────────────────────────────────
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str  # Must be set in .env

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_db_url(cls, v: str) -> str:
        if not v.startswith(("postgresql+asyncpg://", "postgresql://")):
            raise ValueError("DATABASE_URL must use postgresql+asyncpg:// scheme")
        # Ensure asyncpg driver
        if v.startswith("postgresql://"):
            v = v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
