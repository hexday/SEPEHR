"""
SEPEHR Backend — Domain Enumerations
"""

from enum import Enum


class UserRole(str, Enum):
    USER = "user"
    MODERATOR = "moderator"
    PUBLISHER = "publisher"
    ADMINISTRATOR = "administrator"


class ConversationType(str, Enum):
    DIRECT = "direct"
    GROUP = "group"


class MemberRole(str, Enum):
    MEMBER = "member"
    ADMIN = "admin"


class MessageType(str, Enum):
    TEXT = "text"
    VOICE = "voice"
    IMAGE = "image"
    FILE = "file"
    LOCATION = "location"
    SYSTEM = "system"


class MessageStatus(str, Enum):
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"


class NewsPostStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    DANGER = "danger"
    CRITICAL = "critical"


class MapPointType(str, Enum):
    HOSPITAL = "hospital"
    SHELTER = "shelter"
    AID_CENTER = "aid_center"
    SAFE_ROUTE = "safe_route"
    DANGER_ZONE = "danger_zone"
    CHECKPOINT = "checkpoint"
    WATER = "water"
    FOOD = "food"


class AuditAction(str, Enum):
    LOGIN = "login"
    LOGOUT = "logout"
    REGISTER = "register"
    PASSWORD_CHANGE = "password_change"
    TOKEN_REFRESH = "token_refresh"
    USER_UPDATE = "user_update"
    USER_DELETE = "user_delete"
    MESSAGE_DELETE = "message_delete"
    ALERT_CREATE = "alert_create"
    ALERT_UPDATE = "alert_update"
    POST_PUBLISH = "post_publish"
    FILE_UPLOAD = "file_upload"
    ADMIN_ACTION = "admin_action"
