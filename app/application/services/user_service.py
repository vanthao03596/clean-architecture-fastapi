"""User service - application layer business logic."""

from collections.abc import Callable

from app.application.dtos.user_dto import CreateUserDTO, UpdateUserDTO, UserDTO
from app.application.exceptions import (
    UserAlreadyExistsError,
    UserNotFoundError,
)
from app.domain.entities.user import User
from app.domain.repositories.unit_of_work import IUnitOfWork
from app.domain.services.password_hasher import IPasswordHasher


class UserService:
    """
    User service encapsulating user-related use cases.

    This service:
    1. Depends on IUnitOfWork abstraction (not concrete implementation)
    2. Depends on IPasswordHasher abstraction (not concrete implementation)
    3. Contains business logic and orchestration
    4. Uses domain entities internally
    5. Returns DTOs to the presentation layer

    Dependency Inversion Principle:
    - UserService (high-level) depends on IPasswordHasher (abstraction)
    - Argon2PasswordHasher (low-level) implements IPasswordHasher
    - Dependencies point INWARD toward the domain layer
    """

    def __init__(
        self,
        uow_factory: Callable[[], IUnitOfWork],
        password_hasher: IPasswordHasher,
    ):
        """
        Initialize service with dependencies.

        Args:
            uow_factory: Factory function that returns IUnitOfWork instances
            password_hasher: Password hashing service (abstraction, not concrete class)

        Example:
            # Production
            service = UserService(
                uow_factory=lambda: UnitOfWork(session),
                password_hasher=Argon2PasswordHasher()
            )

            # Testing
            service = UserService(
                uow_factory=lambda: FakeUnitOfWork(),
                password_hasher=FakePasswordHasher()
            )
        """
        self._uow_factory = uow_factory
        self._password_hasher = password_hasher

    async def create_user(self, dto: CreateUserDTO) -> UserDTO:
        """
        Create a new user.

        Business rules:
        1. Email must be unique
        2. Password must be hashed before storage

        Args:
            dto: User creation data

        Returns:
            Created user DTO

        Raises:
            UserAlreadyExistsError: If email already exists
        """
        async with self._uow_factory() as uow:
            # Check if email already exists
            if await uow.users.email_exists(dto.email):
                raise UserAlreadyExistsError(f"Email {dto.email} already registered")

            # Create domain entity with hashed password
            user = User(
                email=dto.email,
                name=dto.name,
                password_hash=self._password_hasher.hash(dto.password),
            )

            # Persist via repository
            created_user = await uow.users.add(user)

            # Commit transaction
            await uow.commit()

            # Return DTO
            return UserDTO.from_entity(created_user)

    async def get_user_by_id(self, user_id: int) -> UserDTO:
        """
        Retrieve user by ID.

        Args:
            user_id: User ID

        Returns:
            User DTO

        Raises:
            UserNotFoundError: If user doesn't exist
        """
        async with self._uow_factory() as uow:
            user = await uow.users.get_by_id(user_id)

            if user is None:
                raise UserNotFoundError(f"User with ID {user_id} not found")

            return UserDTO.from_entity(user)

    async def get_user_by_email(self, email: str) -> UserDTO | None:
        """
        Get user by email.

        Args:
            email: User email

        Returns:
            User DTO if found, None otherwise
        """
        async with self._uow_factory() as uow:
            user = await uow.users.get_by_email(email)

            if user is None:
                return None

            return UserDTO.from_entity(user)

    async def get_all_users(self, skip: int = 0, limit: int = 100) -> list[UserDTO]:
        """
        Get all users with pagination.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of user DTOs
        """
        async with self._uow_factory() as uow:
            users = await uow.users.get_all(skip=skip, limit=limit)
            return [UserDTO.from_entity(user) for user in users]

    async def update_user(self, user_id: int, dto: UpdateUserDTO) -> UserDTO:
        """
        Update user information.

        Args:
            user_id: User ID to update
            dto: Update data

        Returns:
            Updated user DTO

        Raises:
            UserNotFoundError: If user doesn't exist
            UserAlreadyExistsError: If email is taken by another user
        """
        async with self._uow_factory() as uow:
            # Get existing user
            user = await uow.users.get_by_id(user_id)
            if user is None:
                raise UserNotFoundError(f"User with ID {user_id} not found")

            # Check email uniqueness if changing
            if dto.email and dto.email != user.email:
                existing = await uow.users.get_by_email(dto.email)
                if existing is not None:
                    raise UserAlreadyExistsError(f"Email {dto.email} already in use")

            # Update entity using domain methods
            if dto.name:
                user.change_name(dto.name)

            if dto.email:
                user.change_email(dto.email)

            # Persist changes
            updated_user = await uow.users.update(user)

            # Commit
            await uow.commit()

            return UserDTO.from_entity(updated_user)

    async def delete_user(self, user_id: int) -> None:
        """
        Delete a user.

        Args:
            user_id: User ID to delete

        Raises:
            UserNotFoundError: If user doesn't exist
        """
        async with self._uow_factory() as uow:
            deleted = await uow.users.delete(user_id)

            if not deleted:
                raise UserNotFoundError(f"User with ID {user_id} not found")

            await uow.commit()

    async def verify_password(self, email: str, password: str) -> bool:
        """
        Verify a user's password.

        This method is useful for authentication flows where you need to
        check if a provided password is correct.

        Args:
            email: User's email
            password: Plain text password to verify

        Returns:
            True if password is correct, False otherwise

        Example:
            is_valid = await user_service.verify_password(
                email="user@example.com",
                password="their_password"
            )
            if is_valid:
                # Grant access
            else:
                # Deny access
        """
        async with self._uow_factory() as uow:
            user = await uow.users.get_by_email(email)

            if user is None:
                # User doesn't exist - return False (don't reveal this info)
                # For security, we don't distinguish between "user not found"
                # and "wrong password" in the return value
                return False

            # Verify password using the password hasher
            return self._password_hasher.verify(password, user.password_hash)
