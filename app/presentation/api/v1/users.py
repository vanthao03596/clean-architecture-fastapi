"""User API endpoints."""

from fastapi import APIRouter, Depends, status

from app.application.dtos.user_dto import CreateUserDTO, UpdateUserDTO, UserDTO
from app.application.services.user_service import UserService
from app.presentation.dependencies import get_user_service

router = APIRouter(prefix="/users", tags=["users"])


@router.post(
    "/",
    response_model=UserDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user",
    description="Create a new user with email, name, and password.",
)
async def create_user(
    dto: CreateUserDTO,
    service: UserService = Depends(get_user_service),
) -> UserDTO:
    """
    Create a new user.

    Exception handling is done by global exception handlers.
    The service layer raises domain/application exceptions,
    which are automatically converted to appropriate HTTP responses.
    """
    return await service.create_user(dto)


@router.get(
    "/{user_id}",
    response_model=UserDTO,
    summary="Get user by ID",
    description="Retrieve a user by their ID.",
)
async def get_user(
    user_id: int,
    service: UserService = Depends(get_user_service),
) -> UserDTO:
    """Get user by ID."""
    return await service.get_user_by_id(user_id)


@router.get(
    "/",
    response_model=list[UserDTO],
    summary="Get all users",
    description="Retrieve all users with optional pagination.",
)
async def get_users(
    skip: int = 0,
    limit: int = 100,
    service: UserService = Depends(get_user_service),
) -> list[UserDTO]:
    """Get all users with pagination."""
    return await service.get_all_users(skip=skip, limit=limit)


@router.put(
    "/{user_id}",
    response_model=UserDTO,
    summary="Update user",
    description="Update user information (email and/or name).",
)
async def update_user(
    user_id: int,
    dto: UpdateUserDTO,
    service: UserService = Depends(get_user_service),
) -> UserDTO:
    """Update user."""
    return await service.update_user(user_id, dto)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete user",
    description="Delete a user by their ID.",
)
async def delete_user(
    user_id: int,
    service: UserService = Depends(get_user_service),
) -> None:
    """Delete user."""
    await service.delete_user(user_id)
