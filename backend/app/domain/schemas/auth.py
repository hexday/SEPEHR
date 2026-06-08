"""
SEPEHR Backend — Pydantic Schemas: Auth & Users
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.enums.all import UserRole


# ── Validation Helpers ────────────────────────────────────────────────────────

USERNAME_RE = re.compile(r"^[a-zA-Z0-9_]{3,32}$")
PASSWORD_MIN_LENGTH = 8


def validate_username(v: str) -> str:
    if not USERNAME_RE.match(v):
        raise ValueError(
            "Username must be 3-32 characters and contain only letters, digits, or underscores"
        )
    return v.lower()


def validate_password(v: str) -> str:
    if len(v) < PASSWORD_MIN_LENGTH:
        raise ValueError(f"Password must be at least {PASSWORD_MIN_LENGTH} characters")
    if len(v) > 128:
        raise ValueError("Password must not exceed 128 characters")
    return v


# ── Request Schemas ───────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=32)
    password: str = Field(..., min_length=8, max_length=128)
    display_name: str = Field(..., min_length=1, max_length=64)
    public_key: Optional[str] = Field(None, max_length=2048)

    @field_validator("username")
    @classmethod
    def check_username(cls, v: str) -> str:
        return validate_username(v)

    @field_validator("password")
    @classmethod
    def check_password(cls, v: str) -> str:
        return validate_password(v)

    @field_validator("display_name")
    @classmethod
    def check_display_name(cls, v: str) -> str:
        return v.strip()


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=32)
    password: str = Field(..., min_length=1, max_length=128)

    @field_validator("username")
    @classmethod
    def normalize_username(cls, v: str) -> str:
        return v.lower().strip()


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., min_length=10)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1, max_length=128)
    new_password: str = Field(..., min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def check_password(cls, v: str) -> str:
        return validate_password(v)


# ── Response Schemas ──────────────────────────────────────────────────────────

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class UserPublicSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    username: str
    display_name: str
    avatar_url: Optional[str] = None
    role: UserRole
    is_active: bool
    last_seen: Optional[datetime] = None
    public_key: Optional[str] = None


class UserPrivateSchema(UserPublicSchema):
    """Full user schema for self-view."""
    created_at: datetime


class UpdateProfileRequest(BaseModel):
    display_name: Optional[str] = Field(None, min_length=1, max_length=64)
    public_key: Optional[str] = Field(None, max_length=2048)

    @field_validator("display_name")
    @classmethod
    def check_display_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Display name cannot be empty")
        return v


# ── Admin Schemas ─────────────────────────────────────────────────────────────

class AdminUpdateUserRequest(BaseModel):
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    display_name: Optional[str] = Field(None, min_length=1, max_length=64)
