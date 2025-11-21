"""FastAPI application entry point."""

from fastapi import FastAPI, Depends
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from sqlalchemy.exc import SQLAlchemyError

from app.presentation.api.v1 import users, auth
from app.presentation.exception_handlers import (
    application_error_handler,
    domain_exception_handler,
    validation_error_handler,
    database_error_handler,
    generic_exception_handler,
)
from app.presentation.error_schemas import ValidationErrorResponse
from app.application.exceptions import ApplicationError
from app.domain.exceptions import DomainException
from app.infrastructure.config.settings import Settings, get_settings


# Get settings for app configuration
_settings = get_settings()

app = FastAPI(
    title=_settings.app_name,
    description="FastAPI application following Clean Architecture principles with Repository and Unit of Work patterns",
    version=_settings.app_version,
    debug=_settings.debug,
)

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.cors_origins_list,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register exception handlers
# Only 5 handlers needed for ALL exceptions!
# - ApplicationError handles ALL application layer exceptions (UserNotFoundError, etc.)
# - DomainException handles ALL domain layer exceptions
# - RequestValidationError handles Pydantic validation errors
# - SQLAlchemyError handles database errors
# - Exception handles everything else
app.add_exception_handler(ApplicationError, application_error_handler)  # type: ignore[arg-type]
app.add_exception_handler(DomainException, domain_exception_handler)  # type: ignore[arg-type]
app.add_exception_handler(RequestValidationError, validation_error_handler)  # type: ignore[arg-type]
app.add_exception_handler(SQLAlchemyError, database_error_handler)  # type: ignore[arg-type]
app.add_exception_handler(Exception, generic_exception_handler)

# Include routers
app.include_router(users.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")


@app.get("/")
async def root() -> dict[str, str]:
    """Health check endpoint."""
    return {
        "message": _settings.app_name,
        "status": "running",
        "version": _settings.app_version,
        "environment": _settings.environment,
    }


@app.get("/config")
async def show_config(settings: Settings = Depends(get_settings)) -> dict[str, str | int | list[str]]:
    """Show current configuration (non-sensitive data only).

    WARNING: Only for development/debugging. Remove in production.
    """
    return {
        "environment": settings.environment,
        "app_name": settings.app_name,
        "app_version": settings.app_version,
        "debug": settings.debug,
        "cors_origins": settings.cors_origins_list,
    }


def custom_openapi():
    """
    Customize OpenAPI schema to use our custom validation error format.

    Replaces the default HTTPValidationError schema with ValidationErrorResponse
    to match the actual error format returned by our validation_error_handler.
    """
    # Return cached schema if it exists
    if app.openapi_schema:
        return app.openapi_schema

    # Generate the base OpenAPI schema
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    # Get the JSON schema for our custom validation error response
    validation_schema = ValidationErrorResponse.model_json_schema()

    # Remove the default HTTPValidationError from components
    if "HTTPValidationError" in openapi_schema.get("components", {}).get("schemas", {}):
        del openapi_schema["components"]["schemas"]["HTTPValidationError"]

    # Remove ValidationError as well (used by HTTPValidationError)
    if "ValidationError" in openapi_schema.get("components", {}).get("schemas", {}):
        del openapi_schema["components"]["schemas"]["ValidationError"]

    # Add our custom validation error schema
    openapi_schema["components"]["schemas"]["ValidationErrorResponse"] = validation_schema

    # Update all 422 response references to use our custom schema
    for path_data in openapi_schema.get("paths", {}).values():
        for operation in path_data.values():
            if isinstance(operation, dict) and "responses" in operation:
                if "422" in operation["responses"]:
                    operation["responses"]["422"] = {
                        "description": "Validation Error",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ValidationErrorResponse"}
                            }
                        },
                    }

    # Cache the schema
    app.openapi_schema = openapi_schema
    return app.openapi_schema


# Override the default OpenAPI schema generation
app.openapi = custom_openapi