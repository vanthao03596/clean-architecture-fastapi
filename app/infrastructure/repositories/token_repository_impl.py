"""In-memory token repository implementation.

This is an INFRASTRUCTURE detail. The domain layer (ITokenRepository interface)
defines WHAT we need (token storage/revocation), while this implementation
defines HOW we do it (using in-memory dictionaries).

Dependency flow:
    AuthService (application) → ITokenRepository (domain) ← InMemoryTokenRepository (infrastructure)

This implementation:
1. Uses in-memory storage (suitable for development and small deployments)
2. Can be replaced with RedisTokenRepository for production
3. Thread-safe using asyncio locks
4. Automatically cleans up expired tokens

For production, replace with Redis:
- Redis provides persistence across restarts
- Redis supports distributed deployments
- Redis has built-in TTL for automatic cleanup
"""

import asyncio
from datetime import UTC, datetime

from app.domain.repositories.token_repository import ITokenRepository, TokenMetadata


class InMemoryTokenRepository(ITokenRepository):
    """
    In-memory implementation of token repository.

    Stores tokens in Python dictionaries. Suitable for:
    - Development and testing
    - Single-server deployments
    - Low-traffic applications

    Limitations:
    - Data lost on restart
    - Not suitable for multi-server deployments
    - Memory grows with token count (mitigated by cleanup)

    For production, consider RedisTokenRepository instead.
    """

    def __init__(self) -> None:
        """Initialize in-memory storage."""
        # Store token metadata by token_id
        self._tokens: dict[str, TokenMetadata] = {}

        # Store token families for quick revocation
        # family_id -> set of token_ids
        self._families: dict[str, set[str]] = {}

        # Lock for thread-safe operations
        self._lock = asyncio.Lock()

    async def store_token(self, metadata: TokenMetadata) -> None:
        """
        Store token metadata in memory.

        Args:
            metadata: Token metadata to store
        """
        async with self._lock:
            # Store token metadata
            self._tokens[metadata.token_id] = metadata

            # Track family if present
            if metadata.family_id:
                if metadata.family_id not in self._families:
                    self._families[metadata.family_id] = set()
                self._families[metadata.family_id].add(metadata.token_id)

    async def revoke_token(self, token_id: str) -> None:
        """
        Revoke a specific token.

        Args:
            token_id: Token identifier to revoke
        """
        async with self._lock:
            if token_id in self._tokens:
                self._tokens[token_id].is_revoked = True

    async def revoke_token_family(self, family_id: str) -> None:
        """
        Revoke all tokens in a family.

        Called when token reuse is detected to invalidate entire chain.

        Args:
            family_id: Family identifier
        """
        async with self._lock:
            if family_id in self._families:
                # Revoke all tokens in the family
                for token_id in self._families[family_id]:
                    if token_id in self._tokens:
                        self._tokens[token_id].is_revoked = True

    async def is_token_revoked(self, token_id: str) -> bool:
        """
        Check if token is revoked.

        Args:
            token_id: Token identifier

        Returns:
            True if revoked, False otherwise
        """
        async with self._lock:
            if token_id not in self._tokens:
                # Unknown token - treat as not revoked
                # (allows system to work without storing all tokens)
                return False
            return self._tokens[token_id].is_revoked

    async def get_token_metadata(self, token_id: str) -> TokenMetadata | None:
        """
        Retrieve token metadata.

        Args:
            token_id: Token identifier

        Returns:
            TokenMetadata if found, None otherwise
        """
        async with self._lock:
            return self._tokens.get(token_id)

    async def cleanup_expired_tokens(self) -> int:
        """
        Remove expired tokens from memory.

        Should be called periodically to prevent memory growth.

        Returns:
            Number of tokens removed
        """
        async with self._lock:
            now = datetime.now(UTC)
            expired_tokens = [
                token_id
                for token_id, metadata in self._tokens.items()
                if metadata.expires_at < now
            ]

            # Remove expired tokens
            for token_id in expired_tokens:
                metadata = self._tokens[token_id]

                # Remove from family tracking
                if metadata.family_id and metadata.family_id in self._families:
                    self._families[metadata.family_id].discard(token_id)
                    # Remove empty families
                    if not self._families[metadata.family_id]:
                        del self._families[metadata.family_id]

                # Remove token
                del self._tokens[token_id]

            return len(expired_tokens)

    async def get_stats(self) -> dict[str, int]:
        """
        Get repository statistics (useful for monitoring).

        Returns:
            Dictionary with token counts and stats
        """
        async with self._lock:
            total_tokens = len(self._tokens)
            revoked_tokens = sum(1 for t in self._tokens.values() if t.is_revoked)
            active_families = len(self._families)

            return {
                "total_tokens": total_tokens,
                "revoked_tokens": revoked_tokens,
                "active_tokens": total_tokens - revoked_tokens,
                "active_families": active_families,
            }

    async def mark_token_used(self, token_id: str, used_at: datetime) -> None:
        """
        Mark when a refresh token was first used.

        Only sets used_at if it hasn't been set before (first use only).

        Args:
            token_id: Token identifier
            used_at: Timestamp when token was first used
        """
        async with self._lock:
            if token_id in self._tokens:
                metadata = self._tokens[token_id]
                # Only mark on first use
                if metadata.used_at is None:
                    metadata.used_at = used_at

    async def get_latest_token_in_family(self, family_id: str) -> TokenMetadata | None:
        """
        Get the most recent token in a family by rotation_sequence.

        Args:
            family_id: Family identifier

        Returns:
            TokenMetadata of the latest token, None if family not found
        """
        async with self._lock:
            if family_id not in self._families:
                return None

            # Get all tokens in family
            family_tokens = [
                self._tokens[token_id]
                for token_id in self._families[family_id]
                if token_id in self._tokens
            ]

            if not family_tokens:
                return None

            # Return token with highest rotation_sequence
            return max(family_tokens, key=lambda t: t.rotation_sequence)

    async def is_within_overlap_period(
        self, token_id: str, overlap_seconds: int
    ) -> bool:
        """
        Check if a token's first use was within the overlap period.

        Args:
            token_id: Token identifier
            overlap_seconds: Overlap period in seconds

        Returns:
            True if within overlap period, False otherwise
        """
        async with self._lock:
            if token_id not in self._tokens:
                return False

            metadata = self._tokens[token_id]

            # If never used, not within overlap period
            if metadata.used_at is None:
                return False

            # Check if used_at is within overlap_seconds from now
            now = datetime.now(UTC)
            time_since_use = (now - metadata.used_at).total_seconds()

            return time_since_use <= overlap_seconds
