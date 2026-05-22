"""
WebSocket Real-Time Streaming Handler
Provides live streaming of radio events to connected listeners
"""
import logging
import json
from datetime import datetime
from typing import Set, Dict, Any

from fastapi import WebSocket, WebSocketDisconnect
import json as _json
from app.core.state_engine import state_engine

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for broadcasting"""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.connection_metadata: Dict[WebSocket, Dict[str, Any]] = {}
        self.recent_chats: List[Dict[str, Any]] = []

    async def connect(self, websocket: WebSocket, client_id: str = "") -> None:
        """Register a new WebSocket connection"""
        await websocket.accept()
        self.active_connections.add(websocket)
        self.connection_metadata[websocket] = {
            "client_id": client_id,
            "connected_at": datetime.utcnow().isoformat(),
        }
        logger.info(f"Client connected: {client_id} (total: {len(self.active_connections)})")

    def disconnect(self, websocket: WebSocket) -> None:
        """Unregister a WebSocket connection"""
        self.active_connections.discard(websocket)
        metadata = self.connection_metadata.pop(websocket, {})
        client_id = metadata.get("client_id", "unknown")
        logger.info(
            f"Client disconnected: {client_id} (total: {len(self.active_connections)})"
        )

    async def broadcast(self, message: Dict[str, Any]) -> None:
        """Broadcast message to all connected clients"""
        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Failed to send message: {e}")
                disconnected.add(connection)

        # Clean up disconnected clients
        for conn in disconnected:
            self.disconnect(conn)

    def add_chat(self, chat: Dict[str, Any]) -> None:
        """Store recent chat messages in-memory for quick consumption by director/AI."""
        try:
            self.recent_chats.insert(0, chat)
            # Keep last 100
            self.recent_chats = self.recent_chats[:100]
        except Exception:
            pass

    def get_recent_chats(self, limit: int = 10) -> List[Dict[str, Any]]:
        return list(self.recent_chats[:limit])

    async def broadcast_track_update(
        self, track: Dict[str, Any], event_type: str = "track_changed"
    ) -> None:
        """Broadcast track update to all listeners"""
        await self.broadcast_event("music", {"event": event_type, "track": track})

    async def broadcast_dj_message(self, text: str) -> None:
        """Broadcast AI DJ message"""
        await self.broadcast_event("ai_speech", {"text": text})

    async def broadcast_status(self, status: Dict[str, Any]) -> None:
        """Broadcast system status update"""
        await self.broadcast_event("announcement", {"status": status})

    async def broadcast_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        """Broadcast unified event format to all listeners.

        Event format:
        {"type": "ai_speech|music|announcement|chat", "timestamp": "...", "payload": {...}}
        """
        message = {
            "type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "payload": payload,
            "listener_count": len(self.active_connections),
        }
        await self.broadcast(message)

    async def send_personal_message(
        self, message: Dict[str, Any], websocket: WebSocket
    ) -> None:
        """Send message to specific connection"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Failed to send personal message: {e}")
            self.disconnect(websocket)

    def get_listener_count(self) -> int:
        """Get number of active listeners"""
        return len(self.active_connections)

    async def get_status(self) -> Dict[str, Any]:
        """Get connection manager status"""
        return {
            "active_listeners": self.get_listener_count(),
            "connections": list(
                {
                    "client_id": meta.get("client_id"),
                    "connected_at": meta.get("connected_at"),
                }
                for meta in self.connection_metadata.values()
            ),
        }


# Global connection manager instance
ws_manager = ConnectionManager()


async def handle_ws_connection(websocket: WebSocket) -> None:
    """
    Main WebSocket handler - manages connection lifecycle
    
    Expected message format from client:
    {
        "type": "connect",  # "connect", "disconnect", "chat"
        "data": {...}
    }
    """
    client_id = f"client_{len(ws_manager.active_connections)}"
    try:
        await ws_manager.connect(websocket, client_id)

        # Send initial connection message
        await ws_manager.send_personal_message(
            {
                "type": "connection_established",
                "client_id": client_id,
                "timestamp": datetime.utcnow().isoformat(),
            },
            websocket,
        )

        # Listen for incoming messages
        while True:
            data = await websocket.receive_text()
            message = _json.loads(data)

            # Handle different message types
            if message.get("type") == "ping":
                await ws_manager.send_personal_message(
                    {"type": "pong", "timestamp": datetime.utcnow().isoformat()},
                    websocket,
                )
            elif message.get("type") == "chat":
                chat_payload = {
                    "client_id": client_id,
                    "text": message.get("text", ""),
                    "timestamp": datetime.utcnow().isoformat(),
                }

                # Store chat locally for director/AI consumption and broadcast
                ws_manager.add_chat(chat_payload)
                await ws_manager.broadcast_event("chat", chat_payload)

            elif message.get("type") == "status_request":
                # Send status to requester
                await ws_manager.send_personal_message(
                    {
                        "type": "status",
                        "data": await ws_manager.get_status(),
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                    websocket,
                )
            else:
                logger.debug(f"Unknown message type: {message.get('type')}")

    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        ws_manager.disconnect(websocket)
