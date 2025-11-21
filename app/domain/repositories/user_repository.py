"""User repository interface."""

from abc import abstractmethod

from app.domain.entities.user import User
from app.domain.repositories.base import IRepository


class IUserRepository(IRepository[User]):
    """
    User-specific repository interface.

    Extends base repository with user-specific query methods.
    This interface defines business-driven queries like "find by email"
    which are domain concerns, not infrastructure details.
    """

    @abstractmethod
    async def get_by_email(self, email: str) -> User | None:
        """
        Find a user by their email address.

        Args:
            email: The user's email

        Returns:
            User if found, None otherwise
        """
        pass

    @abstractmethod
    async def email_exists(self, email: str) -> bool:
        """
        Check if an email is already registered.

        Args:
            email: The email to check

        Returns:
            True if email exists, False otherwise
        """
        pass
