"""Unit tests for AuthService.

Tests authentication use cases:
1. Login (credential validation + token generation)
2. Token refresh with overlap period logic
3. Get current user from token
"""

from datetime import UTC, datetime, timedelta

import pytest

from app.application.dtos.auth_dto import LoginDTO, RefreshTokenDTO
from app.application.exceptions.exceptions import (
    InvalidCredentialsError,
    InvalidTokenError,
    UserNotFoundError,
)
from app.application.services.auth_service import AuthService
from app.domain.entities.user import User
from app.domain.repositories.token_repository import TokenMetadata
from tests.fakes.unit_of_work_fake import FakeUnitOfWork

pytestmark = pytest.mark.unit


@pytest.fixture
def sample_user() -> User:
    """Create a sample user with FakePasswordHasher format."""
    return User(
        id=1,
        email="test@example.com",
        name="Test User",
        password_hash="HASHED:password123",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture
def fake_uow_with_user(sample_user):
    """Provide UnitOfWork with a user."""
    return FakeUnitOfWork(initial_users=[sample_user])


@pytest.fixture
def auth_service(
    fake_uow_with_user, fake_token_service, fake_token_repository, fake_password_hasher
):
    """Provide AuthService with fake dependencies."""

    def uow_factory():
        return fake_uow_with_user

    return AuthService(
        uow_factory=uow_factory,
        token_service=fake_token_service,
        token_repository=fake_token_repository,
        password_hasher=fake_password_hasher,
        access_token_expire_minutes=30,
        refresh_token_expire_days=7,
        refresh_token_overlap_seconds=5,
    )


# === LOGIN TESTS ===


@pytest.mark.asyncio
async def test_login_success(auth_service, sample_user):
    """Test successful login returns tokens."""
    # Arrange
    login_dto = LoginDTO(email="test@example.com", password="password123")

    # Act
    result = await auth_service.login(login_dto)

    # Assert
    assert result.access_token.startswith("access_")
    assert result.refresh_token.startswith("refresh_")
    assert result.token_type == "bearer"
    assert result.expires_in == 30 * 60  # 30 minutes in seconds


@pytest.mark.asyncio
async def test_login_wrong_email(auth_service):
    """Test login fails with non-existent email."""
    # Arrange
    login_dto = LoginDTO(email="wrong@example.com", password="password123")

    # Act & Assert
    with pytest.raises(InvalidCredentialsError):
        await auth_service.login(login_dto)


@pytest.mark.asyncio
async def test_login_wrong_password(auth_service):
    """Test login fails with incorrect password."""
    # Arrange
    login_dto = LoginDTO(email="test@example.com", password="wrongpassword")

    # Act & Assert
    with pytest.raises(InvalidCredentialsError):
        await auth_service.login(login_dto)


@pytest.mark.asyncio
async def test_login_stores_refresh_token_metadata(auth_service, fake_token_repository):
    """Test that login stores refresh token metadata."""
    # Arrange
    login_dto = LoginDTO(email="test@example.com", password="password123")

    # Act
    result = await auth_service.login(login_dto)

    # Assert - verify refresh token was stored
    # Extract token_id from refresh token
    token_data = auth_service._token_service.verify_refresh_token(result.refresh_token)
    assert token_data is not None
    assert token_data.token_id is not None

    metadata = await fake_token_repository.get_token_metadata(token_data.token_id)
    assert metadata is not None
    assert metadata.user_id == 1
    assert metadata.token_type == "refresh"


# === GET CURRENT USER TESTS ===


@pytest.mark.asyncio
async def test_get_current_user_success(auth_service, sample_user):
    """Test getting current user from valid access token."""
    # Arrange
    access_token = auth_service._token_service.generate_access_token(
        user_id=sample_user.id, email=sample_user.email
    )

    # Act
    result = await auth_service.get_current_user(access_token)

    # Assert
    assert result.id == sample_user.id
    assert result.email == sample_user.email
    assert result.name == sample_user.name


@pytest.mark.asyncio
async def test_get_current_user_invalid_token(auth_service):
    """Test getting current user fails with invalid token."""
    # Arrange
    invalid_token = "invalid_token"

    # Act & Assert
    with pytest.raises(InvalidTokenError):
        await auth_service.get_current_user(invalid_token)


@pytest.mark.asyncio
async def test_get_current_user_expired_token(auth_service, sample_user):
    """Test getting current user fails with expired token."""
    # Arrange
    access_token = auth_service._token_service.generate_access_token(
        user_id=sample_user.id, email=sample_user.email
    )
    # Expire the token
    auth_service._token_service.expire_token(access_token)

    # Act & Assert
    with pytest.raises(InvalidTokenError):
        await auth_service.get_current_user(access_token)


@pytest.mark.asyncio
async def test_get_current_user_user_not_found(auth_service):
    """Test getting current user fails when user doesn't exist."""
    # Arrange
    # Generate token for non-existent user
    access_token = auth_service._token_service.generate_access_token(
        user_id=999, email="nonexistent@example.com"
    )

    # Act & Assert
    with pytest.raises(UserNotFoundError):
        await auth_service.get_current_user(access_token)


# === REFRESH TOKEN TESTS ===


@pytest.mark.asyncio
async def test_refresh_token_first_use_success(auth_service, sample_user):
    """Test first use of refresh token succeeds and issues new tokens."""
    # Arrange - login to get a refresh token
    login_dto = LoginDTO(email="test@example.com", password="password123")
    login_result = await auth_service.login(login_dto)

    # Act - use refresh token
    refresh_dto = RefreshTokenDTO(refresh_token=login_result.refresh_token)
    result = await auth_service.refresh_token(refresh_dto)

    # Assert
    assert result.access_token.startswith("access_")
    assert result.refresh_token.startswith("refresh_")
    assert result.refresh_token != login_result.refresh_token  # New token issued


@pytest.mark.asyncio
async def test_refresh_token_invalid_token(auth_service):
    """Test refresh fails with invalid token."""
    # Arrange
    refresh_dto = RefreshTokenDTO(refresh_token="invalid_token")

    # Act & Assert
    with pytest.raises(InvalidTokenError, match="Invalid or expired"):
        await auth_service.refresh_token(refresh_dto)


@pytest.mark.asyncio
async def test_refresh_token_expired_token(auth_service, sample_user):
    """Test refresh fails with expired token."""
    # Arrange
    refresh_token = auth_service._token_service.generate_refresh_token(
        user_id=sample_user.id, email=sample_user.email
    )
    # Store the token
    token_data = auth_service._token_service.verify_refresh_token(refresh_token)
    await auth_service._store_refresh_token(token_data)

    # Expire it
    auth_service._token_service.expire_token(refresh_token)

    # Act & Assert
    refresh_dto = RefreshTokenDTO(refresh_token=refresh_token)
    with pytest.raises(InvalidTokenError, match="Invalid or expired"):
        await auth_service.refresh_token(refresh_dto)


@pytest.mark.asyncio
async def test_refresh_token_not_in_repository(
    auth_service, sample_user, fake_token_repository
):
    """Test refresh fails when token not found in repository."""
    # Arrange - generate token but don't store it
    refresh_token = auth_service._token_service.generate_refresh_token(
        user_id=sample_user.id, email=sample_user.email
    )
    # Explicitly don't store it in repository

    # Act & Assert
    refresh_dto = RefreshTokenDTO(refresh_token=refresh_token)
    with pytest.raises(InvalidTokenError, match="Token not found or has been revoked"):
        await auth_service.refresh_token(refresh_dto)


@pytest.mark.asyncio
async def test_refresh_token_revoked_token(
    auth_service, sample_user, fake_token_repository
):
    """Test refresh fails with revoked token."""
    # Arrange
    login_dto = LoginDTO(email="test@example.com", password="password123")
    login_result = await auth_service.login(login_dto)

    # Revoke the token
    token_data = auth_service._token_service.verify_refresh_token(
        login_result.refresh_token
    )
    await fake_token_repository.revoke_token(token_data.token_id)

    # Act & Assert
    refresh_dto = RefreshTokenDTO(refresh_token=login_result.refresh_token)
    with pytest.raises(InvalidTokenError, match="Token has been revoked"):
        await auth_service.refresh_token(refresh_dto)


@pytest.mark.asyncio
async def test_refresh_token_reuse_within_overlap_previous_token_allowed(
    auth_service, sample_user, fake_token_repository
):
    """Test reusing the PREVIOUS token within overlap period is allowed."""
    # Arrange - login and refresh once
    login_dto = LoginDTO(email="test@example.com", password="password123")
    login_result = await auth_service.login(login_dto)

    # First refresh - this marks the original token as used
    refresh_dto = RefreshTokenDTO(refresh_token=login_result.refresh_token)
    _first_refresh = await auth_service.refresh_token(refresh_dto)

    # Act - reuse the ORIGINAL (previous) token within overlap period
    # This should succeed because it's the immediate previous token
    result = await auth_service.refresh_token(refresh_dto)

    # Assert - should succeed
    assert result.access_token.startswith("access_")
    assert result.refresh_token.startswith("refresh_")


@pytest.mark.asyncio
async def test_refresh_token_reuse_within_overlap_older_token_breach(
    auth_service, sample_user, fake_token_repository
):
    """Test reusing an OLDER token (not immediate previous) within overlap period triggers breach."""
    # Arrange - login and refresh twice to create a chain
    login_dto = LoginDTO(email="test@example.com", password="password123")
    login_result = await auth_service.login(login_dto)

    # First refresh
    refresh_dto_1 = RefreshTokenDTO(refresh_token=login_result.refresh_token)
    first_refresh = await auth_service.refresh_token(refresh_dto_1)

    # Second refresh - now the original token is 2 steps back
    refresh_dto_2 = RefreshTokenDTO(refresh_token=first_refresh.refresh_token)
    _second_refresh = await auth_service.refresh_token(refresh_dto_2)

    # Act - reuse the ORIGINAL token (2 steps back) within overlap period
    # This should trigger breach detection
    with pytest.raises(InvalidTokenError, match="Old token reuse detected"):
        await auth_service.refresh_token(refresh_dto_1)

    # Assert - family should be revoked
    original_token_data = auth_service._token_service.verify_refresh_token(
        login_result.refresh_token
    )
    assert await fake_token_repository.is_token_revoked(original_token_data.token_id)


@pytest.mark.asyncio
async def test_refresh_token_reuse_outside_overlap_period_breach(
    auth_service, sample_user, fake_token_repository
):
    """Test reusing ANY token outside overlap period triggers breach."""
    # Arrange - login and get refresh token
    login_dto = LoginDTO(email="test@example.com", password="password123")
    login_result = await auth_service.login(login_dto)

    # Get token data
    token_data = auth_service._token_service.verify_refresh_token(
        login_result.refresh_token
    )

    # Manually set the used_at time to be outside overlap period (10 seconds ago)
    # We need to directly update the metadata since mark_token_used only sets it once
    old_time = datetime.now(UTC) - timedelta(seconds=10)
    metadata = await fake_token_repository.get_token_metadata(token_data.token_id)
    updated_metadata = TokenMetadata(
        token_id=metadata.token_id,
        user_id=metadata.user_id,
        token_type=metadata.token_type,
        issued_at=metadata.issued_at,
        expires_at=metadata.expires_at,
        is_revoked=metadata.is_revoked,
        family_id=metadata.family_id,
        used_at=old_time,  # Set to old time
        rotation_sequence=metadata.rotation_sequence,
        parent_token_id=metadata.parent_token_id,
    )
    await fake_token_repository.store_token(updated_metadata)

    # Act - try to reuse outside overlap period
    refresh_dto = RefreshTokenDTO(refresh_token=login_result.refresh_token)
    with pytest.raises(InvalidTokenError, match="Token reuse detected"):
        await auth_service.refresh_token(refresh_dto)

    # Assert - family should be revoked
    assert await fake_token_repository.is_token_revoked(token_data.token_id)


@pytest.mark.asyncio
async def test_refresh_token_user_not_found(auth_service, fake_token_repository):
    """Test refresh fails when user no longer exists."""
    # Arrange - generate token for user ID that doesn't exist
    refresh_token = auth_service._token_service.generate_refresh_token(
        user_id=999, email="nonexistent@example.com"
    )
    token_data = auth_service._token_service.verify_refresh_token(refresh_token)
    await auth_service._store_refresh_token(token_data)

    # Act & Assert
    refresh_dto = RefreshTokenDTO(refresh_token=refresh_token)
    with pytest.raises(UserNotFoundError):
        await auth_service.refresh_token(refresh_dto)


@pytest.mark.asyncio
async def test_refresh_token_rotation_increments_sequence(
    auth_service, sample_user, fake_token_repository
):
    """Test that token rotation increments the sequence number."""
    # Arrange
    login_dto = LoginDTO(email="test@example.com", password="password123")
    login_result = await auth_service.login(login_dto)

    # Get original token data
    original_token_data = auth_service._token_service.verify_refresh_token(
        login_result.refresh_token
    )
    assert original_token_data.rotation_sequence == 0

    # Act - refresh token
    refresh_dto = RefreshTokenDTO(refresh_token=login_result.refresh_token)
    result = await auth_service.refresh_token(refresh_dto)

    # Get new token data
    new_token_data = auth_service._token_service.verify_refresh_token(
        result.refresh_token
    )

    # Assert - sequence should be incremented
    assert new_token_data.rotation_sequence == 1
    assert new_token_data.parent_token_id == original_token_data.token_id
    assert new_token_data.family_id == original_token_data.family_id


@pytest.mark.asyncio
async def test_refresh_token_stores_new_token_metadata(
    auth_service, sample_user, fake_token_repository
):
    """Test that refreshing stores metadata for the new token."""
    # Arrange
    login_dto = LoginDTO(email="test@example.com", password="password123")
    login_result = await auth_service.login(login_dto)

    # Act
    refresh_dto = RefreshTokenDTO(refresh_token=login_result.refresh_token)
    result = await auth_service.refresh_token(refresh_dto)

    # Assert - new token should be in repository
    new_token_data = auth_service._token_service.verify_refresh_token(
        result.refresh_token
    )
    metadata = await fake_token_repository.get_token_metadata(new_token_data.token_id)

    assert metadata is not None
    assert metadata.user_id == sample_user.id
    assert metadata.token_type == "refresh"
    assert metadata.rotation_sequence == 1
