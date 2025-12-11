"""
Application Settings

Centralized configuration management using Pydantic Settings.
All configuration is loaded from environment variables with sensible defaults.

Configuration Categories:
=========================
- Application: Basic app info (name, version, debug mode)
- Server: Host and port settings
- Database: PostgreSQL connection and pool settings
- Security: JWT and authentication settings
- CORS: Cross-origin resource sharing
- External Services: OpenAI, AWS, Redis, Qdrant

Environment Variables:
======================
Settings are loaded from environment variables or .env file.
Environment variables take precedence over .env file values.

Usage:
======
    from src.config.settings import settings

    # Access settings
    db_url = settings.DATABASE_URL
    is_dev = settings.is_development
"""

from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    All settings can be overridden via environment variables.
    Use .env file for local development.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    # ═══════════════════════════════════════════════════════════════════════════════
    # APPLICATION
    # ═══════════════════════════════════════════════════════════════════════════════

    APP_NAME: str = "Dora"
    APP_VERSION: str = "1.0.0"
    APP_ENV: str = "development"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # ═══════════════════════════════════════════════════════════════════════════════
    # SERVER
    # ═══════════════════════════════════════════════════════════════════════════════

    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # ═══════════════════════════════════════════════════════════════════════════════
    # DATABASE
    # ═══════════════════════════════════════════════════════════════════════════════

    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/dora",
        description="PostgreSQL connection URL (use asyncpg driver for async)",
    )
    DATABASE_POOL_SIZE: int = Field(
        default=10,
        description="Number of persistent connections in the pool",
    )
    DATABASE_MAX_OVERFLOW: int = Field(
        default=20,
        description="Extra connections allowed when pool is exhausted",
    )

    # ═══════════════════════════════════════════════════════════════════════════════
    # SECURITY
    # ═══════════════════════════════════════════════════════════════════════════════

    SECRET_KEY: str = Field(
        default="change-me-in-production",
        description="Secret key for JWT token signing",
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=10080,  # 7 days
        description="JWT access token expiry in minutes",
    )
    JWT_ALGORITHM: str = "HS256"

    # ═══════════════════════════════════════════════════════════════════════════════
    # CORS
    # ═══════════════════════════════════════════════════════════════════════════════

    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173"],
        description="Allowed CORS origins",
    )

    # ═══════════════════════════════════════════════════════════════════════════════
    # EXTERNAL SERVICES - OpenAI
    # ═══════════════════════════════════════════════════════════════════════════════

    OPENAI_API_KEY: str = Field(
        default="",
        description="OpenAI API key for AI processing",
    )

    # ═══════════════════════════════════════════════════════════════════════════════
    # EXTERNAL SERVICES - AWS
    # ═══════════════════════════════════════════════════════════════════════════════

    AWS_REGION: str = "us-east-1"
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""

    # SQS Queues
    SQS_CONTENT_QUEUE_URL: str = Field(
        default="",
        description="SQS queue URL for content processing jobs",
    )
    SQS_CLUSTERING_QUEUE_URL: str = Field(
        default="",
        description="SQS queue URL for clustering jobs",
    )

    # ═══════════════════════════════════════════════════════════════════════════════
    # EXTERNAL SERVICES - Vector Database
    # ═══════════════════════════════════════════════════════════════════════════════

    QDRANT_URL: str = Field(
        default="http://localhost:6333",
        description="Qdrant vector database URL",
    )
    QDRANT_API_KEY: str = ""

    # ═══════════════════════════════════════════════════════════════════════════════
    # EXTERNAL SERVICES - Redis
    # ═══════════════════════════════════════════════════════════════════════════════

    REDIS_URL: str = Field(
        default="redis://localhost:6379",
        description="Redis connection URL for caching",
    )

    # ═══════════════════════════════════════════════════════════════════════════════
    # PROPERTIES
    # ═══════════════════════════════════════════════════════════════════════════════

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.APP_ENV == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.APP_ENV == "development"


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Uses lru_cache to ensure settings are only loaded once.
    This is more efficient than creating a new instance every time.

    Returns:
        Settings: Application settings instance
    """
    return Settings()


# Global settings instance for convenient import
settings = get_settings()
