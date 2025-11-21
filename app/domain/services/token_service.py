"""Token service interface - domain layer abstraction.

This interface belongs in the domain layer because token generation
and validation are BUSINESS REQUIREMENTS for authentication, not
implementation details.

The domain cares that:
1. Users can authenticate and receive access tokens
2. Tokens can be validated to identify users
3. Tokens expire after a certain time (security requirement)

The domain does NOT care:
- What token format is used (JWT, opaque tokens, etc.)
- Which library implements it (PyJWT, jose, etc.)
- How tokens are encoded/signed (HS256, RS256, etc.)
"""

from abc import ABC, abstractmethod
from datetime import UTC, datetime


class TokenData:
    """
    Domain representation of decoded token data.

    This is a pure domain object with no framework dependencies.
    """

    def __init__(
        self,
        user_id: int,
        email: str,
        issued_at: datetime,
        expires_at: datetime,
        token_id: str | None = None,  # JWT ID (jti) for tracking
        family_id: str | None = None,  # Token family for rotation
        parent_token_id: str | None = None,  # Previous token in rotation chain
        rotation_sequence: int = 0,  # Position in rotation chain (0, 1, 2, ...)
    ):
        self.user_id = user_id
        self.email = email
        self.issued_at = issued_at
        self.expires_at = expires_at
        self.token_id = token_id
        self.family_id = family_id
        self.parent_token_id = parent_token_id
        self.rotation_sequence = rotation_sequence

    @property
    def is_expired(self) -> bool:
        """Check if token is expired."""
        from datetime import datetime

        return datetime.now(UTC) > self.expires_at


class ITokenService(ABC):
    """
    Interface for token generation and validation.

    This abstraction allows the application layer to work with
    authentication tokens without depending on a specific token
    format or library.
    """

    @abstractmethod
    def generate_access_token(self, user_id: int, email: str) -> str:
        """
        Generate an access token for a user.

        Args:
            user_id: User's unique identifier
            email: User's email address

        Returns:
            Encoded token string

        Example:
            token = token_service.generate_access_token(
                user_id=123,
                email="user@example.com"
            )
            # Returns: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
        """
        pass

    @abstractmethod
    def generate_refresh_token(
        self,
        user_id: int,
        email: str,
        family_id: str | None = None,
        parent_token_id: str | None = None,
        rotation_sequence: int = 0,
    ) -> str:
        """
        Generate a refresh token for obtaining new access tokens.

        Refresh tokens typically have longer expiration times than
        access tokens.

        Args:
            user_id: User's unique identifier
            email: User's email address
            family_id: Optional token family ID for rotation tracking
            parent_token_id: Optional ID of previous token in rotation chain
            rotation_sequence: Position in rotation chain (0, 1, 2, ...)

        Returns:
            Encoded refresh token string
        """
        pass

    @abstractmethod
    def verify_token(self, token: str) -> TokenData | None:
        """
        Verify and decode a token.

        Args:
            token: Encoded token string to verify

        Returns:
            TokenData if token is valid, None if invalid/expired

        Example:
            token_data = token_service.verify_token(token_string)
            if token_data and not token_data.is_expired:
                user_id = token_data.user_id
                # Grant access
            else:
                # Deny access
        """
        pass

    @abstractmethod
    def verify_refresh_token(self, token: str) -> TokenData | None:
        """
        Verify and decode a refresh token.

        This may have different validation rules than access tokens
        (e.g., checking if token has been revoked in a blacklist).

        Args:
            token: Encoded refresh token string

        Returns:
            TokenData if token is valid, None otherwise
        """
        pass
