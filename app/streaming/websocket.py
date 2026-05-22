"""
WebSocket Real-Time Streaming Handler
Provides live streaming of radio events to connected listeners
"""
import logging
import json
from datetime import datetime
from typing import Set, Dict, Any

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for broadcasting"""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.connection_metadata: Dict[WebSocket, Dict[str, Any]] = {}

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

    async def broadcast_track_update(
        self, track: Dict[str, Any], event_type: str = "track_changed"
    ) -> None:
        """Broadcast track update to all listeners"""
        message = {
            "type": event_type,
            "track": track,
            "timestamp": datetime.utcnow().isoformat(),
            "listener_count": len(self.active_connections),
        }
        await self.broadcast(message)

    async def broadcast_dj_message(self, text: str) -> None:
        """Broadcast AI DJ message"""
        message = {
            "type": "dj_message",
            "text": text,
            "timestamp": datetime.utcnow().isoformat(),
            "listener_count": len(self.active_connections),
        }
        await self.broadcast(message)

    async def broadcast_status(self, status: Dict[str, Any]) -> None:
        """Broadcast system status update"""
        message = {
            "type": "status",
            "data": status,
            "timestamp": datetime.utcnow().isoformat(),
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
            message = json.loads(data)

            # Handle different message types
            if message.get("type") == "ping":
                await ws_manager.send_personal_message(
                    {"type": "pong", "timestamp": datetime.utcnow().isoformat()},
                    websocket,
                )
            elif message.get("type") == "chat":
                # Broadcast chat message
                await ws_manager.broadcast({
                    "type": "chat",
                    "client_id": client_id,
                    "text": message.get("text", ""),
                    "timestamp": datetime.utcnow().isoformat(),
                })
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
