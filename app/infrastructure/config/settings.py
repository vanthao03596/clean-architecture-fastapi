"""Application settings using pydantic-settings."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration - single source of truth.

    All settings loaded from environment variables or .env files.

    Usage:
        settings = get_settings()
        print(settings.database_url)
        print(settings.secret_key)
    """

    # Database
    db_host: str = Field(default="localhost")
    db_port: int = Field(default=5432)
    db_user: str = Field(default="postgres")
    db_password: str = Field(default="postgres")
    db_name: str = Field(default="fastapi_db")
    db_echo: bool = Field(default=False)
    db_pool_size: int = Field(default=5)
    db_max_overflow: int = Field(default=10)

    # Security
    secret_key: str = Field(default="", min_length=32)
    algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=30)
    refresh_token_expire_days: int = Field(default=7)
    refresh_token_overlap_seconds: int = Field(
        default=5,
        description="Overlap period for refresh token rotation (Auth0-style). "
        "Previous token remains valid for this many seconds to handle "
        "network latency and concurrent requests without triggering breach detection.",
    )

    # Application
    environment: Literal["dev", "prod", "test"] = Field(default="dev")
    debug: bool = Field(default=False)
    app_name: str = Field(default="Clean Architecture FastAPI")
    app_version: str = Field(default="1.0.0")

    # CORS
    cors_origins: str = Field(default="http://localhost:3000")

    # Logging
    log_level: str = Field(default="INFO")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """Ensure secret_key is provided and meets requirements."""
        if not v or len(v) < 32:
            raise ValueError(
                "SECRET_KEY must be set in environment and be at least 32 characters long"
            )
        return v

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse comma-separated CORS origins into a list."""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def database_url(self) -> str:
        """Build async PostgreSQL URL."""
        return f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    @property
    def database_url_sync(self) -> str:
        """Build sync PostgreSQL URL (for Alembic)."""
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment == "prod"

    @property
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.environment == "dev"

    @property
    def is_testing(self) -> bool:
        """Check if running in test mode."""
        return self.environment == "test"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance.

    Settings are loaded once and cached for the application lifecycle.
    For testing, clear the cache with: get_settings.cache_clear()

    Returns:
        Settings instance loaded from environment
    """
    return Settings()
