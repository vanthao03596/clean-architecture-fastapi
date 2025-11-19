"""Fake token service for testing without real JWT implementation.

This fake token service implements simple, predictable token generation
and validation for testing purposes.
"""

from typing import Optional
from datetime import datetime, timezone, timedelta
import uuid

from app.domain.services.token_service import ITokenService, TokenData


class FakeTokenService(ITokenService):
    """
    In-memory fake implementation of ITokenService.

    This is used for unit testing services without real JWT encoding/decoding.
    Tokens are simple strings with predictable format for easy testing.

    Token format: "access_<user_id>_<email>" or "refresh_<user_id>_<email>_<token_id>"

    Usage:
        token_service = FakeTokenService()
        access_token = token_service.generate_access_token(user_id=1, email="test@example.com")
        # Returns: "access_1_test@example.com"
    """

    def __init__(
        self,
        access_token_expire_minutes: int = 30,
        refresh_token_expire_days: int = 7,
    ):
        """
        Initialize fake token service with configurable expiration times.

        Args:
            access_token_expire_minutes: Access token lifetime in minutes
            refresh_token_expire_days: Refresh token lifetime in days
        """
        self.access_token_expire_minutes = access_token_expire_minutes
        self.refresh_token_expire_days = refresh_token_expire_days
        # Store tokens for verification
        self._tokens: dict[str, TokenData] = {}

    def generate_access_token(self, user_id: int, email: str) -> str:
        """Generate a fake access token."""
        token = f"access_{user_id}_{email}"

        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(minutes=self.access_token_expire_minutes)

        token_data = TokenData(
            user_id=user_id,
            email=email,
            issued_at=now,
            expires_at=expires_at,
        )

        self._tokens[token] = token_data
        return token

    def generate_refresh_token(
        self,
        user_id: int,
        email: str,
        family_id: Optional[str] = None,
        parent_token_id: Optional[str] = None,
        rotation_sequence: int = 0,
    ) -> str:
        """Generate a fake refresh token with rotation support."""
        token_id = str(uuid.uuid4())

        # Generate family_id if not provided (new token family)
        if family_id is None:
            family_id = str(uuid.uuid4())

        # Include token_id in token string for uniqueness
        token = f"refresh_{user_id}_{email}_{token_id}"

        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(days=self.refresh_token_expire_days)

        token_data = TokenData(
            user_id=user_id,
            email=email,
            issued_at=now,
            expires_at=expires_at,
            token_id=token_id,
            family_id=family_id,
            parent_token_id=parent_token_id,
            rotation_sequence=rotation_sequence,
        )

        self._tokens[token] = token_data
        return token

    def verify_token(self, token: str) -> Optional[TokenData]:
        """Verify and decode a fake access token."""
        if token not in self._tokens:
            return None

        token_data = self._tokens[token]

        # Check if expired
        if token_data.is_expired:
            return None

        return token_data

    def verify_refresh_token(self, token: str) -> Optional[TokenData]:
        """Verify and decode a fake refresh token."""
        if token not in self._tokens:
            return None

        token_data = self._tokens[token]

        # Check if expired
        if token_data.is_expired:
            return None

        return token_data

    # Helper methods for testing

    def clear(self) -> None:
        """Clear all stored tokens (useful for test teardown)."""
        self._tokens.clear()

    def count(self) -> int:
        """Get total number of tokens stored (useful for assertions)."""
        return len(self._tokens)

    def expire_token(self, token: str) -> None:
        """Force a token to be expired (useful for testing expiration)."""
        if token in self._tokens:
            token_data = self._tokens[token]
            # Set expires_at to the past
            self._tokens[token] = TokenData(
                user_id=token_data.user_id,
                email=token_data.email,
                issued_at=token_data.issued_at,
                expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
                token_id=token_data.token_id,
                family_id=token_data.family_id,
                parent_token_id=token_data.parent_token_id,
                rotation_sequence=token_data.rotation_sequence,
            )
