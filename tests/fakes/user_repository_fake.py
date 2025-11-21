"""Fake user repository for testing without a database.

This fake repository stores data in memory and implements the same interface
as the real repository, allowing you to test services in isolation.
"""

from datetime import UTC, datetime

from app.domain.entities.user import User
from app.domain.repositories.user_repository import IUserRepository


class FakeUserRepository(IUserRepository):
    """
    In-memory fake implementation of IUserRepository.

    This is used for unit testing services without a real database.
    It implements the same interface as the real repository but stores
    data in memory using a dictionary.

    Usage:
        repo = FakeUserRepository()
        user = User(email="test@example.com", name="Test", password_hash="hash")
        created_user = await repo.add(user)
    """

    def __init__(self, initial_data: list[User] | None = None):
        """
        Initialize with empty in-memory storage.

        Args:
            initial_data: Optional list of users to pre-populate the repository
        """
        self._users: dict[int, User] = {}
        self._next_id = 1

        # Pre-populate if initial data provided
        if initial_data:
            for user in initial_data:
                if user.id is None:
                    user_with_id = User(
                        id=self._next_id,
                        email=user.email,
                        name=user.name,
                        password_hash=user.password_hash,
                        created_at=user.created_at or datetime.now(UTC),
                        updated_at=user.updated_at or datetime.now(UTC),
                    )
                    self._users[self._next_id] = user_with_id
                    self._next_id += 1
                else:
                    self._users[user.id] = user
                    self._next_id = max(self._next_id, user.id + 1)

    async def get_by_id(self, id: int) -> User | None:
        """Get user by ID from memory."""
        return self._users.get(id)

    async def get_all(self, skip: int = 0, limit: int = 100) -> list[User]:
        """Get all users from memory with pagination."""
        all_users = list(self._users.values())
        return all_users[skip : skip + limit]

    async def add(self, entity: User) -> User:
        """
        Add user to memory.

        Automatically generates ID and timestamps if not set.
        """
        # Generate ID if not set
        user_id = entity.id if entity.id is not None else self._next_id

        # Generate timestamps if not set
        now = datetime.now(UTC)
        created_at = entity.created_at or now
        updated_at = entity.updated_at or now

        # Create new user with ID and timestamps
        new_user = User(
            id=user_id,
            email=entity.email,
            name=entity.name,
            password_hash=entity.password_hash,
            created_at=created_at,
            updated_at=updated_at,
        )

        self._users[user_id] = new_user

        # Increment next ID if we used it
        if entity.id is None:
            self._next_id += 1

        return new_user

    async def update(self, entity: User) -> User:
        """Update user in memory."""
        if entity.id is None or entity.id not in self._users:
            raise ValueError(f"User with ID {entity.id} not found")

        # Update timestamp
        updated_user = User(
            id=entity.id,
            email=entity.email,
            name=entity.name,
            password_hash=entity.password_hash,
            created_at=entity.created_at,
            updated_at=datetime.now(UTC),
        )

        self._users[entity.id] = updated_user
        return updated_user

    async def delete(self, id: int) -> bool:
        """Delete user from memory."""
        if id in self._users:
            del self._users[id]
            return True
        return False

    async def exists(self, id: int) -> bool:
        """Check if user exists in memory."""
        return id in self._users

    async def get_by_email(self, email: str) -> User | None:
        """Find user by email in memory."""
        for user in self._users.values():
            if user.email == email:
                return user
        return None

    async def email_exists(self, email: str) -> bool:
        """Check if email exists in memory."""
        return any(user.email == email for user in self._users.values())

    # Helper methods for testing

    def clear(self) -> None:
        """Clear all data (useful for test teardown)."""
        self._users.clear()
        self._next_id = 1

    def count(self) -> int:
        """Get total number of users (useful for assertions)."""
        return len(self._users)

    def get_all_sync(self) -> list[User]:
        """Get all users synchronously (useful for quick checks in tests)."""
        return list(self._users.values())
