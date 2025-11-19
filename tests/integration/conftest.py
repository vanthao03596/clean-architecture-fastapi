"""Integration test fixtures.

Provides fixtures for integration testing with real database and FastAPI client.
Uses SQLite in-memory database for fast, isolated tests.
"""

import pytest
import pytest_asyncio
from typing import AsyncGenerator, Generator
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)

from app.main import app
from app.infrastructure.persistence.database import Base
from app.infrastructure.config.settings import Settings
from app.presentation.dependencies import get_session_factory


# Test database URL (SQLite in-memory)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def test_engine() -> AsyncGenerator[AsyncEngine, None]:
    """Create a test database engine using SQLite in-memory."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        future=True,
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Drop all tables after test
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def test_session_factory(test_engine: AsyncEngine):
    """Create a test session factory."""
    return async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )


@pytest_asyncio.fixture
async def test_session(test_session_factory) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    async with test_session_factory() as session:
        yield session


@pytest.fixture
def client(test_session_factory) -> Generator[TestClient, None, None]:
    """
    Create a FastAPI test client with test database.

    This client uses the real application but with an in-memory database.
    """

    # Override the session factory dependency
    def override_get_session_factory():
        return test_session_factory

    app.dependency_overrides[get_session_factory] = override_get_session_factory

    with TestClient(app) as test_client:
        yield test_client

    # Clean up overrides
    app.dependency_overrides.clear()
