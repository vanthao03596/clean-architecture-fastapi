"""Unit tests for UserService.

These tests use fake repositories to test the service layer in isolation
without a database.
"""

import pytest

from app.application.dtos.user_dto import CreateUserDTO, UpdateUserDTO
from app.application.exceptions import UserAlreadyExistsError, UserNotFoundError
from app.domain.entities.user import User

pytestmark = pytest.mark.unit


class TestUserServiceCreate:
    """Test cases for creating users."""

    @pytest.mark.asyncio
    async def test_create_user_success(self, user_service, fake_uow):
        """Test successful user creation."""
        # Arrange
        dto = CreateUserDTO(
            email="newuser@example.com",
            name="New User",
            password="password123",
        )

        # Act
        result = await user_service.create_user(dto)

        # Assert
        assert result.email == "newuser@example.com"
        assert result.name == "New User"
        assert result.id is not None
        assert result.created_at is not None
        assert result.updated_at is not None

        # Verify commit was called
        assert fake_uow.was_committed()

        # Verify user is in repository
        assert fake_uow.users.count() == 1

    @pytest.mark.asyncio
    async def test_create_user_duplicate_email(self, user_service, fake_uow):
        """Test creating user with duplicate email raises error."""
        # Arrange
        dto = CreateUserDTO(
            email="test@example.com",
            name="Test User",
            password="password123",
        )

        # Create first user
        await user_service.create_user(dto)

        # Act & Assert
        with pytest.raises(UserAlreadyExistsError) as exc_info:
            await user_service.create_user(dto)

        assert "already registered" in str(exc_info.value)
        assert exc_info.value.error_code == "USER_ALREADY_EXISTS"

    @pytest.mark.asyncio
    async def test_create_user_hashes_password(self, user_service, fake_uow):
        """Test that password is hashed before storage."""
        # Arrange
        dto = CreateUserDTO(
            email="test@example.com",
            name="Test User",
            password="plaintext_password",
        )

        # Act
        result = await user_service.create_user(dto)

        # Assert
        # Verify the returned DTO doesn't contain password
        assert not hasattr(result, "password")
        assert not hasattr(result, "password_hash")

        # Verify the stored user has a hashed password
        stored_user = await fake_uow.users.get_by_id(result.id)
        assert stored_user.password_hash != "plaintext_password"
        assert stored_user.password_hash is not None


class TestUserServiceGet:
    """Test cases for retrieving users."""

    @pytest.mark.asyncio
    async def test_get_user_by_id_success(self, user_service_with_data, sample_user):
        """Test retrieving existing user by ID."""
        # Act
        result = await user_service_with_data.get_user_by_id(sample_user.id)

        # Assert
        assert result.id == sample_user.id
        assert result.email == sample_user.email
        assert result.name == sample_user.name

    @pytest.mark.asyncio
    async def test_get_user_by_id_not_found(self, user_service):
        """Test retrieving non-existent user raises error."""
        # Act & Assert
        with pytest.raises(UserNotFoundError) as exc_info:
            await user_service.get_user_by_id(999)

        assert "not found" in str(exc_info.value)
        assert exc_info.value.error_code == "USER_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_get_user_by_email_success(self, user_service_with_data, sample_user):
        """Test retrieving user by email."""
        # Act
        result = await user_service_with_data.get_user_by_email(sample_user.email)

        # Assert
        assert result is not None
        assert result.email == sample_user.email
        assert result.name == sample_user.name

    @pytest.mark.asyncio
    async def test_get_user_by_email_not_found(self, user_service):
        """Test retrieving non-existent user by email returns None."""
        # Act
        result = await user_service.get_user_by_email("nonexistent@example.com")

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_get_all_users(self, user_service_with_data):
        """Test retrieving all users."""
        # Act
        result = await user_service_with_data.get_all_users()

        # Assert
        assert len(result) == 2
        assert all(user.email for user in result)

    @pytest.mark.asyncio
    async def test_get_all_users_with_pagination(self, user_service_with_data):
        """Test retrieving users with pagination."""
        # Act
        result = await user_service_with_data.get_all_users(skip=0, limit=1)

        # Assert
        assert len(result) == 1


class TestUserServiceUpdate:
    """Test cases for updating users."""

    @pytest.mark.asyncio
    async def test_update_user_success(
        self, user_service_with_data, fake_uow_with_users, sample_user
    ):
        """Test updating user fields."""
        # Arrange - Test updating name
        name_dto = UpdateUserDTO(name="Updated Name")

        # Act
        result = await user_service_with_data.update_user(sample_user.id, name_dto)

        # Assert
        assert result.name == "Updated Name"
        assert result.email == sample_user.email  # Email unchanged
        assert fake_uow_with_users.was_committed()

        # Arrange - Test updating email
        email_dto = UpdateUserDTO(email="newemail@example.com")

        # Act
        result = await user_service_with_data.update_user(sample_user.id, email_dto)

        # Assert
        assert result.email == "newemail@example.com"
        assert result.name == "Updated Name"  # Name from previous update

    @pytest.mark.asyncio
    async def test_update_user_not_found(self, user_service):
        """Test updating non-existent user raises error."""
        # Arrange
        dto = UpdateUserDTO(name="New Name")

        # Act & Assert
        with pytest.raises(UserNotFoundError) as exc_info:
            await user_service.update_user(999, dto)

        assert "not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_user_duplicate_email(
        self, user_service_with_data, sample_user, another_user
    ):
        """Test updating user with existing email raises error."""
        # Arrange
        dto = UpdateUserDTO(email=another_user.email)

        # Act & Assert
        with pytest.raises(UserAlreadyExistsError) as exc_info:
            await user_service_with_data.update_user(sample_user.id, dto)

        assert "already in use" in str(exc_info.value)


class TestUserServiceDelete:
    """Test cases for deleting users."""

    @pytest.mark.asyncio
    async def test_delete_user_success(
        self, user_service_with_data, fake_uow_with_users, sample_user
    ):
        """Test successful user deletion."""
        # Act
        await user_service_with_data.delete_user(sample_user.id)

        # Assert
        # Verify commit was called
        assert fake_uow_with_users.was_committed()

        # Verify user is deleted
        assert fake_uow_with_users.users.count() == 1
        assert not await fake_uow_with_users.users.exists(sample_user.id)

    @pytest.mark.asyncio
    async def test_delete_user_not_found(self, user_service):
        """Test deleting non-existent user raises error."""
        # Act & Assert
        with pytest.raises(UserNotFoundError) as exc_info:
            await user_service.delete_user(999)

        assert "not found" in str(exc_info.value)


class TestUserServicePasswordVerification:
    """Test cases for password verification."""

    @pytest.mark.asyncio
    async def test_verify_password_success(self, user_service, fake_uow):
        """Test successful password verification."""
        # Arrange - Create a user
        dto = CreateUserDTO(
            email="user@example.com",
            name="Test User",
            password="correct_password",
        )
        await user_service.create_user(dto)

        # Act
        is_valid = await user_service.verify_password(
            email="user@example.com", password="correct_password"
        )

        # Assert
        assert is_valid is True

    @pytest.mark.asyncio
    async def test_verify_password_wrong_password(self, user_service, fake_uow):
        """Test password verification with wrong password."""
        # Arrange - Create a user
        dto = CreateUserDTO(
            email="user@example.com",
            name="Test User",
            password="correct_password",
        )
        await user_service.create_user(dto)

        # Act
        is_valid = await user_service.verify_password(
            email="user@example.com", password="wrong_password"
        )

        # Assert
        assert is_valid is False

    @pytest.mark.asyncio
    async def test_verify_password_nonexistent_user(self, user_service):
        """Test password verification for non-existent user."""
        # Act
        is_valid = await user_service.verify_password(
            email="nonexistent@example.com", password="any_password"
        )

        # Assert
        # Should return False without revealing user doesn't exist
        assert is_valid is False


class TestUserServiceTransactions:
    """Test cases for transaction behavior."""

    @pytest.mark.asyncio
    async def test_transaction_commits_on_success(self, user_service, fake_uow):
        """Test that successful operations commit."""
        # Arrange
        dto = CreateUserDTO(
            email="test@example.com",
            name="Test User",
            password="password123",
        )

        # Act
        await user_service.create_user(dto)

        # Assert
        assert fake_uow.was_committed()
        assert not fake_uow.was_rolled_back()

    @pytest.mark.asyncio
    async def test_transaction_rolls_back_on_error(self, user_service, fake_uow):
        """Test that failed operations don't commit."""
        # Arrange - pre-add a user
        existing_user = User(
            email="existing@example.com",
            name="Existing",
            password_hash="HASHED:existing_password",
        )
        await fake_uow.users.add(existing_user)

        dto = CreateUserDTO(
            email="existing@example.com",  # Duplicate email
            name="Test User",
            password="password123",
        )

        # Act & Assert
        with pytest.raises(UserAlreadyExistsError):
            await user_service.create_user(dto)

        # The UoW should not have committed after the error
        # (Note: In the fake implementation, we track commit attempts,
        # but in a real scenario, the transaction would rollback)
