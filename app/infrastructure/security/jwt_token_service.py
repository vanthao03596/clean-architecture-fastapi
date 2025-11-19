"""JWT token service implementation using PyJWT.

This is an INFRASTRUCTURE detail. The domain layer (ITokenService interface)
defines WHAT we need (token generation/validation), while this implementation
defines HOW we do it (using JWT via PyJWT library).

Dependency flow:
    AuthService (application) → ITokenService (domain) ← JWTTokenService (infrastructure)

This design allows us to:
1. Test AuthService with a FakeTokenService (no real JWT in unit tests)
2. Swap token implementations (OAuth, opaque tokens) without changing application code
3. Keep the domain layer pure and framework-agnostic
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
import uuid

import jwt
from jwt.exceptions import InvalidTokenError, ExpiredSignatureError

from app.domain.services.token_service import ITokenService, TokenData
from app.domain.repositories.token_repository import ITokenRepository, TokenMetadata


class JWTTokenService(ITokenService):
    """
    Production token service using JWT (JSON Web Tokens) via PyJWT.

    JWT Structure:
    - Header: Algorithm and token type (e.g., {"alg": "HS256", "typ": "JWT"})
    - Payload: Claims (user_id, email, exp, iat, type)
    - Signature: HMAC signature using secret key

    Token Types:
    - Access Token: Short-lived (default: 30 minutes), used for API access
    - Refresh Token: Long-lived (default: 7 days), used to obtain new access tokens

    Security Considerations:
    - Uses HS256 (HMAC with SHA-256) for signing
    - Secret key must be at least 32 characters (enforced in Settings)
    - Tokens include expiration time (exp claim)
    - Tokens include issued-at time (iat claim)
    - Token type is stored in payload to prevent access/refresh token confusion
    """

    def __init__(
        self,
        secret_key: str,
        token_repository: ITokenRepository,
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 30,
        refresh_token_expire_days: int = 7,
    ):
        """
        Initialize JWT token service.

        Args:
            secret_key: Secret key for signing tokens (min 32 characters)
            token_repository: Repository for token tracking and revocation
            algorithm: JWT signing algorithm (default: HS256)
            access_token_expire_minutes: Access token lifetime in minutes
            refresh_token_expire_days: Refresh token lifetime in days

        Raises:
            ValueError: If secret_key is too short
        """
        if len(secret_key) < 32:
            raise ValueError("Secret key must be at least 32 characters long")

        self._secret_key = secret_key
        self._token_repository = token_repository
        self._algorithm = algorithm
        self._access_token_expire_minutes = access_token_expire_minutes
        self._refresh_token_expire_days = refresh_token_expire_days

    def generate_access_token(self, user_id: int, email: str) -> str:
        """
        Generate a JWT access token.

        The token payload contains:
        - sub (subject): User ID
        - email: User's email
        - exp (expiration): When token expires
        - iat (issued at): When token was created
        - jti (JWT ID): Unique token identifier
        - type: "access" (to distinguish from refresh tokens)

        Args:
            user_id: User's unique identifier
            email: User's email address

        Returns:
            Encoded JWT string

        Example:
            >>> service = JWTTokenService(secret_key="x" * 32, token_repository=repo)
            >>> token = service.generate_access_token(123, "user@example.com")
            >>> print(token)
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjMi..."
        """
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(minutes=self._access_token_expire_minutes)
        token_id = str(uuid.uuid4())

        payload = {
            "sub": str(user_id),  # Subject (user ID)
            "email": email,
            "exp": expires_at,  # Expiration time
            "iat": now,  # Issued at
            "jti": token_id,  # JWT ID (unique identifier)
            "type": "access",  # Token type
        }

        return jwt.encode(payload, self._secret_key, algorithm=self._algorithm)

    def generate_refresh_token(
        self,
        user_id: int,
        email: str,
        family_id: Optional[str] = None,
        parent_token_id: Optional[str] = None,
        rotation_sequence: int = 0,
    ) -> str:
        """
        Generate a JWT refresh token.

        Refresh tokens have a longer lifetime and are used to obtain
        new access tokens without re-authenticating.

        For token rotation, a family_id groups related tokens together.
        When token reuse is detected, the entire family is revoked.

        Args:
            user_id: User's unique identifier
            email: User's email address
            family_id: Optional token family ID for rotation tracking
            parent_token_id: Optional ID of previous token in rotation chain
            rotation_sequence: Position in rotation chain (0, 1, 2, ...)

        Returns:
            Encoded JWT refresh token
        """
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(days=self._refresh_token_expire_days)
        token_id = str(uuid.uuid4())

        # If no family_id provided, create a new family
        if family_id is None:
            family_id = str(uuid.uuid4())

        payload = {
            "sub": str(user_id),
            "email": email,
            "exp": expires_at,
            "iat": now,
            "jti": token_id,  # JWT ID (unique identifier)
            "fid": family_id,  # Family ID for token rotation
            "pid": parent_token_id,  # Parent token ID (previous in chain)
            "seq": rotation_sequence,  # Rotation sequence number
            "type": "refresh",  # Mark as refresh token
        }

        return jwt.encode(payload, self._secret_key, algorithm=self._algorithm)

    def verify_token(self, token: str) -> Optional[TokenData]:
        """
        Verify and decode a JWT access token.

        This method:
        1. Verifies the signature using the secret key
        2. Checks if the token has expired
        3. Validates the token type is "access"
        4. Extracts user information

        Args:
            token: Encoded JWT string

        Returns:
            TokenData if valid, None if invalid/expired/wrong type

        Example:
            >>> service = JWTTokenService(secret_key="x" * 32, token_repository=repo)
            >>> token = service.generate_access_token(123, "user@example.com")
            >>> token_data = service.verify_token(token)
            >>> print(token_data.user_id)
            123
        """
        try:
            # Decode and verify token
            payload = jwt.decode(
                token,
                self._secret_key,
                algorithms=[self._algorithm],
            )

            # Verify token type
            if payload.get("type") != "access":
                return None

            # Extract data
            user_id = int(payload.get("sub"))
            email = payload.get("email")
            iat = datetime.fromtimestamp(payload.get("iat"), tz=timezone.utc)
            exp = datetime.fromtimestamp(payload.get("exp"), tz=timezone.utc)
            token_id = payload.get("jti")

            return TokenData(
                user_id=user_id,
                email=email,
                issued_at=iat,
                expires_at=exp,
                token_id=token_id,
            )

        except (InvalidTokenError, ExpiredSignatureError, ValueError, KeyError):
            # Token is invalid, expired, or malformed
            return None

    def verify_refresh_token(self, token: str) -> Optional[TokenData]:
        """
        Verify and decode a JWT refresh token.

        Similar to verify_token but checks for "refresh" type.
        Does NOT check revocation - that's handled by auth_service
        for proper reuse detection.

        Args:
            token: Encoded JWT refresh token

        Returns:
            TokenData if valid JWT, None if invalid/expired/wrong type
            Note: Returns TokenData even if token is revoked (checked separately)
        """
        try:
            payload = jwt.decode(
                token,
                self._secret_key,
                algorithms=[self._algorithm],
            )

            # Verify token type
            if payload.get("type") != "refresh":
                return None

            user_id = int(payload.get("sub"))
            email = payload.get("email")
            iat = datetime.fromtimestamp(payload.get("iat"), tz=timezone.utc)
            exp = datetime.fromtimestamp(payload.get("exp"), tz=timezone.utc)
            token_id = payload.get("jti")
            family_id = payload.get("fid")
            parent_token_id = payload.get("pid")  # Parent token ID
            rotation_sequence = payload.get("seq", 0)  # Rotation sequence (default 0)

            # Return token data regardless of revocation status
            # Revocation is checked in auth_service for proper reuse detection
            return TokenData(
                user_id=user_id,
                email=email,
                issued_at=iat,
                expires_at=exp,
                token_id=token_id,
                family_id=family_id,
                parent_token_id=parent_token_id,
                rotation_sequence=rotation_sequence,
            )

        except (InvalidTokenError, ExpiredSignatureError, ValueError, KeyError):
            return None

    async def store_refresh_token_metadata(self, token_data: TokenData) -> None:
        """
        Store refresh token metadata for tracking.

        Should be called after generating a refresh token.

        Args:
            token_data: Token data to store
        """
        if token_data.token_id:
            metadata = TokenMetadata(
                token_id=token_data.token_id,
                user_id=token_data.user_id,
                token_type="refresh",
                issued_at=token_data.issued_at,
                expires_at=token_data.expires_at,
                family_id=token_data.family_id,
                parent_token_id=token_data.parent_token_id,
                rotation_sequence=token_data.rotation_sequence,
            )
            await self._token_repository.store_token(metadata)

    async def revoke_refresh_token(self, token_id: str) -> None:
        """
        Revoke a specific refresh token.

        Args:
            token_id: Token identifier to revoke
        """
        await self._token_repository.revoke_token(token_id)

    async def revoke_token_family(self, family_id: str) -> None:
        """
        Revoke all tokens in a family.

        Called when token reuse is detected.

        Args:
            family_id: Family identifier
        """
        await self._token_repository.revoke_token_family(family_id)
