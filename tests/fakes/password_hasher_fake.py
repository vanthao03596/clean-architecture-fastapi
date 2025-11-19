"""Fake password hasher for testing.

This fake implementation allows testing user-related functionality without
the performance overhead of real cryptographic hashing.

WHY USE A FAKE?
In unit tests, we want to test business logic (e.g., "email must be unique"),
not cryptographic algorithms. Real Argon2 hashing:
- Takes ~100ms per hash (intentionally slow for security)
- Makes tests slow (testing 100 users = 10 seconds just for hashing)
- Adds no value (we trust pwdlib's implementation)

The fake hasher:
- Returns predictable hashes (plain text + prefix)
- Executes in microseconds
- Makes test assertions easier (you can see what was hashed)
- Allows testing password verification logic

WHEN NOT TO USE:
Integration tests that verify the actual Argon2 implementation should use
the real Argon2PasswordHasher, not this fake.
"""

from app.domain.services.password_hasher import IPasswordHasher


class FakePasswordHasher(IPasswordHasher):
    """
    Fake password hasher for unit testing.

    This implementation:
    1. Prefixes passwords with "HASHED:" instead of real hashing
    2. Verifies by comparing the plain password with the hash
    3. Maintains the same interface as the real hasher

    Usage in tests:
        # Setup
        hasher = FakePasswordHasher()

        # Hash a password
        hashed = hasher.hash("password123")
        # Returns: "HASHED:password123"

        # Verify password
        hasher.verify("password123", "HASHED:password123")  # True
        hasher.verify("wrong", "HASHED:password123")  # False

    Security Note:
        NEVER use this in production! This is for testing only.
        The fake hasher provides no security - it's just string concatenation.
    """

    # Prefix to identify fake hashes (useful when debugging tests)
    HASH_PREFIX = "HASHED:"

    def hash(self, plain_password: str) -> str:
        """
        "Hash" a password by prefixing it.

        This is intentionally insecure - it's a test double, not real crypto.

        Args:
            plain_password: The plain text password

        Returns:
            Fake hash (just the password with a prefix)

        Example:
            >>> hasher = FakePasswordHasher()
            >>> hasher.hash("test123")
            'HASHED:test123'
        """
        return f"{self.HASH_PREFIX}{plain_password}"

    def verify(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verify a password by comparing against the fake hash.

        Args:
            plain_password: The plain text password to verify
            hashed_password: The fake hash to check against

        Returns:
            True if the hash matches the expected format, False otherwise

        Example:
            >>> hasher = FakePasswordHasher()
            >>> hashed = hasher.hash("mypassword")
            >>> hasher.verify("mypassword", hashed)
            True
            >>> hasher.verify("wrongpassword", hashed)
            False
        """
        # Check if it's a valid fake hash
        if not hashed_password.startswith(self.HASH_PREFIX):
            return False

        # Extract the "hashed" password (remove prefix)
        expected_password = hashed_password[len(self.HASH_PREFIX) :]

        # Compare with plain password
        return plain_password == expected_password

    # Helper methods for testing

    def is_fake_hash(self, hashed_password: str) -> bool:
        """
        Check if a hash was created by this fake hasher.

        Useful in tests to verify that the fake hasher is being used.

        Args:
            hashed_password: The hash to check

        Returns:
            True if this is a fake hash, False otherwise

        Example:
            >>> hasher = FakePasswordHasher()
            >>> hasher.is_fake_hash("HASHED:password")
            True
            >>> hasher.is_fake_hash("$argon2id$...")
            False
        """
        return hashed_password.startswith(self.HASH_PREFIX)

    def extract_plain_password(self, hashed_password: str) -> str:
        """
        Extract the original password from a fake hash.

        Useful for debugging tests or making assertions about what was hashed.

        Args:
            hashed_password: The fake hash

        Returns:
            The original plain password

        Raises:
            ValueError: If the hash is not a fake hash

        Example:
            >>> hasher = FakePasswordHasher()
            >>> hashed = hasher.hash("secret123")
            >>> hasher.extract_plain_password(hashed)
            'secret123'
        """
        if not self.is_fake_hash(hashed_password):
            raise ValueError(
                f"Not a fake hash: {hashed_password}. "
                f"Expected to start with '{self.HASH_PREFIX}'"
            )

        return hashed_password[len(self.HASH_PREFIX) :]
