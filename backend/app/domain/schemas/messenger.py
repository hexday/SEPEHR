"""
SEPEHR Backend — Pydantic Schemas: Messenger
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums.all import ConversationType, MemberRole, MessageStatus, MessageType
from app.domain.schemas.auth import UserPublicSchema


# ── Conversation ──────────────────────────────────────────────────────────────

class CreateDirectConversationRequest(BaseModel):
    recipient_username: str = Field(..., min_length=1, max_length=32)


class CreateGroupConversationRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    member_usernames: list[str] = Field(..., min_length=1, max_length=499)


class UpdateGroupRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=128)


class MemberSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user: UserPublicSchema
    role: MemberRole
    joined_at: datetime
    is_muted: bool


class ConversationSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    type: ConversationType
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    last_message_at: Optional[datetime] = None
    created_at: datetime
    member_count: int = 0
    last_message: Optional["MessageSchema"] = None
    unread_count: int = 0


# ── Messages ──────────────────────────────────────────────────────────────────

class SendTextMessageRequest(BaseModel):
    content_encrypted: str = Field(..., min_length=1, max_length=65536)
    iv: str = Field(..., min_length=1, max_length=64)
    content_preview: Optional[str] = Field(None, max_length=256)
    reply_to_id: Optional[str] = Field(None)


class SendLocationMessageRequest(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    reply_to_id: Optional[str] = None


class MessageSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    conversation_id: str
    sender_id: str
    sender: Optional[UserPublicSchema] = None
    type: MessageType
    content_encrypted: Optional[str] = None
    iv: Optional[str] = None
    content_preview: Optional[str] = None
    file_key: Optional[str] = None
    file_url: Optional[str] = None
    file_size: Optional[int] = None
    file_mime: Optional[str] = None
    file_name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    reply_to_id: Optional[str] = None
    is_deleted: bool = False
    created_at: datetime
    status: Optional[MessageStatus] = None


class MessageListResponse(BaseModel):
    messages: list[MessageSchema]
    has_more: bool
    cursor: Optional[str] = None


class ReceiptSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    message_id: str
    user_id: str
    status: MessageStatus
    updated_at: datetime


# ── WebSocket Events ──────────────────────────────────────────────────────────

class WSNewMessageEvent(BaseModel):
    type: str = "new_message"
    payload: MessageSchema


class WSTypingEvent(BaseModel):
    type: str = "typing"
    payload: dict


class WSReadReceiptEvent(BaseModel):
    type: str = "read_receipt"
    payload: ReceiptSchema
