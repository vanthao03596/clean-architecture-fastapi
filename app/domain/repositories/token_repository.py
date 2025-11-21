"""Token repository interface - domain layer abstraction.

This interface defines the contract for storing and managing tokens
(for blacklisting, revocation, and reuse detection).

Why this belongs in the domain:
- Token revocation is a BUSINESS REQUIREMENT for security
- The domain cares about token lifecycle management
- The domain does NOT care about storage mechanism (Redis, DB, memory, etc.)

This supports:
1. Refresh token rotation (OAuth 2.1 best practice)
2. Token revocation/blacklisting
3. Token reuse detection (security)
"""

from abc import ABC, abstractmethod
from datetime import datetime


class TokenMetadata:
    """
    Domain representation of token metadata for tracking and revocation.

    This stores information about issued tokens to enable:
    - Token revocation (blacklisting)
    - Token reuse detection with overlap period
    - Token family tracking (for rotation)
    - Token rotation sequence tracking (for Auth0-style overlap period)
    """

    def __init__(
        self,
        token_id: str,
        user_id: int,
        token_type: str,  # "access" or "refresh"
        issued_at: datetime,
        expires_at: datetime,
        is_revoked: bool = False,
        family_id: str | None = None,  # For token rotation tracking
        used_at: (
            datetime | None
        ) = None,  # When token was first used (for overlap period)
        rotation_sequence: int = 0,  # Position in rotation chain (0, 1, 2, ...)
        parent_token_id: str | None = None,  # Previous token in rotation chain
    ):
        self.token_id = token_id
        self.user_id = user_id
        self.token_type = token_type
        self.issued_at = issued_at
        self.expires_at = expires_at
        self.is_revoked = is_revoked
        self.family_id = family_id  # Groups related tokens together
        self.used_at = used_at  # Timestamp of first use (enables overlap period)
        self.rotation_sequence = rotation_sequence  # Order in rotation chain
        self.parent_token_id = parent_token_id  # Previous token for validation


class ITokenRepository(ABC):
    """
    Interface for token storage and revocation management.

    This abstraction allows the application layer to manage token
    lifecycle without depending on a specific storage mechanism.
    """

    @abstractmethod
    async def store_token(self, metadata: TokenMetadata) -> None:
        """
        Store token metadata for tracking.

        Args:
            metadata: Token metadata to store

        Example:
            await token_repo.store_token(TokenMetadata(
                token_id="abc123",
                user_id=42,
                token_type="refresh",
                issued_at=datetime.now(timezone.utc),
                expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            ))
        """
        pass

    @abstractmethod
    async def revoke_token(self, token_id: str) -> None:
        """
        Revoke a specific token by its ID.

        Revoked tokens should fail verification even if not expired.

        Args:
            token_id: Unique identifier of the token to revoke

        Example:
            await token_repo.revoke_token("abc123")
        """
        pass

    @abstractmethod
    async def revoke_token_family(self, family_id: str) -> None:
        """
        Revoke all tokens in a token family.

        Used when token reuse is detected - invalidates all tokens
        in the rotation chain to prevent further attacks.

        Args:
            family_id: Family identifier for related tokens

        Example:
            # When token reuse detected, revoke entire family
            await token_repo.revoke_token_family("family-xyz")
        """
        pass

    @abstractmethod
    async def is_token_revoked(self, token_id: str) -> bool:
        """
        Check if a token has been revoked.

        Args:
            token_id: Token identifier to check

        Returns:
            True if token is revoked, False otherwise

        Example:
            if await token_repo.is_token_revoked("abc123"):
                raise InvalidTokenError("Token has been revoked")
        """
        pass

    @abstractmethod
    async def get_token_metadata(self, token_id: str) -> TokenMetadata | None:
        """
        Retrieve token metadata by token ID.

        Args:
            token_id: Token identifier

        Returns:
            TokenMetadata if found, None otherwise

        Example:
            metadata = await token_repo.get_token_metadata("abc123")
            if metadata and metadata.is_revoked:
                # Token was revoked
        """
        pass

    @abstractmethod
    async def cleanup_expired_tokens(self) -> int:
        """
        Remove expired tokens from storage.

        Should be called periodically to prevent unbounded storage growth.

        Returns:
            Number of tokens removed

        Example:
            # Background task runs every hour
            removed = await token_repo.cleanup_expired_tokens()
            logger.info(f"Cleaned up {removed} expired tokens")
        """
        pass

    @abstractmethod
    async def mark_token_used(self, token_id: str, used_at: datetime) -> None:
        """
        Mark when a refresh token was first used.

        This enables the overlap period feature for token rotation.
        The first use timestamp allows checking if subsequent uses
        fall within the overlap window.

        Args:
            token_id: Token identifier
            used_at: Timestamp when token was first used

        Example:
            # When processing refresh token request
            await token_repo.mark_token_used("abc123", datetime.now(timezone.utc))
        """
        pass

    @abstractmethod
    async def get_latest_token_in_family(self, family_id: str) -> TokenMetadata | None:
        """
        Get the most recent (highest rotation_sequence) token in a family.

        Used to determine if a token being reused is the PREVIOUS token
        (allowed within overlap period) or an OLDER token (breach).

        Args:
            family_id: Family identifier

        Returns:
            TokenMetadata of the latest token, None if family not found

        Example:
            # Check if token being used is the previous one
            latest = await token_repo.get_latest_token_in_family("family-xyz")
            if latest and latest.parent_token_id == current_token_id:
                # This is the previous token - overlap logic applies
        """
        pass

    @abstractmethod
    async def is_within_overlap_period(
        self, token_id: str, overlap_seconds: int
    ) -> bool:
        """
        Check if a token's first use was within the overlap period.

        Returns True if the token was first used within the specified
        number of seconds from now. Used to allow reuse of the previous
        token during the overlap window.

        Args:
            token_id: Token identifier
            overlap_seconds: Overlap period in seconds (e.g., 5)

        Returns:
            True if within overlap period, False otherwise

        Example:
            # Allow reuse if within 5-second window
            if await token_repo.is_within_overlap_period("abc123", 5):
                # Token can be reused without triggering breach detection
        """
        pass
