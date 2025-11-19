"""Unit of Work interface - domain layer."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.domain.repositories.user_repository import IUserRepository


class IUnitOfWork(ABC):
    """
    Unit of Work interface for managing transactions.

    This interface belongs to the DOMAIN layer because it defines
    the contract for transactional operations that the application
    layer needs, without specifying implementation details.

    The UoW acts as a facade providing access to all repositories
    within a single transactional boundary.
    """

    # Repository properties - application layer accesses via these
    users: "IUserRepository"
    # Add other repositories here as you create them:
    # products: IProductRepository
    # orders: IOrderRepository

    @abstractmethod
    async def __aenter__(self) -> "IUnitOfWork":
        """
        Enter async context manager.

        This is where the implementation would start a database
        transaction/session.
        """
        pass

    @abstractmethod
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Exit async context manager.

        If exc_type is None (no exception), commit the transaction.
        Otherwise, rollback.
        """
        pass

    @abstractmethod
    async def commit(self) -> None:
        """
        Explicitly commit the current transaction.

        Normally called by __aexit__, but can be called explicitly
        for fine-grained control.
        """
        pass

    @abstractmethod
    async def rollback(self) -> None:
        """
        Explicitly rollback the current transaction.

        Used when you need to abort without raising an exception.
        """
        pass
