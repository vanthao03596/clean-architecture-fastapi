"""Unit tests for User DTOs validation.

Tests Pydantic validation for user DTOs to ensure validation happens
at the API boundary before reaching the domain layer.
"""

import pytest
from pydantic import ValidationError

from app.application.dtos.user_dto import CreateUserDTO, UpdateUserDTO

pytestmark = pytest.mark.unit


# === CREATE USER DTO TESTS ===


def test_create_user_dto_valid():
    """Test creating DTO with valid data."""
    dto = CreateUserDTO(
        email="test@example.com", name="John Doe", password="securepass123"
    )

    assert dto.email == "test@example.com"
    assert dto.name == "John Doe"
    assert dto.password == "securepass123"


def test_create_user_dto_strips_whitespace_from_name():
    """Test that name whitespace is stripped."""
    dto = CreateUserDTO(
        email="test@example.com", name="  John Doe  ", password="securepass123"
    )

    assert dto.name == "John Doe"


def test_create_user_dto_empty_name_raises_error():
    """Test that empty name raises validation error."""
    with pytest.raises(ValidationError) as exc_info:
        CreateUserDTO(email="test@example.com", name="", password="securepass123")

    errors = exc_info.value.errors()
    assert len(errors) == 1
    assert errors[0]["loc"] == ("name",)
    # Pydantic's min_length validator error message
    assert "at least 1" in errors[0]["msg"].lower()


def test_create_user_dto_whitespace_only_name_raises_error():
    """Test that whitespace-only name raises validation error."""
    with pytest.raises(ValidationError) as exc_info:
        CreateUserDTO(email="test@example.com", name="   ", password="securepass123")

    errors = exc_info.value.errors()
    assert len(errors) == 1
    assert errors[0]["loc"] == ("name",)
    # Pydantic's min_length validator error message (after stripping whitespace)
    assert "at least 1" in errors[0]["msg"].lower()


def test_create_user_dto_short_password_raises_error():
    """Test that password shorter than 8 characters raises error."""
    with pytest.raises(ValidationError) as exc_info:
        CreateUserDTO(email="test@example.com", name="John Doe", password="short")

    errors = exc_info.value.errors()
    assert len(errors) == 1
    assert errors[0]["loc"] == ("password",)
    assert "8 characters" in errors[0]["msg"]


def test_create_user_dto_7_character_password_raises_error():
    """Test edge case: 7 characters is too short."""
    with pytest.raises(ValidationError) as exc_info:
        CreateUserDTO(email="test@example.com", name="John Doe", password="1234567")

    errors = exc_info.value.errors()
    assert len(errors) == 1
    assert errors[0]["loc"] == ("password",)


def test_create_user_dto_8_character_password_valid():
    """Test edge case: exactly 8 characters is valid."""
    dto = CreateUserDTO(email="test@example.com", name="John Doe", password="12345678")

    assert dto.password == "12345678"


def test_create_user_dto_invalid_email_raises_error():
    """Test that invalid email format raises error."""
    with pytest.raises(ValidationError) as exc_info:
        CreateUserDTO(email="invalid_email", name="John Doe", password="securepass123")

    errors = exc_info.value.errors()
    assert len(errors) == 1
    assert errors[0]["loc"] == ("email",)


def test_create_user_dto_multiple_validation_errors():
    """Test that multiple validation errors are reported together."""
    with pytest.raises(ValidationError) as exc_info:
        CreateUserDTO(email="invalid_email", name="", password="short")

    errors = exc_info.value.errors()
    # Should have 3 errors: email, name, password
    assert len(errors) == 3
    error_fields = {error["loc"][0] for error in errors}
    assert error_fields == {"email", "name", "password"}


# === UPDATE USER DTO TESTS ===


def test_update_user_dto_valid_name():
    """Test updating with valid name."""
    dto = UpdateUserDTO(name="Jane Doe")

    assert dto.name == "Jane Doe"
    assert dto.email is None


def test_update_user_dto_valid_email():
    """Test updating with valid email."""
    dto = UpdateUserDTO(email="new@example.com")

    assert dto.email == "new@example.com"
    assert dto.name is None


def test_update_user_dto_both_fields():
    """Test updating both fields."""
    dto = UpdateUserDTO(email="new@example.com", name="Jane Doe")

    assert dto.email == "new@example.com"
    assert dto.name == "Jane Doe"


def test_update_user_dto_no_fields():
    """Test creating DTO with no updates (both None)."""
    dto = UpdateUserDTO()

    assert dto.email is None
    assert dto.name is None


def test_update_user_dto_strips_whitespace_from_name():
    """Test that name whitespace is stripped."""
    dto = UpdateUserDTO(name="  Jane Doe  ")

    assert dto.name == "Jane Doe"


def test_update_user_dto_empty_name_raises_error():
    """Test that empty name raises validation error."""
    with pytest.raises(ValidationError) as exc_info:
        UpdateUserDTO(name="")

    errors = exc_info.value.errors()
    assert len(errors) == 1
    assert errors[0]["loc"] == ("name",)
    # Pydantic's min_length validator error message
    assert "at least 1" in errors[0]["msg"].lower()


def test_update_user_dto_whitespace_only_name_raises_error():
    """Test that whitespace-only name raises validation error."""
    with pytest.raises(ValidationError) as exc_info:
        UpdateUserDTO(name="   ")

    errors = exc_info.value.errors()
    assert len(errors) == 1
    assert errors[0]["loc"] == ("name",)
    # Pydantic's min_length validator error message (after stripping whitespace)
    assert "at least 1" in errors[0]["msg"].lower()


def test_update_user_dto_none_name_is_valid():
    """Test that None name is valid (field not being updated)."""
    dto = UpdateUserDTO(name=None)

    assert dto.name is None


def test_update_user_dto_invalid_email_raises_error():
    """Test that invalid email format raises error."""
    with pytest.raises(ValidationError) as exc_info:
        UpdateUserDTO(email="invalid_email")

    errors = exc_info.value.errors()
    assert len(errors) == 1
    assert errors[0]["loc"] == ("email",)


def test_update_user_dto_multiple_validation_errors():
    """Test that multiple validation errors are reported together."""
    with pytest.raises(ValidationError) as exc_info:
        UpdateUserDTO(email="invalid_email", name="")

    errors = exc_info.value.errors()
    assert len(errors) == 2
    error_fields = {error["loc"][0] for error in errors}
    assert error_fields == {"email", "name"}
