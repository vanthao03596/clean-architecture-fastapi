"""Authentication API endpoints."""

from fastapi import APIRouter, Depends, status

from app.application.services.auth_service import AuthService
from app.application.dtos.auth_dto import LoginDTO, TokenDTO, RefreshTokenDTO
from app.application.dtos.user_dto import UserDTO
from app.presentation.dependencies import get_auth_service, get_current_user


router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post(
    "/login",
    response_model=TokenDTO,
    status_code=status.HTTP_200_OK,
    summary="User login",
    description="Authenticate user with email and password, returns access and refresh tokens.",
)
async def login(
    dto: LoginDTO,
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Authenticate user and receive JWT tokens.

    Returns both access token (short-lived) and refresh token (long-lived).
    Use the access token in the Authorization header for subsequent requests.

    Raises:
        401 Unauthorized: If email or password is incorrect
    """
    return await auth_service.login(dto)


@router.post(
    "/refresh",
    response_model=TokenDTO,
    status_code=status.HTTP_200_OK,
    summary="Refresh access token",
    description="Obtain a new access token using a refresh token.",
)
async def refresh_token(
    dto: RefreshTokenDTO,
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Get new access token using refresh token.

    When your access token expires, use this endpoint with your refresh
    token to obtain a new access token without re-authenticating.

    Raises:
        401 Unauthorized: If refresh token is invalid or expired
    """
    return await auth_service.refresh_token(dto)


@router.get(
    "/me",
    response_model=UserDTO,
    status_code=status.HTTP_200_OK,
    summary="Get current user",
    description="Get the currently authenticated user's information.",
)
async def get_me(
    current_user: UserDTO = Depends(get_current_user),
):
    """
    Get current authenticated user.

    This endpoint requires a valid access token in the Authorization header:
    Authorization: Bearer <your_access_token>

    Raises:
        401 Unauthorized: If token is missing, invalid, or expired
    """
    return current_user
