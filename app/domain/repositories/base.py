"""Base repository interfaces following Clean Architecture."""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Optional, List

# Generic type for domain entities
T = TypeVar("T")


class IRepository(ABC, Generic[T]):
    """
    Base repository interface defining standard CRUD operations.

    This interface belongs to the DOMAIN layer and defines the contract
    for data access without any implementation details.

    Type Parameters:
        T: The domain entity type this repository manages
    """

    @abstractmethod
    async def get_by_id(self, id: int) -> Optional[T]:
        """
        Retrieve an entity by its ID.

        Args:
            id: The unique identifier

        Returns:
            The entity if found, None otherwise
        """
        pass

    @abstractmethod
    async def get_all(self, skip: int = 0, limit: int = 100) -> List[T]:
        """
        Retrieve all entities with pagination.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of entities
        """
        pass

    @abstractmethod
    async def add(self, entity: T) -> T:
        """
        Add a new entity.

        Args:
            entity: The entity to add

        Returns:
            The added entity with generated fields (like ID)
        """
        pass

    @abstractmethod
    async def update(self, entity: T) -> T:
        """
        Update an existing entity.

        Args:
            entity: The entity to update

        Returns:
            The updated entity
        """
        pass

    @abstractmethod
    async def delete(self, id: int) -> bool:
        """
        Delete an entity by ID.

        Args:
            id: The unique identifier

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    async def exists(self, id: int) -> bool:
        """
        Check if an entity exists.

        Args:
            id: The unique identifier

        Returns:
            True if exists, False otherwise
        """
        pass
