"""User repository implementation using SQLAlchemy."""

from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.user import User
from app.domain.repositories.user_repository import IUserRepository
from app.infrastructure.persistence.models.user_model import UserModel


class UserRepository(IUserRepository):
    """
    SQLAlchemy implementation of IUserRepository.

    This class contains all database-specific code and depends on:
    - SQLAlchemy (infrastructure)
    - UserModel (infrastructure ORM mapping)

    It implements the IUserRepository interface (domain) and returns
    domain entities, never exposing ORM models to the application layer.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize repository with a database session.

        Args:
            session: SQLAlchemy async session (managed by UoW)
        """
        self._session = session

    async def get_by_id(self, id: int) -> Optional[User]:
        """Get user by ID."""
        result = await self._session.execute(
            select(UserModel).where(UserModel.id == id)
        )
        user_model = result.scalar_one_or_none()

        if user_model is None:
            return None

        return user_model.to_entity()

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[User]:
        """Get all users with pagination."""
        result = await self._session.execute(
            select(UserModel).offset(skip).limit(limit)
        )
        user_models = result.scalars().all()

        return [model.to_entity() for model in user_models]

    async def add(self, entity: User) -> User:
        """
        Add a new user.

        Note: We convert domain entity -> ORM model, persist it,
        then convert back to domain entity.
        """
        user_model = UserModel.from_entity(entity)

        self._session.add(user_model)
        await self._session.flush()  # Get generated ID without committing
        await self._session.refresh(user_model)  # Refresh timestamps

        return user_model.to_entity()

    async def update(self, entity: User) -> User:
        """Update existing user."""
        if entity.id is None:
            raise ValueError("Cannot update user without ID")

        # Get existing model
        result = await self._session.execute(
            select(UserModel).where(UserModel.id == entity.id)
        )
        user_model = result.scalar_one_or_none()

        if user_model is None:
            raise ValueError(f"User with ID {entity.id} not found")

        # Update fields
        user_model.email = entity.email
        user_model.name = entity.name
        user_model.password_hash = entity.password_hash

        await self._session.flush()
        await self._session.refresh(user_model)

        return user_model.to_entity()

    async def delete(self, id: int) -> bool:
        """Delete user by ID."""
        result = await self._session.execute(
            select(UserModel).where(UserModel.id == id)
        )
        user_model = result.scalar_one_or_none()

        if user_model is None:
            return False

        await self._session.delete(user_model)
        await self._session.flush()

        return True

    async def exists(self, id: int) -> bool:
        """Check if user exists."""
        result = await self._session.execute(
            select(UserModel.id).where(UserModel.id == id)
        )
        return result.scalar_one_or_none() is not None

    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email address."""
        result = await self._session.execute(
            select(UserModel).where(UserModel.email == email)
        )
        user_model = result.scalar_one_or_none()

        if user_model is None:
            return None

        return user_model.to_entity()

    async def email_exists(self, email: str) -> bool:
        """Check if email is already registered."""
        result = await self._session.execute(
            select(UserModel.id).where(UserModel.email == email)
        )
        return result.scalar_one_or_none() is not None
