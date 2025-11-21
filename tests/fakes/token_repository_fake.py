"""Fake token repository for testing without a database.

This fake repository stores token metadata in memory and implements the same
interface as the real repository, allowing you to test services in isolation.
"""

from datetime import UTC, datetime

from app.domain.repositories.token_repository import ITokenRepository, TokenMetadata


class FakeTokenRepository(ITokenRepository):
    """
    In-memory fake implementation of ITokenRepository.

    This is used for unit testing services without a real database.
    It implements the same interface as the real repository but stores
    token metadata in memory using a dictionary.

    Usage:
        repo = FakeTokenRepository()
        metadata = TokenMetadata(
            token_id="abc123",
            user_id=1,
            token_type="refresh",
            issued_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        await repo.store_token(metadata)
    """

    def __init__(self) -> None:
        """Initialize with empty in-memory storage."""
        self._tokens: dict[str, TokenMetadata] = {}

    async def store_token(self, metadata: TokenMetadata) -> None:
        """Store token metadata in memory."""
        self._tokens[metadata.token_id] = metadata

    async def revoke_token(self, token_id: str) -> None:
        """Revoke a specific token by marking it as revoked."""
        if token_id in self._tokens:
            metadata = self._tokens[token_id]
            # Create new metadata with is_revoked=True
            self._tokens[token_id] = TokenMetadata(
                token_id=metadata.token_id,
                user_id=metadata.user_id,
                token_type=metadata.token_type,
                issued_at=metadata.issued_at,
                expires_at=metadata.expires_at,
                is_revoked=True,
                family_id=metadata.family_id,
                used_at=metadata.used_at,
                rotation_sequence=metadata.rotation_sequence,
                parent_token_id=metadata.parent_token_id,
            )

    async def revoke_token_family(self, family_id: str) -> None:
        """Revoke all tokens in a token family."""
        for token_id, metadata in self._tokens.items():
            if metadata.family_id == family_id:
                # Mark all tokens in family as revoked
                self._tokens[token_id] = TokenMetadata(
                    token_id=metadata.token_id,
                    user_id=metadata.user_id,
                    token_type=metadata.token_type,
                    issued_at=metadata.issued_at,
                    expires_at=metadata.expires_at,
                    is_revoked=True,
                    family_id=metadata.family_id,
                    used_at=metadata.used_at,
                    rotation_sequence=metadata.rotation_sequence,
                    parent_token_id=metadata.parent_token_id,
                )

    async def is_token_revoked(self, token_id: str) -> bool:
        """Check if a token has been revoked."""
        if token_id not in self._tokens:
            return False
        return self._tokens[token_id].is_revoked

    async def get_token_metadata(self, token_id: str) -> TokenMetadata | None:
        """Retrieve token metadata by token ID."""
        return self._tokens.get(token_id)

    async def cleanup_expired_tokens(self) -> int:
        """Remove expired tokens from storage."""
        now = datetime.now(UTC)
        expired_tokens = [
            token_id
            for token_id, metadata in self._tokens.items()
            if metadata.expires_at < now
        ]

        for token_id in expired_tokens:
            del self._tokens[token_id]

        return len(expired_tokens)

    async def mark_token_used(self, token_id: str, used_at: datetime) -> None:
        """Mark when a refresh token was first used."""
        if token_id in self._tokens:
            metadata = self._tokens[token_id]
            # Only set used_at if not already set (first use only)
            if metadata.used_at is None:
                self._tokens[token_id] = TokenMetadata(
                    token_id=metadata.token_id,
                    user_id=metadata.user_id,
                    token_type=metadata.token_type,
                    issued_at=metadata.issued_at,
                    expires_at=metadata.expires_at,
                    is_revoked=metadata.is_revoked,
                    family_id=metadata.family_id,
                    used_at=used_at,
                    rotation_sequence=metadata.rotation_sequence,
                    parent_token_id=metadata.parent_token_id,
                )

    async def get_latest_token_in_family(self, family_id: str) -> TokenMetadata | None:
        """Get the most recent (highest rotation_sequence) token in a family."""
        family_tokens = [
            metadata
            for metadata in self._tokens.values()
            if metadata.family_id == family_id
        ]

        if not family_tokens:
            return None

        # Return token with highest rotation_sequence
        return max(family_tokens, key=lambda t: t.rotation_sequence)

    async def is_within_overlap_period(
        self, token_id: str, overlap_seconds: int
    ) -> bool:
        """Check if a token's first use was within the overlap period."""
        metadata = await self.get_token_metadata(token_id)

        if not metadata or metadata.used_at is None:
            return False

        now = datetime.now(UTC)
        time_since_first_use = (now - metadata.used_at).total_seconds()

        return time_since_first_use <= overlap_seconds

    # Helper methods for testing

    def clear(self) -> None:
        """Clear all data (useful for test teardown)."""
        self._tokens.clear()

    def count(self) -> int:
        """Get total number of tokens (useful for assertions)."""
        return len(self._tokens)

    def get_all_tokens(self) -> list[TokenMetadata]:
        """Get all tokens (useful for inspection in tests)."""
        return list(self._tokens.values())

    def get_tokens_by_family(self, family_id: str) -> list[TokenMetadata]:
        """Get all tokens in a family (useful for testing rotation)."""
        return [
            metadata
            for metadata in self._tokens.values()
            if metadata.family_id == family_id
        ]
