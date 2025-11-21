"""Unit of Work implementation using SQLAlchemy."""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.repositories.unit_of_work import IUnitOfWork
from app.infrastructure.repositories.user_repository_impl import UserRepository


class UnitOfWork(IUnitOfWork):
    """
    SQLAlchemy implementation of Unit of Work.

    This class:
    1. Manages the SQLAlchemy async session lifecycle
    2. Provides access to all repositories within a transaction
    3. Ensures all repositories share the same session
    4. Commits or rolls back based on operation success
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        """
        Initialize UoW with a session factory.

        Args:
            session_factory: SQLAlchemy async session factory
        """
        self._session_factory = session_factory
        self._session: AsyncSession | None = None

    async def __aenter__(self) -> "UnitOfWork":
        """
        Start a new database session and initialize repositories.

        Returns:
            Self for context manager usage
        """
        # Create new session
        self._session = self._session_factory()

        # Initialize all repositories with the same session
        # This ensures they all participate in the same transaction
        self.users = UserRepository(self._session)
        # Add other repositories here:
        # self.products = ProductRepository(self._session)
        # self.orders = OrderRepository(self._session)

        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """
        Exit context manager, committing or rolling back.

        If an exception occurred (exc_type is not None), rollback.
        Otherwise, commit.
        """
        if exc_type is not None:
            # Exception occurred, rollback
            await self.rollback()

        # Always close the session
        if self._session is not None:
            await self._session.close()
            self._session = None

    async def commit(self) -> None:
        """Commit the current transaction."""
        if self._session is None:
            raise RuntimeError("Cannot commit: no active session")

        await self._session.commit()

    async def rollback(self) -> None:
        """Rollback the current transaction."""
        if self._session is None:
            raise RuntimeError("Cannot rollback: no active session")

        await self._session.rollback()
