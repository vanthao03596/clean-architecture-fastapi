"""Exception handlers for converting exceptions to HTTP responses.

This module provides a scalable approach to exception handling.
Instead of creating individual handlers for each exception, we use
base exception handlers that automatically determine the HTTP status
code based on the error_code attribute.

To add a new exception:
1. Create the exception class (inheriting from ApplicationError or DomainException)
2. Add its error_code to ERROR_CODE_TO_HTTP_STATUS in error_codes.py
3. That's it! No need to create or register a new handler.
"""

import logging

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.application.exceptions import ApplicationError
from app.domain.exceptions import DomainException
from app.presentation.error_codes import get_http_status_for_error_code

# Configure logger (in production, use proper logging configuration)
logger = logging.getLogger(__name__)


async def application_error_handler(
    request: Request, exc: ApplicationError
) -> JSONResponse:
    """
    Handle ALL application layer exceptions.

    This single handler handles all ApplicationError subclasses.
    The HTTP status code is determined by the error_code attribute
    using the ERROR_CODE_TO_HTTP_STATUS mapping.

    No need to create individual handlers for each exception type!
    """
    http_status = get_http_status_for_error_code(exc.error_code)

    return JSONResponse(
        status_code=http_status,
        content={
            "detail": exc.message,
            "error_code": exc.error_code,
        },
    )


async def domain_exception_handler(
    request: Request, exc: DomainException
) -> JSONResponse:
    """
    Handle ALL domain layer exceptions.

    This single handler handles all DomainException subclasses.
    The HTTP status code is determined by the error_code attribute.
    """
    http_status = get_http_status_for_error_code(exc.error_code)

    return JSONResponse(
        status_code=http_status,
        content={
            "detail": exc.message,
            "error_code": exc.error_code,
        },
    )


async def validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """
    Handle Pydantic validation errors from request data.

    Transforms FastAPI's RequestValidationError into a structured,
    user-friendly format that matches our standard error response pattern.

    Returns a list of all validation errors with field locations and messages.
    """
    # Extract all validation errors from Pydantic
    errors = exc.errors()

    # Transform Pydantic errors into our standardized format
    validation_errors = []
    for error in errors:
        # Build field path (e.g., "body.email" or "query.page")
        field_location = ".".join(str(loc) for loc in error["loc"])

        validation_errors.append(
            {
                "field": field_location,
                "message": error["msg"],
            }
        )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Validation failed",
            "error_code": "VALIDATION_ERROR",
            "errors": validation_errors,
        },
    )


async def database_error_handler(
    request: Request, exc: SQLAlchemyError
) -> JSONResponse:
    """
    Handle database errors.

    Catches SQLAlchemy exceptions and returns a standardized error response
    without exposing internal database details.
    """
    # Log the actual error for debugging
    logger.error(f"Database error: {exc}", exc_info=True)

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "An internal database error occurred",
            "error_code": "DATABASE_ERROR",
        },
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle all other unhandled exceptions.

    This is the catch-all handler for any unexpected errors.
    """
    # Log the actual error for debugging
    logger.error(f"Unhandled error: {exc}", exc_info=True)

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "An internal server error occurred",
            "error_code": "INTERNAL_SERVER_ERROR",
        },
    )
