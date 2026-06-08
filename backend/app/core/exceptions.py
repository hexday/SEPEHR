"""
SEPEHR Backend — Structured Exception Hierarchy
"""

from __future__ import annotations

from typing import Any


class SEPEHRException(Exception):
    """Base exception for all SEPEHR errors."""

    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"
    message: str = "An unexpected error occurred"

    def __init__(
        self,
        message: str | None = None,
        detail: Any = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.message = message or self.__class__.message
        self.detail = detail
        self.headers = headers
        super().__init__(self.message)


# ── 400 Bad Request ──────────────────────────────────────────────────────────

class ValidationException(SEPEHRException):
    status_code = 422
    error_code = "VALIDATION_ERROR"
    message = "Input validation failed"


class BadRequestException(SEPEHRException):
    status_code = 400
    error_code = "BAD_REQUEST"
    message = "Invalid request"


# ── 401 Unauthorized ─────────────────────────────────────────────────────────

class UnauthorizedException(SEPEHRException):
    status_code = 401
    error_code = "UNAUTHORIZED"
    message = "Authentication required"

    def __init__(self, message: str | None = None, **kwargs: Any) -> None:
        super().__init__(message, **kwargs)
        self.headers = {"WWW-Authenticate": "Bearer"}


class InvalidCredentialsException(UnauthorizedException):
    error_code = "INVALID_CREDENTIALS"
    message = "Invalid username or password"


class TokenExpiredException(UnauthorizedException):
    error_code = "TOKEN_EXPIRED"
    message = "Authentication token has expired"


class InvalidTokenException(UnauthorizedException):
    error_code = "INVALID_TOKEN"
    message = "Invalid authentication token"


# ── 403 Forbidden ─────────────────────────────────────────────────────────────

class ForbiddenException(SEPEHRException):
    status_code = 403
    error_code = "FORBIDDEN"
    message = "Access denied"


class InsufficientPermissionsException(ForbiddenException):
    error_code = "INSUFFICIENT_PERMISSIONS"
    message = "You do not have permission to perform this action"


# ── 404 Not Found ─────────────────────────────────────────────────────────────

class NotFoundException(SEPEHRException):
    status_code = 404
    error_code = "NOT_FOUND"
    message = "Resource not found"


class UserNotFoundException(NotFoundException):
    error_code = "USER_NOT_FOUND"
    message = "User not found"


class ConversationNotFoundException(NotFoundException):
    error_code = "CONVERSATION_NOT_FOUND"
    message = "Conversation not found"


class MessageNotFoundException(NotFoundException):
    error_code = "MESSAGE_NOT_FOUND"
    message = "Message not found"


class NewsServerNotFoundException(NotFoundException):
    error_code = "NEWS_SERVER_NOT_FOUND"
    message = "News server not found"


class NewsPostNotFoundException(NotFoundException):
    error_code = "NEWS_POST_NOT_FOUND"
    message = "News post not found"


# ── 409 Conflict ──────────────────────────────────────────────────────────────

class ConflictException(SEPEHRException):
    status_code = 409
    error_code = "CONFLICT"
    message = "Resource conflict"


class UsernameExistsException(ConflictException):
    error_code = "USERNAME_EXISTS"
    message = "Username is already taken"


# ── 413 Payload Too Large ─────────────────────────────────────────────────────

class FileTooLargeException(SEPEHRException):
    status_code = 413
    error_code = "FILE_TOO_LARGE"
    message = "Uploaded file exceeds size limit"


# ── 415 Unsupported Media Type ────────────────────────────────────────────────

class UnsupportedFileTypeException(SEPEHRException):
    status_code = 415
    error_code = "UNSUPPORTED_FILE_TYPE"
    message = "File type is not allowed"


# ── 429 Rate Limited ──────────────────────────────────────────────────────────

class RateLimitException(SEPEHRException):
    status_code = 429
    error_code = "RATE_LIMITED"
    message = "Too many requests. Please slow down."


# ── 503 Service Unavailable ───────────────────────────────────────────────────

class ServiceUnavailableException(SEPEHRException):
    status_code = 503
    error_code = "SERVICE_UNAVAILABLE"
    message = "Service is temporarily unavailable"
