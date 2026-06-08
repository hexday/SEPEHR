"""
SEPEHR Backend — Auth Service
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    InvalidCredentialsException,
    InvalidTokenException,
    TokenExpiredException,
    UsernameExistsException,
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    hash_password,
    hash_refresh_token,
    needs_rehash,
    verify_password,
)
from app.domain.enums.all import AuditAction, UserRole
from app.domain.models.all import AuditLog, RefreshToken, User
from app.domain.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
)
from app.infrastructure.cache.redis import cache

logger = logging.getLogger(__name__)


class AuthService:

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def register(
        self,
        request: RegisterRequest,
        ip_address: str | None = None,
    ) -> tuple[User, TokenResponse]:
        """Register a new user and issue tokens."""
        # Check username availability
        existing = await self.db.scalar(
            select(User).where(User.username == request.username, User.deleted_at.is_(None))
        )
        if existing:
            raise UsernameExistsException()

        # Create user
        user = User(
            username=request.username,
            password_hash=hash_password(request.password),
            display_name=request.display_name,
            role=UserRole.USER,
            public_key=request.public_key,
            is_active=True,
        )
        self.db.add(user)
        await self.db.flush()  # Get ID before commit

        # Issue tokens
        tokens = await self._issue_tokens(user, ip_address=ip_address)

        # Audit
        self.db.add(
            AuditLog(
                user_id=user.id,
                action=AuditAction.REGISTER,
                ip_address=ip_address,
            )
        )

        return user, tokens

    async def login(
        self,
        request: LoginRequest,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[User, TokenResponse]:
        """Authenticate a user and issue tokens."""
        user = await self.db.scalar(
            select(User).where(
                User.username == request.username,
                User.deleted_at.is_(None),
            )
        )

        # Always run password check to prevent timing attacks
        dummy_hash = "$argon2id$v=19$m=65536,t=3,p=4$dummy$dummy"
        if not user:
            verify_password(request.password, dummy_hash)
            raise InvalidCredentialsException()

        if not verify_password(request.password, user.password_hash):
            self.db.add(
                AuditLog(
                    user_id=user.id,
                    action=AuditAction.LOGIN,
                    ip_address=ip_address,
                    metadata={"success": False},
                )
            )
            raise InvalidCredentialsException()

        if not user.is_active:
            raise InvalidCredentialsException("Account is deactivated")

        # Rehash if needed (algo upgrade)
        if needs_rehash(user.password_hash):
            user.password_hash = hash_password(request.password)

        # Update last_seen
        user.last_seen = datetime.now(timezone.utc)

        tokens = await self._issue_tokens(user, ip_address=ip_address, user_agent=user_agent)

        self.db.add(
            AuditLog(
                user_id=user.id,
                action=AuditAction.LOGIN,
                ip_address=ip_address,
                user_agent=user_agent,
                metadata={"success": True},
            )
        )

        return user, tokens

    async def refresh(self, raw_token: str) -> TokenResponse:
        """Issue new access token using refresh token."""
        token_hash = hash_refresh_token(raw_token)

        refresh_token = await self.db.scalar(
            select(RefreshToken)
            .where(RefreshToken.token_hash == token_hash)
            .with_for_update(skip_locked=True)
        )

        if not refresh_token:
            raise InvalidTokenException("Refresh token not found")

        if refresh_token.revoked_at is not None:
            # Token reuse detected — revoke all tokens for this user
            await self.db.execute(
                update(RefreshToken)
                .where(
                    RefreshToken.user_id == refresh_token.user_id,
                    RefreshToken.revoked_at.is_(None),
                )
                .values(revoked_at=datetime.now(timezone.utc))
            )
            logger.warning(f"Refresh token reuse detected for user {refresh_token.user_id}")
            raise InvalidTokenException("Token has been revoked")

        if refresh_token.expires_at < datetime.now(timezone.utc):
            raise TokenExpiredException()

        # Rotate: revoke current, issue new
        refresh_token.revoked_at = datetime.now(timezone.utc)

        user = await self.db.get(User, refresh_token.user_id)
        if not user or not user.is_active:
            raise InvalidCredentialsException("Account unavailable")

        return await self._issue_tokens(
            user,
            ip_address=refresh_token.ip_address,
        )

    async def logout(self, raw_token: str) -> None:
        """Revoke a refresh token."""
        token_hash = hash_refresh_token(raw_token)
        await self.db.execute(
            update(RefreshToken)
            .where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(timezone.utc))
        )

    async def _issue_tokens(
        self,
        user: User,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> TokenResponse:
        """Create and store refresh token, return token pair."""
        raw_refresh, hashed_refresh = create_refresh_token()
        expires_at = datetime.now(timezone.utc) + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )

        refresh_token_record = RefreshToken(
            user_id=user.id,
            token_hash=hashed_refresh,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.db.add(refresh_token_record)

        access_token = create_access_token(
            subject=user.id,
            additional_claims={"role": user.role.value, "username": user.username},
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=raw_refresh,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )
