"""User DTOs for application layer using Pydantic."""

from datetime import datetime
from typing import Annotated, Optional
from pydantic import BaseModel, EmailStr, ConfigDict, Field, BeforeValidator

from app.domain.entities.user import User


def strip_whitespace(v: str | None) -> str | None:
    """Strip whitespace from string values."""
    return v.strip() if isinstance(v, str) else v


class CreateUserDTO(BaseModel):
    """
    DTO for creating a user.

    Validation:
    - email: Must be valid email format (EmailStr)
    - name: Cannot be empty, whitespace is automatically trimmed (min_length=1 after stripping)
    - password: Must be at least 8 characters (min_length=8)
    """

    email: EmailStr
    name: Annotated[str, BeforeValidator(strip_whitespace), Field(min_length=1)]
    password: Annotated[str, Field(min_length=8)]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "user@example.com",
                "name": "John Doe",
                "password": "securepassword123",
            }
        }
    )


class UpdateUserDTO(BaseModel):
    """
    DTO for updating a user.

    Validation:
    - email: Must be valid email format if provided (EmailStr)
    - name: Cannot be empty if provided, whitespace is automatically trimmed (min_length=1 after stripping)
    - None values are allowed for fields not being updated
    """

    email: Optional[EmailStr] = None
    name: Annotated[str, BeforeValidator(strip_whitespace), Field(min_length=1)] | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "newemail@example.com",
                "name": "Jane Doe",
            }
        }
    )


class UserDTO(BaseModel):
    """DTO for returning user data to presentation layer."""

    id: int
    email: str
    name: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_entity(cls, user: User) -> "UserDTO":
        """
        Convert a PERSISTED domain entity to DTO.

        PRECONDITION: The user entity MUST be persisted (have id, created_at, updated_at).
        This method should only be called on entities returned from repositories,
        never on newly created entities before persistence.

        Args:
            user: User domain entity (must be persisted)

        Returns:
            UserDTO instance

        Raises:
            ValueError: If the entity is not persisted (missing id, created_at, or updated_at)
        """
        # Validate precondition: entity must be persisted
        if user.id is None:
            raise ValueError(
                "Cannot create UserDTO from non-persisted entity: missing id. "
                "Ensure the entity has been saved via repository before converting to DTO."
            )

        if user.created_at is None:
            raise ValueError(
                "Cannot create UserDTO from non-persisted entity: missing created_at. "
                "Ensure the entity has been saved via repository before converting to DTO."
            )

        if user.updated_at is None:
            raise ValueError(
                "Cannot create UserDTO from non-persisted entity: missing updated_at. "
                "Ensure the entity has been saved via repository before converting to DTO."
            )

        # Type checker now knows these are not None
        return cls(
            id=user.id,
            email=user.email,
            name=user.name,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )
