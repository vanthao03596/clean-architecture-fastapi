"""User domain entity - pure business logic, no infrastructure."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from app.domain.exceptions import InvalidEntityStateException, BusinessRuleViolationException


@dataclass
class User:
    """
    User domain entity representing the business concept of a user.

    This is a pure Python class with NO dependencies on SQLAlchemy,
    FastAPI, or any framework. It contains business rules and validations.
    """

    email: str
    name: str
    password_hash: str
    id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        """
        Validate entity invariants at construction time.

        These are structural validations - they ensure the entity can exist
        in a valid state. Violations indicate the entity cannot be created.
        """
        if not self.email or "@" not in self.email:
            raise InvalidEntityStateException(
                f"Invalid email address: '{self.email}'. Email must contain '@' symbol."
            )

        if not self.name or len(self.name.strip()) == 0:
            raise InvalidEntityStateException(
                "Name cannot be empty. User must have a valid name."
            )

        if not self.password_hash:
            raise InvalidEntityStateException(
                "Password hash is required. User cannot exist without authentication credentials."
            )

    def change_name(self, new_name: str) -> None:
        """
        Change user's name with validation.

        Business rule: Names must not be empty.

        Args:
            new_name: The new name to set

        Raises:
            BusinessRuleViolationException: If name is empty or invalid
        """
        if not new_name or len(new_name.strip()) == 0:
            raise BusinessRuleViolationException(
                "Cannot change name to empty value. Names must contain at least one character."
            )

        object.__setattr__(self, "name", new_name)
        object.__setattr__(self, "updated_at", datetime.now(timezone.utc))

    def change_email(self, new_email: str) -> None:
        """
        Change user's email with validation.

        Business rule: Email must be valid format.

        Args:
            new_email: The new email to set

        Raises:
            BusinessRuleViolationException: If email is invalid
        """
        if not new_email or "@" not in new_email:
            raise BusinessRuleViolationException(
                f"Cannot change email to invalid address: '{new_email}'. Email must contain '@' symbol."
            )

        object.__setattr__(self, "email", new_email)
        object.__setattr__(self, "updated_at", datetime.now(timezone.utc))
