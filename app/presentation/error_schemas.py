"""Pydantic models for error responses used in OpenAPI schema generation."""

from pydantic import BaseModel, Field


class ValidationErrorDetail(BaseModel):
    """Model for individual field validation error.

    Represents a single validation error with the field location and error message.
    """

    field: str = Field(
        ...,
        description="The field path where the validation error occurred (e.g., 'body.email', 'query.page')",
        examples=["body.email", "body.name", "query.page"],
    )
    message: str = Field(
        ...,
        description="Human-readable error message describing what went wrong",
        examples=[
            "value is not a valid email address",
            "field required",
            "value is not a valid integer",
        ],
    )


class ValidationErrorResponse(BaseModel):
    """Model for the complete 422 validation error response.

    This is the actual format returned by the validation_error_handler
    in app/presentation/exception_handlers.py, matching our custom error pattern.
    """

    detail: str = Field(
        ...,
        description="High-level description of the error",
        examples=["Validation failed"],
    )
    error_code: str = Field(
        ...,
        description="Machine-readable error code for client-side error handling",
        examples=["VALIDATION_ERROR"],
    )
    errors: list[ValidationErrorDetail] = Field(
        ...,
        description="List of all validation errors found in the request",
        min_length=1,
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "detail": "Validation failed",
                "error_code": "VALIDATION_ERROR",
                "errors": [
                    {
                        "field": "body.email",
                        "message": "value is not a valid email address",
                    },
                    {
                        "field": "body.name",
                        "message": "field required",
                    },
                ],
            }
        }
    }
