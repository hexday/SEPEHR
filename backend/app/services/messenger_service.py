"""
SEPEHR Backend — Messenger Service
"""

from __future__ import annotations

import base64
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.exceptions import (
    BadRequestException,
    ConversationNotFoundException,
    ForbiddenException,
    UserNotFoundException,
)
from app.core.security import generate_storage_key, safe_filename
from app.domain.enums.all import ConversationType, MemberRole, MessageStatus, MessageType
from app.domain.models.all import (
    Conversation,
    ConversationMember,
    Message,
    MessageReceipt,
    User,
)
from app.domain.schemas.messenger import (
    ConversationSchema,
    MessageSchema,
    SendLocationMessageRequest,
    SendTextMessageRequest,
)
from app.infrastructure.storage.minio import storage
from app.infrastructure.websocket.manager import ws_manager

logger = logging.getLogger(__name__)


class MessengerService:

    def __init__(self, db: AsyncSession, current_user: User) -> None:
        self.db = db
        self.current_user = current_user

    # ── Conversations ─────────────────────────────────────────────────────────

    async def get_conversations(self, limit: int = 30, offset: int = 0) -> list[Conversation]:
        """Get all conversations for the current user, ordered by last activity."""
        result = await self.db.execute(
            select(Conversation)
            .join(
                ConversationMember,
                and_(
                    ConversationMember.conversation_id == Conversation.id,
                    ConversationMember.user_id == self.current_user.id,
                    ConversationMember.left_at.is_(None),
                ),
            )
            .where(Conversation.deleted_at.is_(None))
            .options(
                selectinload(Conversation.members).selectinload(ConversationMember.user)
            )
            .order_by(Conversation.last_message_at.desc().nullslast())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def get_or_create_direct_conversation(
        self, recipient_username: str
    ) -> Conversation:
        """Get existing direct conversation or create one."""
        # Find recipient
        recipient = await self.db.scalar(
            select(User).where(
                User.username == recipient_username,
                User.is_active.is_(True),
                User.deleted_at.is_(None),
            )
        )
        if not recipient:
            raise UserNotFoundException(f"User '{recipient_username}' not found")

        if recipient.id == self.current_user.id:
            raise BadRequestException("Cannot start a conversation with yourself")

        # Check if direct conversation already exists
        existing = await self.db.scalar(
            select(Conversation)
            .join(
                ConversationMember,
                ConversationMember.conversation_id == Conversation.id,
            )
            .where(
                Conversation.type == ConversationType.DIRECT,
                Conversation.deleted_at.is_(None),
                ConversationMember.user_id == self.current_user.id,
                ConversationMember.left_at.is_(None),
            )
            .where(
                Conversation.id.in_(
                    select(ConversationMember.conversation_id).where(
                        ConversationMember.user_id == recipient.id,
                        ConversationMember.left_at.is_(None),
                    )
                )
            )
        )
        if existing:
            return existing

        # Create new direct conversation
        conversation = Conversation(
            type=ConversationType.DIRECT,
            created_by=self.current_user.id,
        )
        self.db.add(conversation)
        await self.db.flush()

        # Add both members
        for user_id, role in [
            (self.current_user.id, MemberRole.ADMIN),
            (recipient.id, MemberRole.ADMIN),
        ]:
            self.db.add(
                ConversationMember(
                    conversation_id=conversation.id,
                    user_id=user_id,
                    role=role,
                )
            )

        return conversation

    async def create_group_conversation(
        self, name: str, member_usernames: list[str]
    ) -> Conversation:
        """Create a group conversation."""
        if len(member_usernames) > 499:
            raise BadRequestException("Group cannot exceed 500 members")

        # Resolve all usernames
        users = await self.db.execute(
            select(User).where(
                User.username.in_(member_usernames),
                User.is_active.is_(True),
                User.deleted_at.is_(None),
            )
        )
        resolved_users = list(users.scalars().all())

        if len(resolved_users) != len(set(member_usernames)):
            found = {u.username for u in resolved_users}
            missing = set(member_usernames) - found
            raise UserNotFoundException(f"Users not found: {', '.join(missing)}")

        conversation = Conversation(
            type=ConversationType.GROUP,
            name=name,
            created_by=self.current_user.id,
        )
        self.db.add(conversation)
        await self.db.flush()

        # Add creator as admin
        self.db.add(
            ConversationMember(
                conversation_id=conversation.id,
                user_id=self.current_user.id,
                role=MemberRole.ADMIN,
            )
        )

        # Add all other members
        for user in resolved_users:
            if user.id != self.current_user.id:
                self.db.add(
                    ConversationMember(
                        conversation_id=conversation.id,
                        user_id=user.id,
                        role=MemberRole.MEMBER,
                    )
                )

        return conversation

    async def _assert_member(self, conversation_id: str) -> ConversationMember:
        """Verify current user is an active member of the conversation."""
        membership = await self.db.scalar(
            select(ConversationMember).where(
                ConversationMember.conversation_id == conversation_id,
                ConversationMember.user_id == self.current_user.id,
                ConversationMember.left_at.is_(None),
            )
        )
        if not membership:
            raise ForbiddenException("You are not a member of this conversation")
        return membership

    # ── Messages ──────────────────────────────────────────────────────────────

    async def get_messages(
        self,
        conversation_id: str,
        limit: int = 30,
        before_id: str | None = None,
    ) -> tuple[list[Message], bool]:
        """Get messages with cursor-based pagination."""
        await self._assert_member(conversation_id)

        query = (
            select(Message)
            .where(
                Message.conversation_id == conversation_id,
                Message.is_deleted.is_(False),
            )
            .options(selectinload(Message.sender))
            .order_by(Message.created_at.desc())
            .limit(limit + 1)
        )

        if before_id:
            cursor_msg = await self.db.get(Message, before_id)
            if cursor_msg:
                query = query.where(Message.created_at < cursor_msg.created_at)

        result = await self.db.execute(query)
        messages = list(result.scalars().all())

        has_more = len(messages) > limit
        return messages[:limit][::-1], has_more

    async def send_text_message(
        self, conversation_id: str, request: SendTextMessageRequest
    ) -> Message:
        """Send an encrypted text message."""
        await self._assert_member(conversation_id)

        conversation = await self.db.scalar(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.deleted_at.is_(None),
            )
        )
        if not conversation:
            raise ConversationNotFoundException()

        message = Message(
            conversation_id=conversation_id,
            sender_id=self.current_user.id,
            type=MessageType.TEXT,
            content_encrypted=request.content_encrypted,
            iv=request.iv,
            content_preview=request.content_preview,
            reply_to_id=request.reply_to_id,
        )
        self.db.add(message)

        # Update conversation last_message_at
        conversation.last_message_at = datetime.now(timezone.utc)

        await self.db.flush()

        # Get all member IDs for WebSocket notifications
        member_ids_result = await self.db.execute(
            select(ConversationMember.user_id).where(
                ConversationMember.conversation_id == conversation_id,
                ConversationMember.left_at.is_(None),
                ConversationMember.user_id != self.current_user.id,
            )
        )
        member_ids = list(member_ids_result.scalars().all())

        # Add sent receipt for sender
        self.db.add(
            MessageReceipt(
                message_id=message.id,
                user_id=self.current_user.id,
                status=MessageStatus.SENT,
            )
        )

        return message

    async def send_location_message(
        self, conversation_id: str, request: SendLocationMessageRequest
    ) -> Message:
        """Send a location pin message."""
        await self._assert_member(conversation_id)

        message = Message(
            conversation_id=conversation_id,
            sender_id=self.current_user.id,
            type=MessageType.LOCATION,
            latitude=request.latitude,
            longitude=request.longitude,
            reply_to_id=request.reply_to_id,
        )
        self.db.add(message)

        conversation = await self.db.get(Conversation, conversation_id)
        if conversation:
            conversation.last_message_at = datetime.now(timezone.utc)

        return message

    async def delete_message(self, message_id: str) -> None:
        """Soft-delete a message (only sender or admin can delete)."""
        message = await self.db.scalar(
            select(Message)
            .where(Message.id == message_id)
            .options(selectinload(Message.conversation))
        )
        if not message:
            raise ConversationNotFoundException("Message not found")

        membership = await self._assert_member(message.conversation_id)

        if message.sender_id != self.current_user.id and membership.role != MemberRole.ADMIN:
            raise ForbiddenException("You can only delete your own messages")

        message.is_deleted = True
        message.deleted_at = datetime.now(timezone.utc)
        message.content_encrypted = None
        message.content_preview = "[deleted]"

    async def mark_as_read(self, conversation_id: str, message_id: str) -> None:
        """Mark all messages up to message_id as read."""
        membership = await self._assert_member(conversation_id)
        membership.last_read_message_id = message_id

        # Update receipt
        await self.db.execute(
            update(MessageReceipt)
            .where(
                MessageReceipt.message_id == message_id,
                MessageReceipt.user_id == self.current_user.id,
            )
            .values(status=MessageStatus.READ)
        )

    async def upload_media(
        self,
        conversation_id: str,
        file_data: bytes,
        filename: str,
        content_type: str,
        message_type: MessageType,
    ) -> Message:
        """Upload media and create a message."""
        await self._assert_member(conversation_id)

        # Validate size
        max_sizes = {
            MessageType.IMAGE: settings.MAX_IMAGE_SIZE_MB * 1024 * 1024,
            MessageType.VOICE: settings.MAX_VOICE_SIZE_MB * 1024 * 1024,
            MessageType.FILE: settings.MAX_FILE_SIZE_MB * 1024 * 1024,
        }
        if len(file_data) > max_sizes.get(message_type, settings.MAX_FILE_SIZE_MB * 1024 * 1024):
            raise BadRequestException("File exceeds maximum allowed size")

        # Determine bucket
        from app.core.config import settings as cfg
        bucket_map = {
            MessageType.IMAGE: cfg.MINIO_BUCKET_MEDIA,
            MessageType.VOICE: cfg.MINIO_BUCKET_VOICE,
            MessageType.FILE: cfg.MINIO_BUCKET_FILES,
        }
        bucket = bucket_map.get(message_type, cfg.MINIO_BUCKET_FILES)

        # Store file
        safe_name = safe_filename(filename)
        object_key = generate_storage_key(
            f"messages/{conversation_id}", self.current_user.id, safe_name
        )
        storage.upload_file(bucket, object_key, file_data, content_type)

        message = Message(
            conversation_id=conversation_id,
            sender_id=self.current_user.id,
            type=message_type,
            file_key=object_key,
            file_size=len(file_data),
            file_mime=content_type,
            file_name=safe_name,
        )
        self.db.add(message)

        conversation = await self.db.get(Conversation, conversation_id)
        if conversation:
            conversation.last_message_at = datetime.now(timezone.utc)

        return message
