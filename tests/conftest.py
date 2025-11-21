"""Pytest configuration and fixtures.

This file contains shared fixtures that can be used across all tests.

These fixtures follow the Dependency Inversion Principle:
- Use fake implementations (FakePasswordHasher, FakeUnitOfWork)
- Tests run fast (no real crypto, no database)
- Tests are isolated (each test gets fresh fakes)
"""

from datetime import UTC, datetime

import pytest

from app.application.services.user_service import UserService
from app.domain.entities.user import User
from tests.fakes.password_hasher_fake import FakePasswordHasher
from tests.fakes.token_repository_fake import FakeTokenRepository
from tests.fakes.token_service_fake import FakeTokenService
from tests.fakes.unit_of_work_fake import FakeUnitOfWork


@pytest.fixture
def fake_password_hasher() -> FakePasswordHasher:
    """
    Provide a FakePasswordHasher for tests.

    This fake hasher is fast and predictable, making tests easier to write.
    """
    return FakePasswordHasher()


@pytest.fixture
def sample_user() -> User:
    """
    Create a sample user for testing.

    The password_hash uses the FakePasswordHasher format: "HASHED:password123"
    This makes it easy to verify in tests.
    """
    return User(
        id=1,
        email="test@example.com",
        name="Test User",
        password_hash="HASHED:password123",  # FakePasswordHasher format
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture
def another_user() -> User:
    """Create another sample user for testing."""
    return User(
        id=2,
        email="another@example.com",
        name="Another User",
        password_hash="HASHED:password456",  # FakePasswordHasher format
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture
def fake_uow():
    """
    Provide a fresh FakeUnitOfWork for each test.

    This ensures tests are isolated and don't affect each other.
    """
    return FakeUnitOfWork()


@pytest.fixture
def fake_uow_with_users(sample_user, another_user):
    """
    Provide a FakeUnitOfWork pre-populated with users.

    Useful for testing operations on existing data.
    """
    return FakeUnitOfWork(initial_users=[sample_user, another_user])


@pytest.fixture
def user_service(fake_uow, fake_password_hasher):
    """
    Provide a UserService instance with fake dependencies.

    This allows testing the service layer in isolation:
    - No database (FakeUnitOfWork)
    - No real crypto (FakePasswordHasher)

    Tests run fast and are fully deterministic.
    """

    def uow_factory():
        return fake_uow

    return UserService(uow_factory=uow_factory, password_hasher=fake_password_hasher)


@pytest.fixture
def user_service_with_data(fake_uow_with_users, fake_password_hasher):
    """
    Provide a UserService with pre-populated data.

    Useful for testing operations on existing users.
    """

    def uow_factory():
        return fake_uow_with_users

    return UserService(uow_factory=uow_factory, password_hasher=fake_password_hasher)


@pytest.fixture
def fake_token_service() -> FakeTokenService:
    """
    Provide a FakeTokenService for tests.

    This fake token service generates predictable tokens and
    stores them in memory for fast testing.
    """
    return FakeTokenService()


@pytest.fixture
def fake_token_repository() -> FakeTokenRepository:
    """
    Provide a FakeTokenRepository for tests.

    This fake repository stores token metadata in memory,
    making tests fast and isolated.
    """
    return FakeTokenRepository()
