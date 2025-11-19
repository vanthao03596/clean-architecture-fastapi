"""FastAPI application entry point."""

from fastapi import FastAPI, Depends
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError

from app.presentation.api.v1 import users, auth
from app.presentation.exception_handlers import (
    application_error_handler,
    domain_exception_handler,
    validation_error_handler,
    database_error_handler,
    generic_exception_handler,
)
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
        "database_host": settings.db_host,
        "database_name": settings.db_name,
        "debug": settings.debug,
        "cors_origins": settings.cors_origins_list,
    }