"""Unit tests for password hashers.

These tests verify both the fake and real password hasher implementations.
"""

import pytest

from app.infrastructure.security.argon2_password_hasher import Argon2PasswordHasher
from tests.fakes.password_hasher_fake import FakePasswordHasher

pytestmark = pytest.mark.unit


class TestFakePasswordHasher:
    """Test the fake password hasher implementation."""

    def test_hash_adds_prefix(self):
        """Test that hashing adds the HASHED: prefix."""
        # Arrange
        hasher = FakePasswordHasher()

        # Act
        result = hasher.hash("mypassword")

        # Assert
        assert result == "HASHED:mypassword"
        assert result.startswith(FakePasswordHasher.HASH_PREFIX)

    def test_verify_correct_password(self):
        """Test verifying correct password."""
        # Arrange
        hasher = FakePasswordHasher()
        hashed = hasher.hash("correct_password")

        # Act
        result = hasher.verify("correct_password", hashed)

        # Assert
        assert result is True

    def test_verify_wrong_password(self):
        """Test verifying wrong password."""
        # Arrange
        hasher = FakePasswordHasher()
        hashed = hasher.hash("correct_password")

        # Act
        result = hasher.verify("wrong_password", hashed)

        # Assert
        assert result is False

    def test_verify_invalid_hash_format(self):
        """Test verifying with invalid hash format."""
        # Arrange
        hasher = FakePasswordHasher()

        # Act
        result = hasher.verify("password", "invalid_hash_without_prefix")

        # Assert
        assert result is False


class TestArgon2PasswordHasher:
    """Test the real Argon2 password hasher implementation."""

    def test_hash_creates_valid_argon2_hash(self):
        """Test that hashing creates a valid Argon2 hash."""
        # Arrange
        hasher = Argon2PasswordHasher()

        # Act
        result = hasher.hash("mypassword")

        # Assert
        # Argon2id hashes start with $argon2id$
        assert result.startswith("$argon2id$")
        # Hash should contain version and parameters
        assert "v=19" in result  # Argon2 version 1.3
        assert "m=" in result  # Memory cost parameter
        assert "t=" in result  # Time cost parameter
        assert "p=" in result  # Parallelism parameter

    def test_hash_generates_unique_salts(self):
        """Test that hashing the same password twice produces different hashes."""
        # Arrange
        hasher = Argon2PasswordHasher()
        password = "same_password"

        # Act
        hash1 = hasher.hash(password)
        hash2 = hasher.hash(password)

        # Assert
        # Different salts mean different hashes
        assert hash1 != hash2
        # But both should verify against the same password
        assert hasher.verify(password, hash1)
        assert hasher.verify(password, hash2)

    def test_verify_correct_password(self):
        """Test verifying correct password."""
        # Arrange
        hasher = Argon2PasswordHasher()
        password = "correct_password"
        hashed = hasher.hash(password)

        # Act
        result = hasher.verify(password, hashed)

        # Assert
        assert result is True

    def test_verify_wrong_password(self):
        """Test verifying wrong password."""
        # Arrange
        hasher = Argon2PasswordHasher()
        hashed = hasher.hash("correct_password")

        # Act
        result = hasher.verify("wrong_password", hashed)

        # Assert
        assert result is False

    def test_verify_invalid_hash_returns_false(self):
        """Test that verifying with invalid hash returns False (doesn't raise)."""
        # Arrange
        hasher = Argon2PasswordHasher()

        # Act
        result = hasher.verify("password", "completely_invalid_hash")

        # Assert
        # Should return False, not raise an exception
        assert result is False

    def test_hash_long_password(self):
        """Test hashing a very long password."""
        # Arrange
        hasher = Argon2PasswordHasher()
        long_password = "a" * 1000  # 1000 characters

        # Act
        hashed = hasher.hash(long_password)

        # Assert
        assert hashed.startswith("$argon2id$")
        assert hasher.verify(long_password, hashed)

    def test_hash_unicode_password(self):
        """Test hashing passwords with Unicode characters."""
        # Arrange
        hasher = Argon2PasswordHasher()
        unicode_password = "パスワード🔒"  # Japanese + emoji

        # Act
        hashed = hasher.hash(unicode_password)

        # Assert
        assert hashed.startswith("$argon2id$")
        assert hasher.verify(unicode_password, hashed)
        assert not hasher.verify("パスワード", hashed)  # Without emoji


class TestPasswordHasherInterface:
    """Test that both implementations follow the same interface."""

    @pytest.mark.parametrize(
        "hasher_class",
        [FakePasswordHasher, Argon2PasswordHasher],
        ids=["Fake", "Argon2"],
    )
    def test_hash_returns_string(self, hasher_class):
        """Test that hash() returns a string."""
        # Arrange
        hasher = hasher_class()

        # Act
        result = hasher.hash("password")

        # Assert
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.parametrize(
        "hasher_class",
        [FakePasswordHasher, Argon2PasswordHasher],
        ids=["Fake", "Argon2"],
    )
    def test_verify_returns_bool(self, hasher_class):
        """Test that verify() returns a boolean."""
        # Arrange
        hasher = hasher_class()
        hashed = hasher.hash("password")

        # Act
        result_true = hasher.verify("password", hashed)
        result_false = hasher.verify("wrong", hashed)

        # Assert
        assert isinstance(result_true, bool)
        assert isinstance(result_false, bool)
        assert result_true is True
        assert result_false is False

    @pytest.mark.parametrize(
        "hasher_class",
        [FakePasswordHasher, Argon2PasswordHasher],
        ids=["Fake", "Argon2"],
    )
    def test_round_trip(self, hasher_class):
        """Test hash → verify round trip works."""
        # Arrange
        hasher = hasher_class()
        passwords = ["simple", "Complex123!", "with spaces", "🚀emoji"]

        for password in passwords:
            # Act
            hashed = hasher.hash(password)
            is_valid = hasher.verify(password, hashed)

            # Assert
            assert (
                is_valid
            ), f"Failed to verify '{password}' with {hasher_class.__name__}"
