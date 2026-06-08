"""
SEPEHR Backend — FastAPI Dependencies
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, WebSocket
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    ForbiddenException,
    InvalidTokenException,
    TokenExpiredException,
    UnauthorizedException,
)
from app.core.security import decode_access_token
from app.domain.enums.all import UserRole
from app.domain.models.all import User
from app.infrastructure.database.session import get_db
from app.infrastructure.cache.redis import cache

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(bearer_scheme)
    ] = None,
    db: AsyncSession = Depends(get_db),
) -> User:
    """Extract and validate the current user from JWT bearer token."""
    if not credentials:
        raise UnauthorizedException()

    try:
        payload = decode_access_token(credentials.credentials)
    except JWTError as e:
        err = str(e)
        if "expired" in err:
            raise TokenExpiredException()
        raise InvalidTokenException()

    user_id: str = payload.get("sub")
    if not user_id:
        raise InvalidTokenException()

    # Check token blacklist (for logged-out tokens)
    blacklisted = await cache.get(f"blacklist:token:{credentials.credentials[:16]}")
    if blacklisted:
        raise InvalidTokenException("Token has been revoked")

    user = await db.scalar(
        select(User).where(User.id == user_id, User.deleted_at.is_(None))
    )
    if not user:
        raise UnauthorizedException()

    if not user.is_active:
        raise ForbiddenException("Account is deactivated")

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_role(*roles: UserRole):
    """Dependency factory that requires specific role(s)."""

    async def check_role(current_user: CurrentUser) -> User:
        if current_user.role not in roles:
            raise ForbiddenException(
                f"This action requires one of: {', '.join(r.value for r in roles)}"
            )
        return current_user

    return check_role


RequireAdmin = Annotated[User, Depends(require_role(UserRole.ADMINISTRATOR))]
RequirePublisher = Annotated[
    User,
    Depends(require_role(UserRole.PUBLISHER, UserRole.ADMINISTRATOR)),
]
RequireModerator = Annotated[
    User,
    Depends(require_role(UserRole.MODERATOR, UserRole.ADMINISTRATOR)),
]


async def get_ws_user(
    websocket: WebSocket,
    token: str,
    db: AsyncSession = Depends(get_db),
) -> User:
    """Authenticate a WebSocket connection via query parameter token."""
    try:
        payload = decode_access_token(token)
    except JWTError:
        await websocket.close(code=4001, reason="Invalid authentication token")
        raise InvalidTokenException()

    user_id = payload.get("sub")
    if not user_id:
        await websocket.close(code=4001, reason="Invalid token payload")
        raise InvalidTokenException()

    user = await db.scalar(
        select(User).where(User.id == user_id, User.deleted_at.is_(None))
    )
    if not user or not user.is_active:
        await websocket.close(code=4003, reason="User not found or inactive")
        raise UnauthorizedException()

    return user


def get_client_ip(request) -> str | None:
    """Extract real client IP considering reverse proxy headers."""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Take the first IP (client), not proxy IPs
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else None
