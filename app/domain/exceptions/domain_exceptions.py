"""Domain layer exceptions for business rule violations."""


class DomainException(Exception):
    """
    Base exception for domain layer.

    Domain exceptions represent business rule violations and should be
    raised when domain invariants are broken.

    Examples:
        - Invalid entity state
        - Business rule violations
        - Domain constraint failures
    """

    def __init__(self, message: str, error_code: str = "DOMAIN_ERROR"):
        """
        Initialize domain exception.

        Args:
            message: Human-readable error message
            error_code: Machine-readable error code
        """
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)


class InvalidEntityStateException(DomainException):
    """Raised when an entity is in an invalid state."""

    def __init__(self, message: str):
        super().__init__(message, error_code="INVALID_ENTITY_STATE")


class BusinessRuleViolationException(DomainException):
    """Raised when a business rule is violated."""

    def __init__(self, message: str):
        super().__init__(message, error_code="BUSINESS_RULE_VIOLATION")
