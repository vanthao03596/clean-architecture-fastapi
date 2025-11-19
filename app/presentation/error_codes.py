"""Error code to HTTP status code mapping.

This module provides a centralized mapping of error codes to HTTP status codes.
When you add a new exception, simply add its error_code to this mapping.
"""

from fastapi import status


# Map error codes to HTTP status codes
ERROR_CODE_TO_HTTP_STATUS = {
    # User-related errors
    "USER_NOT_FOUND": status.HTTP_404_NOT_FOUND,
    "USER_ALREADY_EXISTS": status.HTTP_409_CONFLICT,
    "EMAIL_ALREADY_EXISTS": status.HTTP_409_CONFLICT,
    "INVALID_CREDENTIALS": status.HTTP_401_UNAUTHORIZED,
    "EMAIL_NOT_VERIFIED": status.HTTP_403_FORBIDDEN,
    "INSUFFICIENT_PERMISSIONS": status.HTTP_403_FORBIDDEN,

    # Authentication errors
    "TOKEN_EXPIRED": status.HTTP_401_UNAUTHORIZED,
    "INVALID_TOKEN": status.HTTP_401_UNAUTHORIZED,
    "UNAUTHORIZED": status.HTTP_401_UNAUTHORIZED,

    # Domain errors (business rule violations)
    "INVALID_ENTITY_STATE": status.HTTP_400_BAD_REQUEST,
    "BUSINESS_RULE_VIOLATION": status.HTTP_400_BAD_REQUEST,
    "DOMAIN_ERROR": status.HTTP_400_BAD_REQUEST,

    # Application errors
    "APPLICATION_ERROR": status.HTTP_400_BAD_REQUEST,
    "VALIDATION_ERROR": status.HTTP_422_UNPROCESSABLE_ENTITY,

    # Resource errors
    "RESOURCE_NOT_FOUND": status.HTTP_404_NOT_FOUND,
    "RESOURCE_ALREADY_EXISTS": status.HTTP_409_CONFLICT,

    # Infrastructure errors
    "DATABASE_ERROR": status.HTTP_500_INTERNAL_SERVER_ERROR,
    "EXTERNAL_SERVICE_ERROR": status.HTTP_503_SERVICE_UNAVAILABLE,
    "INTERNAL_SERVER_ERROR": status.HTTP_500_INTERNAL_SERVER_ERROR,
}


def get_http_status_for_error_code(error_code: str) -> int:
    """
    Get HTTP status code for a given error code.

    Args:
        error_code: The error code from the exception

    Returns:
        HTTP status code (defaults to 400 if not found)
    """
    return ERROR_CODE_TO_HTTP_STATUS.get(
        error_code,
        status.HTTP_400_BAD_REQUEST,  # Default for unknown errors
    )
