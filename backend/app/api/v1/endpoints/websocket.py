"""
SEPEHR Backend — WebSocket API Endpoint
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, WebSocket
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.session import get_db
from app.infrastructure.websocket.manager import ws_manager

router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(..., description="JWT access token"),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    WebSocket connection endpoint.
    
    Connect with: ws://host/ws?token=<access_token>
    
    Message types (server → client):
    - connected: connection confirmation
    - ping: heartbeat
    - new_message: new chat message received
    - typing: typing indicator
    - read_receipt: message read status update
    - emergency_alert: system-wide emergency notification
    - error: error notification
    
    Message types (client → server):
    - pong: heartbeat response
    - typing: { conversation_id }
    - read_receipt: { message_id, conversation_id }
    """
    from app.api.v1.dependencies.auth import get_ws_user

    try:
        user = await get_ws_user(websocket, token, db)
    except Exception:
        return

    await ws_manager.handle_connection(
        websocket=websocket,
        user_id=user.id,
        user_role=user.role.value,
    )
