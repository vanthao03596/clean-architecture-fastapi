"""Fake Unit of Work for testing without a database.

This fake UoW provides the same interface as the real one but uses
fake repositories that store data in memory.
"""

from typing import List, Optional, cast

from app.domain.repositories.unit_of_work import IUnitOfWork
from app.domain.entities.user import User
from tests.fakes.user_repository_fake import FakeUserRepository


class FakeUnitOfWork(IUnitOfWork):
    """
    In-memory fake implementation of IUnitOfWork.

    Used for testing services in isolation without a database.
    All repositories share the same in-memory storage, so changes
    are visible across repositories within the same UoW instance.

    Usage:
        async with FakeUnitOfWork() as uow:
            user = User(email="test@example.com", ...)
            await uow.users.add(user)
            await uow.commit()
    """

    def __init__(self, initial_users: Optional[List[User]] = None):
        """
        Initialize with fake repositories.

        Args:
            initial_users: Optional list of users to pre-populate the repository
        """
        self.users = FakeUserRepository(initial_data=initial_users)
        # Add other repositories here:
        # self.products = FakeProductRepository()
        # self.orders = FakeOrderRepository()

        self.committed = False
        self.rolled_back = False
        self._is_active = False

    async def __aenter__(self) -> "FakeUnitOfWork":
        """Enter context."""
        self._is_active = True
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context, auto-commit if no exception."""
        if exc_type is None and not self.rolled_back:
            await self.commit()
        elif exc_type is not None:
            await self.rollback()

        self._is_active = False

    async def commit(self) -> None:
        """
        Mark as committed.

        In a fake implementation, data is already persisted to memory,
        so we just track that commit was called.
        """
        if not self._is_active:
            raise RuntimeError("Cannot commit: UoW is not active")

        self.committed = True
        self.rolled_back = False

    async def rollback(self) -> None:
        """
        Mark as rolled back.

        In a real implementation, this would undo changes.
        For testing, we just track that rollback was called.

        Note: The fake repositories don't actually rollback changes
        since they commit immediately. For more advanced testing,
        you could implement a transaction-like mechanism.
        """
        if not self._is_active:
            raise RuntimeError("Cannot rollback: UoW is not active")

        self.rolled_back = True
        self.committed = False

    # Helper methods for testing

    def clear_all(self) -> None:
        """Clear all repository data (useful for test teardown)."""
        # Cast to concrete type to access test helper methods
        cast(FakeUserRepository, self.users).clear()
        # Clear other repositories when added:
        # cast(FakeProductRepository, self.products).clear()
        # cast(FakeOrderRepository, self.orders).clear()

        self.committed = False
        self.rolled_back = False

    def was_committed(self) -> bool:
        """Check if commit was called (useful for assertions)."""
        return self.committed

    def was_rolled_back(self) -> bool:
        """Check if rollback was called (useful for assertions)."""
        return self.rolled_back
