"""
Unit & Integration Tests for AegisOps Real-Time WebSocket Channel (WS /ws/monitor).
Verifies:
- Client connection and INITIAL_STATE handshake
- Heartbeat ping / pong
- Broadcasting METRICS_UPDATE
- Broadcasting NEW_ALERT and ALERT_RESOLVED
- Broadcasting INCIDENT_UPDATE
- Broadcasting SERVICE_STATUS_CHANGE
"""

import asyncio
import json
import pytest
from fastapi.testclient import TestClient

from backend.core.websocket_manager import ws_manager
from backend.main import app
from database.init_db import seed_initial_data


def test_websocket_connection_and_initial_handshake(client, db_session):
    seed_initial_data(db_session)
    with client.websocket_connect("/ws/monitor") as websocket:
        # 1. Receive initial state handshake
        raw_msg = websocket.receive_text()
        msg = json.loads(raw_msg)
        assert msg["type"] == "INITIAL_STATE"
        data = msg["data"]
        assert "telemetry" in data
        assert "active_alerts" in data
        assert "services" in data
        assert len(data["services"]) > 0

        # 2. Ping-pong keepalive
        websocket.send_text("ping")
        resp = json.loads(websocket.receive_text())
        assert resp["type"] == "PONG"


def test_websocket_broadcast_events(client, db_session):
    seed_initial_data(db_session)
    with client.websocket_connect("/ws/monitor") as websocket:
        # Discard initial handshake
        _ = websocket.receive_text()

        # 1. Broadcast METRICS_UPDATE
        asyncio.run(
            ws_manager.broadcast_event(
                "METRICS_UPDATE",
                {
                    "cpu_percent": 82.5,
                    "memory_percent": 74.0,
                    "disk_percent": 65.0,
                    "process_count": 210,
                    "uptime_seconds": 5400.0,
                },
            )
        )
        msg1 = json.loads(websocket.receive_text())
        assert msg1["type"] == "METRICS_UPDATE"
        assert msg1["data"]["cpu_percent"] == 82.5
        assert msg1["data"]["uptime_seconds"] == 5400.0

        # 2. Broadcast NEW_ALERT
        asyncio.run(
            ws_manager.broadcast_alert(
                {
                    "id": "ALT-TEST-1",
                    "service": "api-gateway",
                    "metric": "cpu_usage",
                    "value": 82.5,
                    "threshold": 70.0,
                    "severity": "WARNING",
                    "message": "High CPU warning",
                    "status": "ACTIVE",
                },
                "NEW_ALERT",
            )
        )
        msg2 = json.loads(websocket.receive_text())
        assert msg2["type"] == "NEW_ALERT"
        assert msg2["data"]["id"] == "ALT-TEST-1"
        assert msg2["data"]["severity"] == "WARNING"

        # 3. Broadcast ALERT_RESOLVED
        asyncio.run(
            ws_manager.broadcast_alert(
                {
                    "id": "ALT-TEST-1",
                    "service": "api-gateway",
                    "metric": "cpu_usage",
                    "status": "RESOLVED",
                },
                "ALERT_RESOLVED",
            )
        )
        msg3 = json.loads(websocket.receive_text())
        assert msg3["type"] == "ALERT_RESOLVED"
        assert msg3["data"]["status"] == "RESOLVED"

        # 4. Broadcast INCIDENT_UPDATE
        asyncio.run(
            ws_manager.broadcast_incident(
                {
                    "id": "INC-TEST-99",
                    "title": "Simulated Ingress Timeout",
                    "severity": "CRITICAL",
                    "status": "INVESTIGATING",
                }
            )
        )
        msg4 = json.loads(websocket.receive_text())
        assert msg4["type"] == "INCIDENT_UPDATE"
        assert msg4["data"]["id"] == "INC-TEST-99"

        # 5. Broadcast SERVICE_STATUS_CHANGE
        asyncio.run(
            ws_manager.broadcast_service_status(
                service_name="payment-processor",
                status="DEGRADED",
                service_id=3,
            )
        )
        msg5 = json.loads(websocket.receive_text())
        assert msg5["type"] == "SERVICE_STATUS_CHANGE"
        assert msg5["data"]["service_name"] == "payment-processor"
        assert msg5["data"]["status"] == "DEGRADED"
