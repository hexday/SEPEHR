"""
SEPEHR Backend — Auth API Endpoints
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.auth import CurrentUser, get_client_ip
from app.domain.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
    TokenResponse,
    UpdateProfileRequest,
    UserPrivateSchema,
)
from app.infrastructure.database.session import get_db
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(
    request_data: RegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Register a new user account."""
    service = AuthService(db)
    _, tokens = await service.register(
        request_data,
        ip_address=get_client_ip(request),
    )
    return tokens


@router.post("/login", response_model=TokenResponse)
async def login(
    request_data: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Authenticate and receive tokens."""
    service = AuthService(db)
    _, tokens = await service.login(
        request_data,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
    )
    return tokens


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request_data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Issue new access token using refresh token."""
    service = AuthService(db)
    return await service.refresh(request_data.refresh_token)


@router.post("/logout", status_code=204)
async def logout(
    request_data: RefreshTokenRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Revoke refresh token and logout."""
    service = AuthService(db)
    await service.logout(request_data.refresh_token)


@router.get("/me", response_model=UserPrivateSchema)
async def get_me(current_user: CurrentUser) -> UserPrivateSchema:
    """Get current user profile."""
    return UserPrivateSchema.model_validate(current_user)


@router.patch("/me", response_model=UserPrivateSchema)
async def update_me(
    request_data: UpdateProfileRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> UserPrivateSchema:
    """Update current user profile."""
    if request_data.display_name is not None:
        current_user.display_name = request_data.display_name
    if request_data.public_key is not None:
        current_user.public_key = request_data.public_key
    return UserPrivateSchema.model_validate(current_user)


@router.post("/change-password", status_code=204)
async def change_password(
    request_data: ChangePasswordRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Change the current user's password."""
    from app.core.security import hash_password, verify_password
    from app.core.exceptions import InvalidCredentialsException

    if not verify_password(request_data.current_password, current_user.password_hash):
        raise InvalidCredentialsException("Current password is incorrect")

    current_user.password_hash = hash_password(request_data.new_password)
