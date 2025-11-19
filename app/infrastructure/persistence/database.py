"""Database configuration and session management."""

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
    AsyncEngine,
)
from sqlalchemy.orm import DeclarativeBase

from app.infrastructure.config.settings import Settings


# Base class for all ORM models
class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    pass


def create_database_engine(settings: Settings) -> AsyncEngine:
    """Create SQLAlchemy async engine from settings.

    Args:
        settings: Application settings containing database configuration

    Returns:
        Configured AsyncEngine instance
    """
    return create_async_engine(
        settings.database_url,
        echo=settings.db_echo,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        future=True,
    )


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Create async session factory from engine.

    Args:
        engine: SQLAlchemy async engine

    Returns:
        Session factory that creates AsyncSession instances
    """
    return async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
