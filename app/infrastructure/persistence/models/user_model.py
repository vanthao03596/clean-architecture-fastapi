"""User ORM model - infrastructure layer SQLAlchemy mapping."""

from datetime import datetime

from sqlalchemy import String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.entities.user import User
from app.infrastructure.persistence.database import Base


class UserModel(Base):
    """
    SQLAlchemy ORM model for users table.

    This is an INFRASTRUCTURE detail that maps domain entities to database rows.
    The domain layer never imports this class.
    """

    __tablename__ = "users"

    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # User information
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Authentication
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        insert_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        insert_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        """String representation of UserModel."""
        return f"UserModel(id={self.id!r}, email={self.email!r}, name={self.name!r})"

    def to_entity(self) -> User:
        """
        Convert ORM model to domain entity.

        This mapper method handles the translation between infrastructure
        and domain layers.

        Returns:
            User domain entity
        """
        return User(
            id=self.id,
            email=self.email,
            name=self.name,
            password_hash=self.password_hash,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @staticmethod
    def from_entity(user: User) -> "UserModel":
        """
        Create ORM model from domain entity.

        Args:
            user: Domain entity

        Returns:
            ORM model ready for persistence
        """
        model = UserModel(
            email=user.email,
            name=user.name,
            password_hash=user.password_hash,
        )

        # Set ID if it exists (for updates)
        if user.id is not None:
            model.id = user.id

        # Set timestamps if they exist
        if user.created_at is not None:
            model.created_at = user.created_at
        if user.updated_at is not None:
            model.updated_at = user.updated_at

        return model
