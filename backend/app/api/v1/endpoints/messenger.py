"""
SEPEHR Backend — Messenger API Endpoints
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.auth import CurrentUser
from app.core.config import settings
from app.core.exceptions import UnsupportedFileTypeException
from app.domain.enums.all import MessageType
from app.domain.schemas.messenger import (
    ConversationSchema,
    CreateDirectConversationRequest,
    CreateGroupConversationRequest,
    MessageListResponse,
    MessageSchema,
)
from app.infrastructure.database.session import get_db
from app.services.messenger_service import MessengerService

router = APIRouter(prefix="/messenger", tags=["Messenger"])


@router.get("/conversations", response_model=list[ConversationSchema])
async def list_conversations(
    current_user: CurrentUser,
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> list[ConversationSchema]:
    """List all conversations for the current user."""
    service = MessengerService(db, current_user)
    conversations = await service.get_conversations(limit=limit, offset=offset)
    return [ConversationSchema.model_validate(c) for c in conversations]


@router.post("/conversations/direct", response_model=ConversationSchema, status_code=201)
async def create_direct_conversation(
    request_data: CreateDirectConversationRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> ConversationSchema:
    """Get or create a direct conversation with another user."""
    service = MessengerService(db, current_user)
    conv = await service.get_or_create_direct_conversation(request_data.recipient_username)
    return ConversationSchema.model_validate(conv)


@router.post("/conversations/group", response_model=ConversationSchema, status_code=201)
async def create_group_conversation(
    request_data: CreateGroupConversationRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> ConversationSchema:
    """Create a new group conversation."""
    service = MessengerService(db, current_user)
    conv = await service.create_group_conversation(
        request_data.name, request_data.member_usernames
    )
    return ConversationSchema.model_validate(conv)


@router.get("/conversations/{conversation_id}/messages", response_model=MessageListResponse)
async def list_messages(
    conversation_id: str,
    current_user: CurrentUser,
    limit: int = Query(30, ge=1, le=100),
    before_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
) -> MessageListResponse:
    """List messages in a conversation with cursor-based pagination."""
    service = MessengerService(db, current_user)
    messages, has_more = await service.get_messages(
        conversation_id, limit=limit, before_id=before_id
    )
    return MessageListResponse(
        messages=[MessageSchema.model_validate(m) for m in messages],
        has_more=has_more,
        cursor=messages[0].id if messages and has_more else None,
    )


@router.post(
    "/conversations/{conversation_id}/messages/text",
    response_model=MessageSchema,
    status_code=201,
)
async def send_text_message(
    conversation_id: str,
    request_data,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> MessageSchema:
    """Send an encrypted text message."""
    from app.domain.schemas.messenger import SendTextMessageRequest

    service = MessengerService(db, current_user)
    message = await service.send_text_message(conversation_id, request_data)
    return MessageSchema.model_validate(message)


@router.post(
    "/conversations/{conversation_id}/messages/location",
    response_model=MessageSchema,
    status_code=201,
)
async def send_location(
    conversation_id: str,
    request_data,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> MessageSchema:
    """Send a location pin."""
    from app.domain.schemas.messenger import SendLocationMessageRequest

    service = MessengerService(db, current_user)
    message = await service.send_location_message(conversation_id, request_data)
    return MessageSchema.model_validate(message)


@router.post(
    "/conversations/{conversation_id}/messages/media",
    response_model=MessageSchema,
    status_code=201,
)
async def upload_media(
    conversation_id: str,
    current_user: CurrentUser,
    file: UploadFile = File(...),
    message_type: MessageType = Query(...),
    db: AsyncSession = Depends(get_db),
) -> MessageSchema:
    """Upload and send a media file (image/voice/file)."""
    # Validate content type
    allowed = {
        MessageType.IMAGE: settings.ALLOWED_IMAGE_TYPES,
        MessageType.VOICE: settings.ALLOWED_AUDIO_TYPES,
        MessageType.FILE: None,  # Any type allowed for generic files
    }
    allowed_types = allowed.get(message_type)
    if allowed_types and file.content_type not in allowed_types:
        raise UnsupportedFileTypeException(
            f"File type {file.content_type} not allowed for {message_type.value} messages"
        )

    file_data = await file.read()
    service = MessengerService(db, current_user)
    message = await service.upload_media(
        conversation_id=conversation_id,
        file_data=file_data,
        filename=file.filename or "upload",
        content_type=file.content_type or "application/octet-stream",
        message_type=message_type,
    )
    return MessageSchema.model_validate(message)


@router.delete("/messages/{message_id}", status_code=204)
async def delete_message(
    message_id: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a message (soft delete)."""
    service = MessengerService(db, current_user)
    await service.delete_message(message_id)


@router.post("/conversations/{conversation_id}/read/{message_id}", status_code=204)
async def mark_read(
    conversation_id: str,
    message_id: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Mark messages as read up to the specified message."""
    service = MessengerService(db, current_user)
    await service.mark_as_read(conversation_id, message_id)
