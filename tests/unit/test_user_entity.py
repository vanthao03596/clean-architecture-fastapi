"""Unit tests for User domain entity.

Tests business rules and validations for the User entity:
1. Entity creation with validation
2. Name change with validation
3. Email change with validation
"""

import pytest
from datetime import datetime, timezone

from app.domain.entities.user import User
from app.domain.exceptions import InvalidEntityStateException, BusinessRuleViolationException

pytestmark = pytest.mark.unit


# === USER CREATION TESTS ===


def test_create_valid_user():
    """Test creating a user with valid data."""
    # Arrange & Act
    user = User(
        email="test@example.com",
        name="Test User",
        password_hash="hashed_password",
        id=1,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    # Assert
    assert user.email == "test@example.com"
    assert user.name == "Test User"
    assert user.password_hash == "hashed_password"
    assert user.id == 1


def test_create_user_without_optional_fields():
    """Test creating a user without optional fields (id, timestamps)."""
    # Arrange & Act
    user = User(
        email="test@example.com",
        name="Test User",
        password_hash="hashed_password",
    )

    # Assert
    assert user.email == "test@example.com"
    assert user.name == "Test User"
    assert user.password_hash == "hashed_password"
    assert user.id is None
    assert user.created_at is None
    assert user.updated_at is None


def test_create_user_invalid_email_no_at_symbol():
    """Test creating a user with email missing @ symbol."""
    # Arrange, Act & Assert
    with pytest.raises(
        InvalidEntityStateException,
        match="Invalid email address.*Email must contain '@' symbol"
    ):
        User(
            email="invalid_email",
            name="Test User",
            password_hash="hashed_password",
        )


def test_create_user_empty_email():
    """Test creating a user with empty email."""
    # Arrange, Act & Assert
    with pytest.raises(
        InvalidEntityStateException,
        match="Invalid email address"
    ):
        User(
            email="",
            name="Test User",
            password_hash="hashed_password",
        )


def test_create_user_empty_name():
    """Test creating a user with empty name."""
    # Arrange, Act & Assert
    with pytest.raises(
        InvalidEntityStateException,
        match="Name cannot be empty"
    ):
        User(
            email="test@example.com",
            name="",
            password_hash="hashed_password",
        )


def test_create_user_whitespace_only_name():
    """Test creating a user with whitespace-only name."""
    # Arrange, Act & Assert
    with pytest.raises(
        InvalidEntityStateException,
        match="Name cannot be empty"
    ):
        User(
            email="test@example.com",
            name="   ",
            password_hash="hashed_password",
        )


def test_create_user_empty_password_hash():
    """Test creating a user with empty password hash."""
    # Arrange, Act & Assert
    with pytest.raises(
        InvalidEntityStateException,
        match="Password hash is required"
    ):
        User(
            email="test@example.com",
            name="Test User",
            password_hash="",
        )


# === CHANGE NAME TESTS ===


def test_change_name_success():
    """Test changing user name with valid input."""
    # Arrange
    user = User(
        email="test@example.com",
        name="Old Name",
        password_hash="hashed_password",
    )

    # Act
    user.change_name("New Name")

    # Assert
    assert user.name == "New Name"
    # Note: updated_at is managed by repository (infrastructure layer)


def test_change_name_empty_string():
    """Test changing name to empty string fails."""
    # Arrange
    user = User(
        email="test@example.com",
        name="Old Name",
        password_hash="hashed_password",
    )

    # Act & Assert
    with pytest.raises(
        BusinessRuleViolationException,
        match="Cannot change name to empty value"
    ):
        user.change_name("")

    # Name should remain unchanged
    assert user.name == "Old Name"


def test_change_name_whitespace_only():
    """Test changing name to whitespace-only string fails."""
    # Arrange
    user = User(
        email="test@example.com",
        name="Old Name",
        password_hash="hashed_password",
    )

    # Act & Assert
    with pytest.raises(
        BusinessRuleViolationException,
        match="Cannot change name to empty value"
    ):
        user.change_name("   ")

    # Name should remain unchanged
    assert user.name == "Old Name"


# === CHANGE EMAIL TESTS ===


def test_change_email_success():
    """Test changing user email with valid input."""
    # Arrange
    user = User(
        email="old@example.com",
        name="Test User",
        password_hash="hashed_password",
    )

    # Act
    user.change_email("new@example.com")

    # Assert
    assert user.email == "new@example.com"
    # Note: updated_at is managed by repository (infrastructure layer)


def test_change_email_invalid_no_at_symbol():
    """Test changing email to invalid format fails."""
    # Arrange
    user = User(
        email="old@example.com",
        name="Test User",
        password_hash="hashed_password",
    )

    # Act & Assert
    with pytest.raises(
        BusinessRuleViolationException,
        match="Cannot change email to invalid address.*Email must contain '@' symbol"
    ):
        user.change_email("invalid_email")

    # Email should remain unchanged
    assert user.email == "old@example.com"


def test_change_email_empty_string():
    """Test changing email to empty string fails."""
    # Arrange
    user = User(
        email="old@example.com",
        name="Test User",
        password_hash="hashed_password",
    )

    # Act & Assert
    with pytest.raises(
        BusinessRuleViolationException,
        match="Cannot change email to invalid address"
    ):
        user.change_email("")

    # Email should remain unchanged
    assert user.email == "old@example.com"
