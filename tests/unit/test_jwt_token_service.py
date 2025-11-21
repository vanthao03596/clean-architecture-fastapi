"""Unit tests for JWTTokenService.

Tests JWT token generation and validation:
1. Token generation (access and refresh)
2. Token verification
3. Token expiration handling
4. Token rotation support
"""

import time
from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.infrastructure.security.jwt_token_service import JWTTokenService
from tests.fakes.token_repository_fake import FakeTokenRepository

pytestmark = pytest.mark.unit


@pytest.fixture
def fake_token_repository():
    """Provide a fake token repository."""
    return FakeTokenRepository()


@pytest.fixture
def jwt_service(fake_token_repository):
    """Provide JWTTokenService with a valid secret key."""
    return JWTTokenService(
        secret_key="a" * 32,  # 32 characters minimum
        token_repository=fake_token_repository,
        access_token_expire_minutes=30,
        refresh_token_expire_days=7,
    )


# === INITIALIZATION TESTS ===


def test_init_with_valid_secret_key(fake_token_repository):
    """Test JWTTokenService initializes with valid secret key."""
    # Arrange & Act
    service = JWTTokenService(
        secret_key="a" * 32,
        token_repository=fake_token_repository,
    )

    # Assert
    assert service is not None


def test_init_with_short_secret_key_raises_error(fake_token_repository):
    """Test JWTTokenService raises error with short secret key."""
    # Arrange, Act & Assert
    with pytest.raises(ValueError, match="Secret key must be at least 32 characters"):
        JWTTokenService(
            secret_key="short_key",
            token_repository=fake_token_repository,
        )


# === ACCESS TOKEN GENERATION TESTS ===


def test_generate_access_token_success(jwt_service):
    """Test generating a valid access token."""
    # Arrange
    user_id = 123
    email = "test@example.com"

    # Act
    token = jwt_service.generate_access_token(user_id, email)

    # Assert
    assert token is not None
    assert isinstance(token, str)
    assert len(token) > 0


def test_generate_access_token_contains_correct_claims(jwt_service):
    """Test access token contains all expected claims."""
    # Arrange
    user_id = 123
    email = "test@example.com"

    # Act
    token = jwt_service.generate_access_token(user_id, email)

    # Decode without verification to inspect payload
    payload = jwt.decode(token, options={"verify_signature": False})

    # Assert
    assert payload["sub"] == "123"
    assert payload["email"] == email
    assert payload["type"] == "access"
    assert "exp" in payload
    assert "iat" in payload
    assert "jti" in payload


def test_generate_access_token_expiration(jwt_service):
    """Test access token has correct expiration time."""
    # Arrange
    user_id = 123
    email = "test@example.com"

    # Act
    before_generation = datetime.now(UTC)
    token = jwt_service.generate_access_token(user_id, email)
    _after_generation = datetime.now(UTC)

    payload = jwt.decode(token, options={"verify_signature": False})
    exp_timestamp = payload["exp"]
    exp_datetime = datetime.fromtimestamp(exp_timestamp, tz=UTC)

    # Assert - token expires in approximately 30 minutes
    expected_exp = before_generation + timedelta(minutes=30)
    # Allow 1 second tolerance
    assert abs((exp_datetime - expected_exp).total_seconds()) < 1


# === REFRESH TOKEN GENERATION TESTS ===


def test_generate_refresh_token_success(jwt_service):
    """Test generating a valid refresh token."""
    # Arrange
    user_id = 123
    email = "test@example.com"

    # Act
    token = jwt_service.generate_refresh_token(user_id, email)

    # Assert
    assert token is not None
    assert isinstance(token, str)
    assert len(token) > 0


def test_generate_refresh_token_contains_correct_claims(jwt_service):
    """Test refresh token contains all expected claims."""
    # Arrange
    user_id = 123
    email = "test@example.com"

    # Act
    token = jwt_service.generate_refresh_token(user_id, email)

    # Decode without verification
    payload = jwt.decode(token, options={"verify_signature": False})

    # Assert
    assert payload["sub"] == "123"
    assert payload["email"] == email
    assert payload["type"] == "refresh"
    assert "exp" in payload
    assert "iat" in payload
    assert "jti" in payload
    assert "fid" in payload  # Family ID
    assert "seq" in payload  # Rotation sequence


def test_generate_refresh_token_auto_generates_family_id(jwt_service):
    """Test refresh token auto-generates family_id when not provided."""
    # Arrange
    user_id = 123
    email = "test@example.com"

    # Act
    token = jwt_service.generate_refresh_token(user_id, email)

    # Decode without verification
    payload = jwt.decode(token, options={"verify_signature": False})

    # Assert - family_id should be present and non-null
    assert "fid" in payload
    assert payload["fid"] is not None
    assert len(payload["fid"]) > 0


def test_generate_refresh_token_with_rotation_data(jwt_service):
    """Test refresh token includes rotation data."""
    # Arrange
    user_id = 123
    email = "test@example.com"
    family_id = "family-123"
    parent_token_id = "parent-456"
    rotation_sequence = 2

    # Act
    token = jwt_service.generate_refresh_token(
        user_id,
        email,
        family_id=family_id,
        parent_token_id=parent_token_id,
        rotation_sequence=rotation_sequence,
    )

    # Decode without verification
    payload = jwt.decode(token, options={"verify_signature": False})

    # Assert
    assert payload["fid"] == family_id
    assert payload["pid"] == parent_token_id
    assert payload["seq"] == rotation_sequence


def test_generate_refresh_token_expiration(jwt_service):
    """Test refresh token has correct expiration time."""
    # Arrange
    user_id = 123
    email = "test@example.com"

    # Act
    before_generation = datetime.now(UTC)
    token = jwt_service.generate_refresh_token(user_id, email)
    _after_generation = datetime.now(UTC)

    payload = jwt.decode(token, options={"verify_signature": False})
    exp_timestamp = payload["exp"]
    exp_datetime = datetime.fromtimestamp(exp_timestamp, tz=UTC)

    # Assert - token expires in approximately 7 days
    expected_exp = before_generation + timedelta(days=7)
    # Allow 1 second tolerance
    assert abs((exp_datetime - expected_exp).total_seconds()) < 1


# === ACCESS TOKEN VERIFICATION TESTS ===


def test_verify_access_token_success(jwt_service):
    """Test verifying a valid access token."""
    # Arrange
    user_id = 123
    email = "test@example.com"
    token = jwt_service.generate_access_token(user_id, email)

    # Act
    token_data = jwt_service.verify_token(token)

    # Assert
    assert token_data is not None
    assert token_data.user_id == user_id
    assert token_data.email == email
    assert token_data.token_id is not None


def test_verify_access_token_invalid_token_returns_none(jwt_service):
    """Test verifying an invalid token returns None."""
    # Arrange
    invalid_token = "invalid.token.string"

    # Act
    token_data = jwt_service.verify_token(invalid_token)

    # Assert
    assert token_data is None


def test_verify_access_token_tampered_token_returns_none(jwt_service):
    """Test verifying a tampered token returns None."""
    # Arrange
    user_id = 123
    email = "test@example.com"
    token = jwt_service.generate_access_token(user_id, email)
    # Tamper with the token
    tampered_token = token[:-10] + "tampered00"

    # Act
    token_data = jwt_service.verify_token(tampered_token)

    # Assert
    assert token_data is None


def test_verify_access_token_wrong_type_returns_none(jwt_service):
    """Test verifying a refresh token as access token returns None."""
    # Arrange
    user_id = 123
    email = "test@example.com"
    # Generate refresh token
    refresh_token = jwt_service.generate_refresh_token(user_id, email)

    # Act - try to verify refresh token as access token
    token_data = jwt_service.verify_token(refresh_token)

    # Assert
    assert token_data is None


def test_verify_access_token_expired_returns_none(jwt_service):
    """Test verifying an expired token returns None."""
    # Arrange - create service with very short expiration
    short_lived_service = JWTTokenService(
        secret_key="a" * 32,
        token_repository=FakeTokenRepository(),
        access_token_expire_minutes=0,  # Expire immediately
    )
    token = short_lived_service.generate_access_token(123, "test@example.com")
    time.sleep(1)  # Wait for token to expire

    # Act
    token_data = short_lived_service.verify_token(token)

    # Assert
    assert token_data is None


# === REFRESH TOKEN VERIFICATION TESTS ===


def test_verify_refresh_token_success(jwt_service):
    """Test verifying a valid refresh token."""
    # Arrange
    user_id = 123
    email = "test@example.com"
    token = jwt_service.generate_refresh_token(user_id, email)

    # Act
    token_data = jwt_service.verify_refresh_token(token)

    # Assert
    assert token_data is not None
    assert token_data.user_id == user_id
    assert token_data.email == email
    assert token_data.token_id is not None
    assert token_data.family_id is not None


def test_verify_refresh_token_includes_rotation_data(jwt_service):
    """Test verified refresh token includes rotation data."""
    # Arrange
    user_id = 123
    email = "test@example.com"
    family_id = "family-123"
    parent_token_id = "parent-456"
    rotation_sequence = 2

    token = jwt_service.generate_refresh_token(
        user_id,
        email,
        family_id=family_id,
        parent_token_id=parent_token_id,
        rotation_sequence=rotation_sequence,
    )

    # Act
    token_data = jwt_service.verify_refresh_token(token)

    # Assert
    assert token_data.family_id == family_id
    assert token_data.parent_token_id == parent_token_id
    assert token_data.rotation_sequence == rotation_sequence


def test_verify_refresh_token_invalid_token_returns_none(jwt_service):
    """Test verifying an invalid refresh token returns None."""
    # Arrange
    invalid_token = "invalid.token.string"

    # Act
    token_data = jwt_service.verify_refresh_token(invalid_token)

    # Assert
    assert token_data is None


def test_verify_refresh_token_wrong_type_returns_none(jwt_service):
    """Test verifying an access token as refresh token returns None."""
    # Arrange
    user_id = 123
    email = "test@example.com"
    # Generate access token
    access_token = jwt_service.generate_access_token(user_id, email)

    # Act - try to verify access token as refresh token
    token_data = jwt_service.verify_refresh_token(access_token)

    # Assert
    assert token_data is None


def test_verify_refresh_token_expired_returns_none(jwt_service):
    """Test verifying an expired refresh token returns None."""
    # Arrange - create service with very short expiration
    short_lived_service = JWTTokenService(
        secret_key="a" * 32,
        token_repository=FakeTokenRepository(),
        refresh_token_expire_days=0,  # Expire immediately
    )
    token = short_lived_service.generate_refresh_token(123, "test@example.com")
    time.sleep(1)  # Wait for token to expire

    # Act
    token_data = short_lived_service.verify_refresh_token(token)

    # Assert
    assert token_data is None


# === TOKEN PROPERTIES TESTS ===


def test_token_data_is_expired_property(jwt_service):
    """Test TokenData.is_expired property works correctly."""
    # Arrange - create expired token
    short_lived_service = JWTTokenService(
        secret_key="a" * 32,
        token_repository=FakeTokenRepository(),
        access_token_expire_minutes=0,
    )
    token = short_lived_service.generate_access_token(123, "test@example.com")

    # Decode to get TokenData (bypassing verification and expiration check)
    payload = jwt.decode(
        token,
        "a" * 32,
        algorithms=["HS256"],
        options={"verify_exp": False},  # Don't verify expiration during decode
    )
    from app.domain.services.token_service import TokenData

    token_data = TokenData(
        user_id=int(payload["sub"]),
        email=payload["email"],
        issued_at=datetime.fromtimestamp(payload["iat"], tz=UTC),
        expires_at=datetime.fromtimestamp(payload["exp"], tz=UTC),
        token_id=payload["jti"],
    )

    # Wait for expiration
    time.sleep(1)

    # Act & Assert
    assert token_data.is_expired is True
