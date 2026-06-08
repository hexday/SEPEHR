"""
SEPEHR Backend — SQLAlchemy 2.0 Domain Models
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.domain.enums.all import (
    AlertSeverity,
    AuditAction,
    ConversationType,
    MapPointType,
    MemberRole,
    MessageStatus,
    MessageType,
    NewsPostStatus,
    UserRole,
)


def gen_uuid() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class SoftDeleteMixin:
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None


# ── Users ─────────────────────────────────────────────────────────────────────

class User(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=gen_uuid
    )
    username: Mapped[str] = mapped_column(
        String(32), unique=True, nullable=False, index=True
    )
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    display_name: Mapped[str] = mapped_column(String(64), nullable=False)
    avatar_key: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole), nullable=False, default=UserRole.USER, index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_seen: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    public_key: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    refresh_tokens: Mapped[list[RefreshToken]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    sent_messages: Mapped[list[Message]] = relationship(
        back_populates="sender", foreign_keys="Message.sender_id"
    )
    conversation_memberships: Mapped[list[ConversationMember]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    audit_logs: Mapped[list[AuditLog]] = relationship(back_populates="user")

    __table_args__ = (
        Index("ix_users_username_active", "username", "is_active"),
    )


class RefreshToken(Base, TimestampMixin):
    __tablename__ = "refresh_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    user_agent: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    user: Mapped[User] = relationship(back_populates="refresh_tokens")

    @property
    def is_valid(self) -> bool:
        from datetime import timezone

        return (
            self.revoked_at is None
            and self.expires_at > datetime.now(timezone.utc)
        )


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    user_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    action: Mapped[AuditAction] = mapped_column(SAEnum(AuditAction), nullable=False, index=True)
    resource_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    resource_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    user: Mapped[Optional[User]] = relationship(back_populates="audit_logs")


# ── Messenger ─────────────────────────────────────────────────────────────────

class Conversation(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    type: Mapped[ConversationType] = mapped_column(
        SAEnum(ConversationType), nullable=False, index=True
    )
    name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    avatar_key: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    created_by: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=False
    )
    last_message_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    members: Mapped[list[ConversationMember]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan"
    )
    messages: Mapped[list[Message]] = relationship(
        back_populates="conversation",
        order_by="Message.created_at",
    )


class ConversationMember(Base, TimestampMixin):
    __tablename__ = "conversation_members"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    conversation_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[MemberRole] = mapped_column(
        SAEnum(MemberRole), nullable=False, default=MemberRole.MEMBER
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    left_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_muted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_read_message_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    conversation: Mapped[Conversation] = relationship(back_populates="members")
    user: Mapped[User] = relationship(back_populates="conversation_memberships")

    __table_args__ = (
        UniqueConstraint("conversation_id", "user_id", name="uq_conv_member"),
    )


class Message(Base, TimestampMixin):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    conversation_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sender_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=False, index=True
    )
    type: Mapped[MessageType] = mapped_column(
        SAEnum(MessageType), nullable=False, default=MessageType.TEXT
    )
    # Encrypted content (base64-encoded ciphertext)
    content_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    iv: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    # Plain preview for search (truncated, optional)
    content_preview: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    # For file/voice/image messages
    file_key: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    file_size: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    file_mime: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    file_name: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    # Location
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    # Threading
    reply_to_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("messages.id", ondelete="SET NULL"), nullable=True
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    conversation: Mapped[Conversation] = relationship(back_populates="messages")
    sender: Mapped[User] = relationship(back_populates="sent_messages", foreign_keys=[sender_id])
    receipts: Mapped[list[MessageReceipt]] = relationship(
        back_populates="message", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_messages_conv_created", "conversation_id", "created_at"),
    )


class MessageReceipt(Base):
    __tablename__ = "message_receipts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    message_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[MessageStatus] = mapped_column(
        SAEnum(MessageStatus), nullable=False, default=MessageStatus.SENT
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    message: Mapped[Message] = relationship(back_populates="receipts")

    __table_args__ = (
        UniqueConstraint("message_id", "user_id", name="uq_receipt_msg_user"),
    )


# ── News ──────────────────────────────────────────────────────────────────────

class NewsServer(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "news_servers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    slug: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    icon_key: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    created_by: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=False
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    categories: Mapped[list[NewsCategory]] = relationship(
        back_populates="server", cascade="all, delete-orphan"
    )
    posts: Mapped[list[NewsPost]] = relationship(back_populates="server")


class NewsCategory(Base, TimestampMixin):
    __tablename__ = "news_categories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    server_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("news_servers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    slug: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    color: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    server: Mapped[NewsServer] = relationship(back_populates="categories")
    posts: Mapped[list[NewsPost]] = relationship(back_populates="category")

    __table_args__ = (
        UniqueConstraint("server_id", "slug", name="uq_category_server_slug"),
    )


class NewsPost(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "news_posts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    server_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("news_servers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("news_categories.id", ondelete="SET NULL"), nullable=True, index=True
    )
    publisher_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    slug: Mapped[str] = mapped_column(String(512), nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    cover_image_key: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    video_url: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    status: Mapped[NewsPostStatus] = mapped_column(
        SAEnum(NewsPostStatus), nullable=False, default=NewsPostStatus.DRAFT, index=True
    )
    published_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    server: Mapped[NewsServer] = relationship(back_populates="posts")
    category: Mapped[Optional[NewsCategory]] = relationship(back_populates="posts")

    __table_args__ = (
        Index("ix_news_posts_server_published", "server_id", "published_at"),
        Index("ix_news_posts_status_published", "status", "published_at"),
    )


# ── Emergency Alerts ──────────────────────────────────────────────────────────

class EmergencyAlert(Base, TimestampMixin):
    __tablename__ = "emergency_alerts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[AlertSeverity] = mapped_column(
        SAEnum(AlertSeverity), nullable=False, index=True
    )
    area_geojson: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    issued_by: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=False
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)


# ── Map Points ────────────────────────────────────────────────────────────────

class MapPoint(Base, TimestampMixin):
    __tablename__ = "map_points"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    type: Mapped[MapPointType] = mapped_column(
        SAEnum(MapPointType), nullable=False, index=True
    )
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    contact: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    created_by: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=False
    )

    __table_args__ = (
        Index("ix_map_points_type_active", "type", "is_active"),
        Index("ix_map_points_latlong", "latitude", "longitude"),
    )
