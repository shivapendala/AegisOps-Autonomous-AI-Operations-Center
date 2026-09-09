"""
WebSocket Real-time Telemetry and Alert Streaming.
Broadcasts live host metrics, scikit-learn anomaly evaluations,
and autonomous alerts to connected frontend dashboards.
"""

import asyncio
import json
import logging
from typing import Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from aegisops.ai.anomaly_detector import AnomalyDetector
from monitoring.collector import SystemCollector

logger = logging.getLogger("aegisops.backend.ws")

router = APIRouter(tags=["WebSocket"])


class ConnectionManager:
    """Manages active dashboard WebSocket client connections."""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info("New dashboard client connected. Total clients: %d", len(self.active_connections))

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
        logger.info("Dashboard client disconnected. Remaining clients: %d", len(self.active_connections))

    async def broadcast_json(self, message: dict):
        disconnected = []
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)

        for conn in disconnected:
            self.active_connections.discard(conn)


manager = ConnectionManager()
collector = SystemCollector()
detector = AnomalyDetector()


@router.websocket("/ws/telemetry")
async def websocket_telemetry_endpoint(websocket: WebSocket):
    """
    Continuous bidirectional WebSocket connection.
    Pushes live host telemetry and anomaly evaluation to the frontend.
    """
    await manager.connect(websocket)
    try:
        while True:
            # Check for incoming client messages with a 2-second timeout
            try:
                client_msg = await asyncio.wait_for(websocket.receive_text(), timeout=2.0)
                # Handle client ping or command
                if client_msg == "ping":
                    await websocket.send_text("pong")
            except asyncio.TimeoutError:
                # Regular broadcast tick
                pass

            telemetry = collector.collect()
            anomaly = detector.evaluate_telemetry(telemetry)

            payload = {
                "type": "TELEMETRY_UPDATE",
                "telemetry": telemetry.model_dump(mode="json"),
                "anomaly": anomaly.model_dump(mode="json"),
            }
            await websocket.send_json(payload)

    except (WebSocketDisconnect, ConnectionResetError):
        manager.disconnect(websocket)
    except Exception as exc:
        logger.error("WebSocket session error: %s", exc)
        manager.disconnect(websocket)
