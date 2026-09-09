"""
WebSocket Real-time Telemetry and Event Streaming Routes.
Exposes:
- WS /ws/monitor: Primary monitoring stream for metrics, alerts, incidents, and services.
- WS /ws/telemetry: Compatibility alias.
"""

import asyncio
import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.core.websocket_manager import ws_manager
from database.models.alert import AlertModel
from database.models.service import ServiceModel
from database.session import SessionLocal
from monitoring.collector import SystemCollector

logger = logging.getLogger("aegisops.backend.ws")

router = APIRouter(tags=["WebSocket"])
collector = SystemCollector()


async def _handle_monitoring_socket(websocket: WebSocket):
    """Handles an active monitoring WebSocket connection session."""
    await ws_manager.connect(websocket)
    try:
        # Send initial state snapshot on connection
        telemetry = collector.collect()
        db = SessionLocal()
        try:
            active_alerts = (
                db.query(AlertModel)
                .filter(AlertModel.status == "ACTIVE")
                .order_by(AlertModel.timestamp.desc())
                .limit(20)
                .all()
            )
            services = db.query(ServiceModel).all()
            initial_state = {
                "type": "INITIAL_STATE",
                "data": {
                    "telemetry": telemetry.model_dump(mode="json"),
                    "active_alerts": [a.to_dict() for a in active_alerts],
                    "services": [s.to_dict() for s in services],
                },
            }
            await websocket.send_text(json.dumps(initial_state, default=str))
        finally:
            db.close()

        # Listen for client messages / keepalives
        while True:
            try:
                msg = await websocket.receive_text()
                if msg == "ping":
                    await websocket.send_text(json.dumps({"type": "PONG"}))
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.debug("Client receive loop error: %s", e)
                break

    finally:
        await ws_manager.disconnect(websocket)


@router.websocket("/ws/monitor")
async def websocket_monitor_endpoint(websocket: WebSocket):
    """
    Primary real-time stream endpoint.
    Broadcasts metrics, alerts, incidents, and service updates.
    """
    await _handle_monitoring_socket(websocket)


@router.websocket("/ws/telemetry")
async def websocket_telemetry_endpoint(websocket: WebSocket):
    """Compatibility alias endpoint for /ws/monitor."""
    await _handle_monitoring_socket(websocket)
