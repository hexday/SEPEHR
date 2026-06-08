"""
SEPEHR Backend — WebSocket Gateway
Handles real-time messaging, presence, and notifications.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

from app.core.config import settings
from app.infrastructure.cache.redis import get_redis, presence

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages WebSocket connections across the application.
    Supports pub/sub via Redis for multi-process deployment.
    """

    def __init__(self) -> None:
        # user_id -> set of WebSocket connections
        self._connections: dict[str, set[WebSocket]] = defaultdict(set)
        # conversation_id -> set of user_ids currently connected
        self._conversation_listeners: dict[str, set[str]] = defaultdict(set)

    async def connect(self, websocket: WebSocket, user_id: str) -> None:
        await websocket.accept()
        self._connections[user_id].add(websocket)
        await presence.set_online(user_id)
        logger.info(f"WS connected: user={user_id}, total_connections={self._total_connections}")

    async def disconnect(self, websocket: WebSocket, user_id: str) -> None:
        self._connections[user_id].discard(websocket)
        if not self._connections[user_id]:
            del self._connections[user_id]
            await presence.set_offline(user_id)
        logger.info(f"WS disconnected: user={user_id}")

    @property
    def _total_connections(self) -> int:
        return sum(len(conns) for conns in self._connections.values())

    def is_connected(self, user_id: str) -> bool:
        return user_id in self._connections and bool(self._connections[user_id])

    async def send_to_user(self, user_id: str, payload: dict[str, Any]) -> bool:
        """Send a message to all connections of a user. Returns True if sent."""
        connections = self._connections.get(user_id, set())
        if not connections:
            return False

        message = json.dumps(payload)
        dead: list[WebSocket] = []

        for ws in connections:
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)

        for ws in dead:
            connections.discard(ws)

        return bool(connections)

    async def broadcast_to_users(
        self, user_ids: list[str], payload: dict[str, Any]
    ) -> None:
        """Send to multiple users concurrently."""
        tasks = [self.send_to_user(uid, payload) for uid in user_ids]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def handle_connection(
        self,
        websocket: WebSocket,
        user_id: str,
        user_role: str,
    ) -> None:
        """Main handler for a WebSocket connection lifecycle."""
        await self.connect(websocket, user_id)

        # Send connection confirmation
        await self.send_to_user(
            user_id,
            {
                "type": "connected",
                "payload": {
                    "user_id": user_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            },
        )

        heartbeat_task = asyncio.create_task(self._heartbeat_loop(websocket, user_id))

        try:
            while True:
                raw = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=settings.WS_HEARTBEAT_INTERVAL * 2,
                )
                try:
                    data = json.loads(raw)
                    await self._handle_client_message(user_id, data)
                except json.JSONDecodeError:
                    await self.send_to_user(
                        user_id,
                        {"type": "error", "payload": {"message": "Invalid JSON"}},
                    )

        except (WebSocketDisconnect, asyncio.TimeoutError):
            pass
        except Exception as e:
            logger.error(f"WS error for user {user_id}: {e}")
        finally:
            heartbeat_task.cancel()
            await self.disconnect(websocket, user_id)

    async def _heartbeat_loop(self, websocket: WebSocket, user_id: str) -> None:
        """Send periodic pings to keep connection alive and refresh presence."""
        while True:
            await asyncio.sleep(settings.WS_HEARTBEAT_INTERVAL)
            try:
                await websocket.send_text(json.dumps({"type": "ping"}))
                await presence.heartbeat(user_id)
            except Exception:
                break

    async def _handle_client_message(
        self, user_id: str, data: dict[str, Any]
    ) -> None:
        """Handle incoming messages from WebSocket clients."""
        msg_type = data.get("type")

        if msg_type == "pong":
            # Heartbeat response
            return

        elif msg_type == "typing":
            conversation_id = data.get("payload", {}).get("conversation_id")
            if conversation_id:
                await self._broadcast_typing(user_id, conversation_id)

        elif msg_type == "read_receipt":
            message_id = data.get("payload", {}).get("message_id")
            conversation_id = data.get("payload", {}).get("conversation_id")
            if message_id and conversation_id:
                await self._broadcast_read_receipt(user_id, message_id, conversation_id)

        else:
            logger.debug(f"Unknown WS message type: {msg_type} from user {user_id}")

    async def _broadcast_typing(
        self, sender_id: str, conversation_id: str
    ) -> None:
        """Broadcast typing indicator to conversation members."""
        # This would normally load members from DB/cache
        # For now, emit via Redis pub/sub for inter-process coordination
        redis = await get_redis()
        payload = json.dumps(
            {
                "type": "typing",
                "payload": {
                    "user_id": sender_id,
                    "conversation_id": conversation_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            }
        )
        await redis.publish(f"conv:{conversation_id}", payload)

    async def _broadcast_read_receipt(
        self, reader_id: str, message_id: str, conversation_id: str
    ) -> None:
        """Broadcast read receipt to conversation members."""
        redis = await get_redis()
        payload = json.dumps(
            {
                "type": "read_receipt",
                "payload": {
                    "reader_id": reader_id,
                    "message_id": message_id,
                    "conversation_id": conversation_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            }
        )
        await redis.publish(f"conv:{conversation_id}", payload)

    async def notify_new_message(
        self,
        conversation_id: str,
        message_data: dict[str, Any],
        member_ids: list[str],
    ) -> None:
        """Push a new message notification to all online members."""
        payload = {
            "type": "new_message",
            "payload": {
                "conversation_id": conversation_id,
                "message": message_data,
            },
        }
        await self.broadcast_to_users(member_ids, payload)

    async def notify_alert(self, alert_data: dict[str, Any]) -> None:
        """Broadcast emergency alert to ALL connected users."""
        payload = {"type": "emergency_alert", "payload": alert_data}
        message = json.dumps(payload)
        for user_id, connections in self._connections.items():
            for ws in connections:
                try:
                    await ws.send_text(message)
                except Exception:
                    pass


# Global connection manager instance
ws_manager = ConnectionManager()
