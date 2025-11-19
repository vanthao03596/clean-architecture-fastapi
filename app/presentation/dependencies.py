"""FastAPI dependency injection setup.

This module is the COMPOSITION ROOT - where we wire up dependencies.

In Clean Architecture, the composition root:
1. Lives in the outermost layer (presentation/infrastructure)
2. Creates concrete implementations
3. Injects them into abstractions
4. Never imported by inner layers

This is where we decide:
- Use Argon2PasswordHasher (not bcrypt or scrypt)
- Use UnitOfWork with SQLAlchemy (not MongoDB or Redis)
- Use Settings from environment (not hardcoded config)

All these decisions are isolated here. The application layer doesn't know
or care about these choices - it only knows about interfaces.
"""

from typing import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncEngine

from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.domain.repositories.unit_of_work import IUnitOfWork
from app.domain.repositories.token_repository import ITokenRepository
from app.domain.services.password_hasher import IPasswordHasher
from app.domain.services.token_service import ITokenService
from app.infrastructure.repositories.unit_of_work_impl import UnitOfWork
from app.infrastructure.repositories.token_repository_impl import InMemoryTokenRepository
from app.infrastructure.persistence.database import (
    create_database_engine,
    create_session_factory,
)
from app.infrastructure.security.argon2_password_hasher import Argon2PasswordHasher
from app.infrastructure.security.jwt_token_service import JWTTokenService
from app.infrastructure.config.settings import Settings, get_settings
from app.application.services.user_service import UserService
from app.application.services.auth_service import AuthService
from app.application.dtos.user_dto import UserDTO


# Module-level singletons (created once, reused throughout app lifecycle)
_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker | None = None
_token_repository: ITokenRepository | None = None


def get_database_engine(settings: Settings = Depends(get_settings)) -> AsyncEngine:
    """Get or create database engine singleton.

    The engine is created once and reused for the application lifecycle.

    Args:
        settings: Application settings (injected)

    Returns:
        AsyncEngine instance
    """
    global _engine
    if _engine is None:
        _engine = create_database_engine(settings)
    return _engine


def get_session_factory(
    engine: AsyncEngine = Depends(get_database_engine),
) -> async_sessionmaker:
    """Get or create session factory singleton.

    Args:
        engine: Database engine (injected)

    Returns:
        Session factory
    """
    global _session_factory
    if _session_factory is None:
        _session_factory = create_session_factory(engine)
    return _session_factory



async def get_uow(
    session_factory: async_sessionmaker = Depends(get_session_factory),
) -> AsyncGenerator[IUnitOfWork, None]:
    """
    Dependency that provides a Unit of Work instance.

    Now receives the session factory from get_session_factory,
    which gets its configuration from Settings.

    Dependency chain:
        get_settings() → get_database_engine() → get_session_factory() → get_uow()

    Usage:
        @app.get("/users/{user_id}")
        async def get_user(user_id: int, uow: IUnitOfWork = Depends(get_uow)):
            async with uow:
                user = await uow.users.get_by_id(user_id)
                ...

    Args:
        session_factory: Injected session factory

    Yields:
        IUnitOfWork instance
    """
    uow = UnitOfWork(session_factory)
    try:
        yield uow
    finally:
        # Cleanup if needed
        pass


def get_password_hasher() -> IPasswordHasher:
    """
    Dependency that provides password hasher.

    This is a SINGLETON - we create one instance and reuse it.
    Password hashers are stateless and thread-safe, so this is safe.

    Returns:
        IPasswordHasher implementation (Argon2PasswordHasher in production)

    Note:
        In tests, this dependency can be overridden with FakePasswordHasher:

        app.dependency_overrides[get_password_hasher] = lambda: FakePasswordHasher()
    """
    return Argon2PasswordHasher()


def get_token_repository() -> ITokenRepository:
    """
    Dependency that provides token repository.

    This is a SINGLETON - one instance shared across the application.
    For production with multiple servers, replace with RedisTokenRepository.

    Returns:
        ITokenRepository implementation (InMemoryTokenRepository for development)

    Note:
        In production, use Redis for distributed token storage:

        def get_token_repository():
            return RedisTokenRepository(redis_client=...)
    """
    global _token_repository
    if _token_repository is None:
        _token_repository = InMemoryTokenRepository()
    return _token_repository


def get_user_service(
    password_hasher: IPasswordHasher = Depends(get_password_hasher),
    session_factory: async_sessionmaker = Depends(get_session_factory),
) -> UserService:
    """
    Dependency that provides UserService.

    The service receives:
    1. A factory function that creates UoW instances (for transaction management)
    2. A password hasher (injected via dependency)

    Both dependencies now trace back to Settings through the dependency chain.

    Usage:
        @app.post("/users/")
        async def create_user(
            dto: CreateUserDTO,
            service: UserService = Depends(get_user_service)
        ):
            return await service.create_user(dto)

    Args:
        password_hasher: Injected password hasher (defaults to Argon2)
        session_factory: Injected session factory (from settings)

    Returns:
        UserService instance with all dependencies injected

    Dependency Graph:
        FastAPI endpoint
            → get_user_service()
                → get_password_hasher() → Argon2PasswordHasher
                → get_session_factory() → get_database_engine() → Settings
    """

    def uow_factory() -> IUnitOfWork:
        return UnitOfWork(session_factory)

    return UserService(uow_factory=uow_factory, password_hasher=password_hasher)


# Create security scheme for JWT Bearer tokens
# auto_error=False allows us to return 401 instead of 403 when credentials are missing
security = HTTPBearer(auto_error=False)


def get_token_service(
    settings: Settings = Depends(get_settings),
    token_repository: ITokenRepository = Depends(get_token_repository),
) -> ITokenService:
    """
    Dependency that provides token service.

    Returns a JWTTokenService configured with settings from environment
    and token repository for revocation tracking.

    Args:
        settings: Application settings (injected)
        token_repository: Token repository for tracking (injected)

    Returns:
        ITokenService implementation (JWTTokenService in production)
    """
    return JWTTokenService(
        secret_key=settings.secret_key,
        token_repository=token_repository,
        algorithm=settings.algorithm,
        access_token_expire_minutes=settings.access_token_expire_minutes,
        refresh_token_expire_days=settings.refresh_token_expire_days,
    )


def get_auth_service(
    password_hasher: IPasswordHasher = Depends(get_password_hasher),
    token_service: ITokenService = Depends(get_token_service),
    token_repository: ITokenRepository = Depends(get_token_repository),
    session_factory: async_sessionmaker = Depends(get_session_factory),
    settings: Settings = Depends(get_settings),
) -> AuthService:
    """
    Dependency that provides AuthService.

    The service receives:
    1. UoW factory for database access
    2. Token service for JWT operations
    3. Token repository for revocation tracking
    4. Password hasher for credential validation
    5. Settings for token expiration times and overlap period

    Returns:
        AuthService instance with all dependencies injected
    """
    def uow_factory() -> IUnitOfWork:
        return UnitOfWork(session_factory)

    return AuthService(
        uow_factory=uow_factory,
        token_service=token_service,
        token_repository=token_repository,
        password_hasher=password_hasher,
        access_token_expire_minutes=settings.access_token_expire_minutes,
        refresh_token_expire_days=settings.refresh_token_expire_days,
        refresh_token_overlap_seconds=settings.refresh_token_overlap_seconds,
    )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    auth_service: AuthService = Depends(get_auth_service),
) -> UserDTO:
    """
    Dependency that extracts and validates the current user from JWT.

    This dependency:
    1. Extracts the Bearer token from Authorization header
    2. Validates the token using AuthService
    3. Returns the authenticated user
    4. Raises exceptions if token is invalid (converted to 401 by exception handler)

    Usage in endpoints:
        @router.get("/me")
        async def get_me(current_user: UserDTO = Depends(get_current_user)):
            return current_user

    Args:
        credentials: HTTP Bearer credentials from Authorization header (None if missing)
        auth_service: Injected AuthService

    Returns:
        UserDTO of authenticated user

    Raises:
        InvalidTokenError: If token is invalid/expired (caught by exception handler)
    """
    from app.application.exceptions.exceptions import InvalidTokenError

    if credentials is None:
        raise InvalidTokenError("Missing authorization credentials")

    return await auth_service.get_current_user(credentials.credentials)
