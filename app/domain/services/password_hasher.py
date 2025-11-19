"""Password hashing interface - domain service abstraction.

This interface defines the contract for password hashing operations.
It belongs in the domain layer because password hashing is a BUSINESS REQUIREMENT,
not an infrastructure detail.

The domain cares that passwords must be:
1. Hashed before storage (security requirement)
2. Verifiable during authentication (business use case)

The domain does NOT care:
- Which algorithm is used (Argon2, bcrypt, scrypt)
- Which library implements it (pwdlib, passlib, bcrypt)
- Implementation details (salt generation, iteration counts)

This is the Dependency Inversion Principle in action:
- High-level policy (UserService) depends on this abstraction
- Low-level detail (Argon2PasswordHasher) implements this abstraction
- Dependencies point INWARD toward the domain
"""

from abc import ABC, abstractmethod


class IPasswordHasher(ABC):
    """
    Interface for password hashing operations.

    This abstraction allows the application layer to hash and verify passwords
    without depending on a specific hashing library or algorithm.

    Implementations must be cryptographically secure and use appropriate
    salt generation and iteration counts.
    """

    @abstractmethod
    def hash(self, plain_password: str) -> str:
        """
        Hash a plain text password.

        The implementation must:
        1. Generate a unique salt
        2. Use a cryptographically secure algorithm
        3. Return a string that includes both hash and salt (for verification)

        Args:
            plain_password: The plain text password to hash

        Returns:
            Hashed password string (format depends on implementation)

        Example:
            hasher = SomePasswordHasher()
            hashed = hasher.hash("my_password")
            # hashed might be: "$argon2id$v=19$m=65536,t=3,p=4$..."
        """
        pass

    @abstractmethod
    def verify(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verify a plain text password against a hashed password.

        Args:
            plain_password: The plain text password to verify
            hashed_password: The previously hashed password to check against

        Returns:
            True if password matches, False otherwise

        Example:
            hasher = SomePasswordHasher()
            hashed = hasher.hash("my_password")

            hasher.verify("my_password", hashed)  # Returns: True
            hasher.verify("wrong_password", hashed)  # Returns: False
        """
        pass
