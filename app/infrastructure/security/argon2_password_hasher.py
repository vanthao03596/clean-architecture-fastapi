"""Argon2 password hasher implementation using pwdlib.

This is an INFRASTRUCTURE detail. The domain layer (IPasswordHasher interface)
defines WHAT we need (hash and verify operations), while this implementation
defines HOW we do it (using Argon2 via pwdlib).

Dependency flow:
    UserService (application) → IPasswordHasher (domain) ← Argon2PasswordHasher (infrastructure)

Notice the dependency points INWARD:
- UserService depends on IPasswordHasher (domain abstraction)
- Argon2PasswordHasher implements IPasswordHasher (infrastructure depends on domain)
- pwdlib is only imported here (external library isolated to infrastructure)

This design allows us to:
1. Test UserService with a FakePasswordHasher (no real crypto in unit tests)
2. Swap algorithms (bcrypt, scrypt) without changing application code
3. Keep the domain layer pure and framework-agnostic
"""

from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

from app.domain.services.password_hasher import IPasswordHasher


class Argon2PasswordHasher(IPasswordHasher):
    """
    Production password hasher using Argon2id algorithm via pwdlib.

    Argon2 is the winner of the Password Hashing Competition (2015) and is
    recommended by OWASP for password storage. The Argon2id variant provides
    both side-channel and GPU attack resistance.

    Configuration:
    - Algorithm: Argon2id (hybrid mode combining Argon2i and Argon2d)
    - Memory cost: 65536 KB (64 MB) - makes GPU attacks expensive
    - Time cost: 3 iterations - balances security and performance
    - Parallelism: 4 threads - utilizes modern CPUs

    These are pwdlib's secure defaults. For custom configurations, modify
    the Argon2Hasher initialization.

    Usage:
        hasher = Argon2PasswordHasher()

        # Hash a password
        hashed = hasher.hash("user_password_123")
        # Returns: "$argon2id$v=19$m=65536,t=3,p=4$<salt>$<hash>"

        # Verify a password
        is_valid = hasher.verify("user_password_123", hashed)
        # Returns: True

        is_valid = hasher.verify("wrong_password", hashed)
        # Returns: False
    """

    def __init__(self):
        """
        Initialize Argon2 password hasher with secure defaults.

        pwdlib's PasswordHash automatically:
        1. Generates cryptographically secure salts
        2. Uses Argon2id with recommended parameters
        3. Handles hash format encoding/decoding
        """
        # PasswordHash can support multiple hashers (for password migration scenarios)
        # We only use Argon2 for new passwords
        self._password_hash = PasswordHash((Argon2Hasher(),))

    def hash(self, plain_password: str) -> str:
        """
        Hash a plain text password using Argon2id.

        The resulting hash contains:
        - Algorithm identifier ($argon2id$)
        - Version (v=19)
        - Parameters (memory, time, parallelism)
        - Salt (randomly generated, base64 encoded)
        - Hash (derived key, base64 encoded)

        Args:
            plain_password: The plain text password to hash

        Returns:
            Argon2 hash string (self-contained, includes salt and parameters)

        Example:
            >>> hasher = Argon2PasswordHasher()
            >>> hashed = hasher.hash("my_secure_password")
            >>> print(hashed)
            "$argon2id$v=19$m=65536,t=3,p=4$c29tZXNhbHQ$..."

        Note:
            Each call generates a unique salt, so hashing the same password
            twice will produce different hashes (this is correct behavior).
        """
        return self._password_hash.hash(plain_password)

    def verify(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verify a plain text password against an Argon2 hash.

        This method:
        1. Extracts the salt and parameters from the hash
        2. Re-hashes the plain password using the same salt/parameters
        3. Performs a constant-time comparison to prevent timing attacks

        Args:
            plain_password: The plain text password to verify
            hashed_password: The Argon2 hash to check against

        Returns:
            True if the password matches, False otherwise

        Example:
            >>> hasher = Argon2PasswordHasher()
            >>> hashed = hasher.hash("correct_password")
            >>> hasher.verify("correct_password", hashed)
            True
            >>> hasher.verify("wrong_password", hashed)
            False

        Security Notes:
        - Uses constant-time comparison to prevent timing attacks
        - Safe to call with invalid hashes (returns False, doesn't raise)
        - Resistant to length extension attacks
        """
        try:
            # pwdlib's verify method handles all security considerations
            # Returns (is_valid, needs_rehash) tuple
            # We only care about validity here
            is_valid, _ = self._password_hash.verify_and_update(
                plain_password, hashed_password
            )
            return is_valid
        except Exception:
            # If hash is malformed or verification fails, return False
            # Don't leak information about why verification failed
            return False
