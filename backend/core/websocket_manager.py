"""
Centralized WebSocket Manager for AegisOps.
Handles client connection lifecycles, keepalives, and broadcasts:
- New Metrics (METRICS_UPDATE)
- New Alerts & Alert Resolutions (NEW_ALERT, ALERT_RESOLVED)
- Incident Updates (INCIDENT_UPDATE)
- Service Status Changes (SERVICE_STATUS_CHANGE)
"""

import asyncio
from datetime import datetime, timezone
import json
import logging
from typing import Any, Dict, Optional, Set
from fastapi import WebSocket

logger = logging.getLogger("aegisops.backend.websocket_manager")


class ConnectionManager:
    """
    Manages active dashboard WebSocket connections and dispatches real-time events.
    """

    def __init__(self):
        self._active_connections: Set[WebSocket] = set()
        self._lock = asyncio.Lock()

    @property
    def client_count(self) -> int:
        return len(self._active_connections)

    async def connect(self, websocket: WebSocket) -> None:
        """Accepts and registers a new WebSocket client."""
        await websocket.accept()
        async with self._lock:
            self._active_connections.add(websocket)
        logger.info("Client connected to WS /ws/monitor. Active clients: %d", len(self._active_connections))

    async def disconnect(self, websocket: WebSocket) -> None:
        """Unregisters a disconnected WebSocket client."""
        async with self._lock:
            self._active_connections.discard(websocket)
        logger.info("Client disconnected from WS /ws/monitor. Active clients: %d", len(self._active_connections))

    async def broadcast_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        """Broadcasts a typed JSON payload to all connected clients."""
        if not self._active_connections:
            return

        message: Dict[str, Any] = {
            "type": event_type,
            "data": payload,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Expose top-level fields for direct convenience (e.g. {"type": "incident_created", "incident_id": 101})
        if isinstance(payload, dict):
            if "incident_id" in payload:
                clean_id = str(payload["incident_id"]).replace("INC-", "")
                message["incident_id"] = int(clean_id) if clean_id.isdigit() else payload["incident_id"]
            elif "id" in payload and any(sub in event_type.lower() for sub in ["incident", "inc"]):
                clean_id = str(payload["id"]).replace("INC-", "")
                message["incident_id"] = int(clean_id) if clean_id.isdigit() else payload["id"]

            if "alert_id" in payload:
                clean_id = str(payload["alert_id"]).replace("ALT-", "")
                message["alert_id"] = int(clean_id) if clean_id.isdigit() else payload["alert_id"]
            elif "id" in payload and any(sub in event_type.lower() for sub in ["alert", "alt"]):
                clean_id = str(payload["id"]).replace("ALT-", "")
                message["alert_id"] = int(clean_id) if clean_id.isdigit() else payload["id"]

            if "severity" in payload:
                message["severity"] = payload["severity"]
            if "title" in payload:
                message["title"] = payload["title"]

        # Serialized JSON string
        raw_message = json.dumps(message, default=str)
        dead_connections = []

        async with self._lock:
            active_copy = list(self._active_connections)

        for connection in active_copy:
            try:
                await connection.send_text(raw_message)
            except Exception as err:
                logger.debug("Failed to send message to client, marking for removal: %s", err)
                dead_connections.append(connection)

        if dead_connections:
            async with self._lock:
                for dead in dead_connections:
                    self._active_connections.discard(dead)

    async def broadcast_metrics(self, telemetry: Any) -> None:
        """Broadcasts real-time host telemetry snapshot."""
        data = telemetry.model_dump(mode="json") if hasattr(telemetry, "model_dump") else telemetry
        await self.broadcast_event("METRICS_UPDATE", data)

    async def broadcast_new_alert(self, alert_data: Dict[str, Any]) -> None:
        """Broadcasts a new threshold breach alert (type: new_alert)."""
        await self.broadcast_event("new_alert", alert_data)

    async def broadcast_alert(self, alert_data: Dict[str, Any], event_type: str = "NEW_ALERT") -> None:
        """Broadcasts threshold alert event (NEW_ALERT, new_alert, or ALERT_RESOLVED)."""
        await self.broadcast_event(event_type, alert_data)

    async def broadcast_incident_created(self, incident_data: Dict[str, Any]) -> None:
        """Broadcasts new incident creation (type: incident_created)."""
        await self.broadcast_event("incident_created", incident_data)

    async def broadcast_incident_updated(self, incident_data: Dict[str, Any]) -> None:
        """Broadcasts incident modification/update (type: incident_updated)."""
        await self.broadcast_event("incident_updated", incident_data)

    async def broadcast_incident_resolved(self, incident_data: Dict[str, Any]) -> None:
        """Broadcasts incident resolution (type: incident_resolved)."""
        await self.broadcast_event("incident_resolved", incident_data)

    async def broadcast_incident(self, incident_data: Dict[str, Any], event_type: str = "INCIDENT_UPDATE") -> None:
        """Broadcasts incident lifecycle change."""
        await self.broadcast_event(event_type, incident_data)

    async def broadcast_service_status(
        self,
        service_name: str,
        status: str,
        service_id: Optional[int] = None,
        details: Optional[str] = None,
    ) -> None:
        """Broadcasts service status change."""
        payload = {
            "service_id": service_id,
            "service_name": service_name,
            "status": status,
            "details": details or f"Service {service_name} status updated to {status}",
        }
        await self.broadcast_event("SERVICE_STATUS_CHANGE", payload)


# Global WebSocket manager singleton
ws_manager = ConnectionManager()
