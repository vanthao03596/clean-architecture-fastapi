"""Authentication service - application layer business logic.

This service orchestrates authentication use cases:
1. User login (credential validation + token generation)
2. Token refresh (obtain new access token using refresh token)
3. Get current user (extract user from token)

DEPENDENCY INVERSION in action:
- AuthService depends on ITokenService (abstraction)
- AuthService depends on IPasswordHasher (abstraction)
- AuthService depends on IUnitOfWork (abstraction)
- No dependencies on PyJWT, Argon2, or SQLAlchemy
"""

import logging
from collections.abc import Callable
from datetime import UTC, datetime

from app.application.dtos.auth_dto import LoginDTO, RefreshTokenDTO, TokenDTO
from app.application.dtos.user_dto import UserDTO
from app.application.exceptions.exceptions import (
    InvalidCredentialsError,
    InvalidTokenError,
    UserNotFoundError,
)
from app.domain.repositories.token_repository import ITokenRepository, TokenMetadata
from app.domain.repositories.unit_of_work import IUnitOfWork
from app.domain.services.password_hasher import IPasswordHasher
from app.domain.services.token_service import ITokenService, TokenData

logger = logging.getLogger(__name__)


class AuthService:
    """
    Authentication service encapsulating auth-related use cases.

    This service:
    1. Depends on abstractions (ITokenService, IPasswordHasher, IUnitOfWork)
    2. Contains authentication business logic
    3. Returns DTOs to the presentation layer
    4. Raises application exceptions (converted to HTTP by presentation)

    Testing:
    - Unit tests use FakeTokenService, FakePasswordHasher, FakeUnitOfWork
    - No PyJWT or database required in unit tests
    """

    def __init__(
        self,
        uow_factory: Callable[[], IUnitOfWork],
        token_service: ITokenService,
        token_repository: ITokenRepository,
        password_hasher: IPasswordHasher,
        access_token_expire_minutes: int = 30,
        refresh_token_expire_days: int = 7,
        refresh_token_overlap_seconds: int = 5,
    ):
        """
        Initialize auth service with dependencies.

        Args:
            uow_factory: Factory function that returns IUnitOfWork instances
            token_service: Token generation/validation service (abstraction)
            token_repository: Token repository for revocation tracking
            password_hasher: Password hashing service (abstraction)
            access_token_expire_minutes: Access token lifetime (for response)
            refresh_token_expire_days: Refresh token lifetime in days
            refresh_token_overlap_seconds: Overlap period for token rotation (Auth0-style)
        """
        self._uow_factory = uow_factory
        self._token_service = token_service
        self._token_repository = token_repository
        self._password_hasher = password_hasher
        self._access_token_expire_minutes = access_token_expire_minutes
        self._refresh_token_expire_days = refresh_token_expire_days
        self._refresh_token_overlap_seconds = refresh_token_overlap_seconds

    async def login(self, dto: LoginDTO) -> TokenDTO:
        """
        Authenticate user and generate tokens.

        Business logic:
        1. Validate credentials (email + password)
        2. If valid, generate access and refresh tokens
        3. Return both tokens with expiration info

        Args:
            dto: Login credentials (email + password)

        Returns:
            TokenDTO with access_token and refresh_token

        Raises:
            InvalidCredentialsError: If email or password is incorrect

        Example:
            token_dto = await auth_service.login(
                LoginDTO(email="user@example.com", password="secret")
            )
            # Use token_dto.access_token for API requests
        """
        async with self._uow_factory() as uow:
            # Get user by email
            user = await uow.users.get_by_email(dto.email)

            if user is None:
                # Don't reveal whether email exists (security)
                raise InvalidCredentialsError()

            # Verify password
            if not self._password_hasher.verify(dto.password, user.password_hash):
                raise InvalidCredentialsError()

            # Generate tokens
            # user.id is guaranteed non-None since we fetched from DB
            assert user.id is not None
            access_token = self._token_service.generate_access_token(
                user_id=user.id,
                email=user.email,
            )

            # Generate refresh token (creates new family)
            refresh_token = self._token_service.generate_refresh_token(
                user_id=user.id,
                email=user.email,
            )

            # Decode to get metadata and store it
            refresh_token_data = self._token_service.verify_refresh_token(refresh_token)
            if refresh_token_data:
                await self._store_refresh_token(refresh_token_data)

            return TokenDTO(
                access_token=access_token,
                refresh_token=refresh_token,
                token_type="bearer",
                expires_in=self._access_token_expire_minutes * 60,  # Convert to seconds
            )

    async def refresh_token(self, dto: RefreshTokenDTO) -> TokenDTO:
        """
        Generate new access token using refresh token with rotation and overlap period.

        Implements OAuth 2.1 refresh token rotation with Auth0-style overlap period:
        1. Validate refresh token JWT
        2. Check if token has been used before:
           a. First use → Mark as used, issue new tokens
           b. Reuse within overlap period (previous token) → Issue new tokens (safe)
           c. Reuse outside overlap period → BREACH → Revoke family
           d. Older token reused → BREACH → Revoke family
        3. New refresh token inherits family_id for tracking

        Args:
            dto: Refresh token request

        Returns:
            New TokenDTO with fresh access and refresh tokens

        Raises:
            InvalidTokenError: If refresh token is invalid/expired/reused
            UserNotFoundError: If user no longer exists
        """
        # Verify refresh token JWT signature and expiration
        token_data = self._token_service.verify_refresh_token(dto.refresh_token)

        if token_data is None or token_data.is_expired:
            raise InvalidTokenError("Invalid or expired refresh token")

        # Get token metadata for overlap period logic
        if not token_data.token_id:
            raise InvalidTokenError("Token missing identifier")

        metadata = await self._token_repository.get_token_metadata(token_data.token_id)

        # Handle token that's not in repository (e.g., very old or cleaned up)
        if metadata is None:
            logger.warning(
                f"Refresh token {token_data.token_id} not found in repository. "
                "Token may be expired or cleaned up."
            )
            raise InvalidTokenError("Token not found or has been revoked")

        # Check if token has been revoked (family-wide revocation)
        if metadata.is_revoked:
            logger.warning(
                f"Revoked refresh token used for user {token_data.user_id}. "
                f"Family {token_data.family_id} was previously revoked."
            )
            raise InvalidTokenError("Token has been revoked")

        # === OVERLAP PERIOD LOGIC ===
        now = datetime.now(UTC)

        # Check if this token has been used before
        if metadata.used_at is not None:
            # Token has been used before - check overlap period conditions
            time_since_use = (now - metadata.used_at).total_seconds()

            # Check if within overlap window
            within_overlap = time_since_use <= self._refresh_token_overlap_seconds

            if within_overlap:
                # WITHIN OVERLAP PERIOD: Check if this is the IMMEDIATE previous token
                # Only the previous token can be reused; older tokens trigger breach
                if token_data.family_id:
                    latest_token = (
                        await self._token_repository.get_latest_token_in_family(
                            token_data.family_id
                        )
                    )

                    # Check if current token is the parent of the latest token
                    # (i.e., this is the immediate previous token)
                    if (
                        latest_token
                        and latest_token.parent_token_id == token_data.token_id
                    ):
                        # This IS the immediate previous token - allow reuse
                        logger.info(
                            f"Previous token {token_data.token_id} (seq={token_data.rotation_sequence}) "
                            f"reused within overlap period ({time_since_use:.2f}s < {self._refresh_token_overlap_seconds}s). "
                            f"Latest token: {latest_token.token_id} (seq={latest_token.rotation_sequence}). "
                            f"Allowing reuse for user {token_data.user_id}."
                        )
                        # Continue to issue new tokens
                    else:
                        # This is an OLDER token (2nd-to-last or earlier) - BREACH!
                        logger.warning(
                            f"BREACH DETECTED! Old token {token_data.token_id} (seq={token_data.rotation_sequence}) "
                            f"reused within overlap period. This is NOT the immediate previous token. "
                            f"Latest token: {latest_token.token_id if latest_token else 'N/A'} "
                            f"(seq={latest_token.rotation_sequence if latest_token else 'N/A'}). "
                            f"Revoking family {token_data.family_id} for user {token_data.user_id}."
                        )
                        await self._token_repository.revoke_token_family(
                            token_data.family_id
                        )
                        raise InvalidTokenError(
                            "Old token reuse detected. All tokens in family have been revoked."
                        )
                else:
                    # No family_id - shouldn't happen, but handle gracefully
                    logger.warning(
                        f"Token {token_data.token_id} has no family_id. Allowing reuse within overlap."
                    )
            else:
                # OUTSIDE OVERLAP PERIOD: Reject ALL token reuse
                # This is Auth0-compliant behavior - hard cutoff at overlap period
                logger.warning(
                    f"BREACH DETECTED! Token {token_data.token_id} reused outside overlap period "
                    f"({time_since_use:.2f}s > {self._refresh_token_overlap_seconds}s). "
                    f"Revoking family {token_data.family_id} for user {token_data.user_id}."
                )
                if token_data.family_id:
                    await self._token_repository.revoke_token_family(
                        token_data.family_id
                    )
                raise InvalidTokenError(
                    "Token reuse detected. All tokens in family have been revoked."
                )
        else:
            # First use of this token - mark it as used
            await self._token_repository.mark_token_used(token_data.token_id, now)
            logger.debug(
                f"Token {token_data.token_id} used for first time by user {token_data.user_id}"
            )

        # === TOKEN ROTATION ===
        async with self._uow_factory() as uow:
            # Verify user still exists
            user = await uow.users.get_by_id(token_data.user_id)

            if user is None:
                raise UserNotFoundError(f"User {token_data.user_id} not found")

            # Generate new access token
            assert user.id is not None
            access_token = self._token_service.generate_access_token(
                user_id=user.id,
                email=user.email,
            )

            # Generate new refresh token with incremented sequence
            new_refresh_token = self._token_service.generate_refresh_token(
                user_id=user.id,
                email=user.email,
                family_id=token_data.family_id,  # Inherit family
                parent_token_id=token_data.token_id,  # Track parent
                rotation_sequence=token_data.rotation_sequence
                + 1,  # Increment sequence
            )

            # Store new refresh token metadata
            new_token_data = self._token_service.verify_refresh_token(new_refresh_token)
            if new_token_data:
                await self._store_refresh_token(new_token_data)

            logger.info(
                f"Token rotation successful for user {user.id}. "
                f"Old token: {token_data.token_id} (seq={token_data.rotation_sequence}), "
                f"New token: {new_token_data.token_id if new_token_data else 'N/A'} "
                f"(seq={token_data.rotation_sequence + 1})"
            )

            return TokenDTO(
                access_token=access_token,
                refresh_token=new_refresh_token,
                token_type="bearer",
                expires_in=self._access_token_expire_minutes * 60,
            )

    async def get_current_user(self, access_token: str) -> UserDTO:
        """
        Get the currently authenticated user from access token.

        This is used by the FastAPI dependency to extract the current
        user from the Authorization header.

        Args:
            access_token: JWT access token

        Returns:
            UserDTO of authenticated user

        Raises:
            InvalidTokenError: If token is invalid/expired
            UserNotFoundError: If user no longer exists
        """
        # Verify access token
        token_data = self._token_service.verify_token(access_token)

        if token_data is None or token_data.is_expired:
            raise InvalidTokenError("Invalid or expired access token")

        async with self._uow_factory() as uow:
            # Get user from database
            user = await uow.users.get_by_id(token_data.user_id)

            if user is None:
                raise UserNotFoundError(f"User {token_data.user_id} not found")

            return UserDTO.from_entity(user)

    async def _store_refresh_token(self, token_data: TokenData) -> None:
        """
        Store refresh token metadata for tracking.

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
