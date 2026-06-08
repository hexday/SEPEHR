"""
SEPEHR Backend — Security: JWT, password hashing, token management
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import struct
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, VerifyMismatchError
from jose import JWTError, jwt

from app.core.config import settings

# ── Password Hashing ──────────────────────────────────────────────────────────

_ph = PasswordHasher(
    time_cost=settings.ARGON2_TIME_COST,
    memory_cost=settings.ARGON2_MEMORY_COST,
    parallelism=settings.ARGON2_PARALLELISM,
)


def hash_password(plain: str) -> str:
    """Hash a plaintext password with Argon2id."""
    return _ph.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against an Argon2id hash."""
    try:
        return _ph.verify(hashed, plain)
    except (VerifyMismatchError, VerificationError):
        return False


def needs_rehash(hashed: str) -> bool:
    """Check if the hash needs to be upgraded."""
    return _ph.check_needs_rehash(hashed)


# ── JWT Tokens ────────────────────────────────────────────────────────────────

def create_access_token(
    subject: str | int,
    additional_claims: dict[str, Any] | None = None,
) -> str:
    """Create a short-lived JWT access token."""
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "iat": now,
        "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        "type": "access",
    }
    if additional_claims:
        payload.update(additional_claims)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token() -> tuple[str, str]:
    """
    Create a refresh token.
    Returns (raw_token, hashed_token).
    raw_token is given to the client; hashed_token is stored in DB.
    """
    raw = secrets.token_urlsafe(64)
    hashed = _hash_token(raw)
    return raw, hashed


def _hash_token(token: str) -> str:
    """Deterministic SHA-256 hash of a token for DB storage."""
    return hashlib.sha256(token.encode()).hexdigest()


def hash_refresh_token(raw: str) -> str:
    return _hash_token(raw)


def decode_access_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a JWT access token.
    Raises JWTError on failure.
    """
    payload = jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
    )
    if payload.get("type") != "access":
        raise JWTError("Invalid token type")
    return payload


# ── CSRF / Nonce ──────────────────────────────────────────────────────────────

def generate_nonce() -> str:
    """Generate a cryptographically secure nonce for CSP headers."""
    return secrets.token_urlsafe(16)


# ── File Security ─────────────────────────────────────────────────────────────

def safe_filename(filename: str) -> str:
    """Sanitize a filename, stripping path components and dangerous chars."""
    import re
    basename = os.path.basename(filename)
    safe = re.sub(r"[^\w\-.]", "_", basename)
    # Prevent double extensions attack
    parts = safe.rsplit(".", 1)
    if len(parts) == 2:
        name, ext = parts
        safe = f"{name[:100]}.{ext[:10]}"
    return safe or "unnamed"


def generate_storage_key(prefix: str, user_id: str, filename: str) -> str:
    """Generate a unique, non-guessable storage key for uploaded files."""
    random_part = secrets.token_urlsafe(16)
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
    return f"{prefix}/{user_id}/{random_part}.{ext}"
