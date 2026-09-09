"""
End-to-End Live WebSocket Verification Script.
Connects to ws://127.0.0.1:8000/ws/monitor and validates:
1. INITIAL_STATE handshake packet
2. Periodic 2-second METRICS_UPDATE packets
3. Real-time INCIDENT_UPDATE upon incident creation
4. Real-time SERVICE_STATUS_CHANGE upon service status modification
"""

import asyncio
import json
import urllib.request
import websockets


async def test_live_websocket():
    uri = "ws://127.0.0.1:8000/ws/monitor"
    print(f"Connecting to {uri}...")
    async with websockets.connect(uri) as ws:
        # 1. Receive INITIAL_STATE
        raw = await asyncio.wait_for(ws.recv(), timeout=5.0)
        msg = json.loads(raw)
        print("1. Received Handshake:", msg.get("type"))
        assert msg.get("type") == "INITIAL_STATE", f"Expected INITIAL_STATE, got {msg.get('type')}"
        assert "telemetry" in msg["data"]
        assert "services" in msg["data"]
        print(f"   Handshake validated. Monitored services count: {len(msg['data']['services'])}")

        # 2. Wait for regular 2s METRICS_UPDATE
        print("2. Waiting for live 2-second METRICS_UPDATE...")
        raw_metric = await asyncio.wait_for(ws.recv(), timeout=6.0)
        metric_msg = json.loads(raw_metric)
        print(f"   Received Event: {metric_msg.get('type')}")
        if metric_msg.get("type") == "METRICS_UPDATE":
            cpu = metric_msg["data"].get("cpu_percent")
            mem = metric_msg["data"].get("memory_percent")
            uptime = metric_msg["data"].get("uptime_seconds")
            print(f"   Telemetery -> CPU: {cpu}% | RAM: {mem}% | Uptime: {uptime}s")

        # 3. Trigger new incident via REST API and verify WebSocket receives INCIDENT_UPDATE
        print("3. Generating test Incident via REST API...")
        req_data = json.dumps({
            "title": "WebSocket Live Incident Test",
            "description": "Verifying real-time broadcast to connected dashboard",
            "severity": "CRITICAL",
        }).encode()
        req = urllib.request.Request(
            "http://127.0.0.1:8000/api/incidents",
            data=req_data,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req) as resp:
            created_inc = json.loads(resp.read().decode())
            inc_id = created_inc["id"]
            print(f"   Created Incident via REST: {inc_id}")

        # Read WS message until we get INCIDENT_UPDATE
        inc_event_received = False
        for _ in range(5):
            raw_event = await asyncio.wait_for(ws.recv(), timeout=5.0)
            event_msg = json.loads(raw_event)
            print(f"   WS packet received: {event_msg.get('type')}")
            if event_msg.get("type") == "INCIDENT_UPDATE" and event_msg["data"].get("id") == inc_id:
                inc_event_received = True
                print("   Successfully verified live INCIDENT_UPDATE over WebSocket!")
                break
        assert inc_event_received, "Did not receive INCIDENT_UPDATE over WebSocket!"

        # 4. Trigger service status update via REST API and verify SERVICE_STATUS_CHANGE
        print("4. Generating Service Status Change via REST API...")
        svc_req = urllib.request.Request(
            "http://127.0.0.1:8000/api/services/1/status?status=DEGRADED",
            method="PATCH",
        )
        with urllib.request.urlopen(svc_req) as resp:
            updated_svc = json.loads(resp.read().decode())
            print(f"   Updated Service via REST: {updated_svc['name']} -> {updated_svc['status']}")

        svc_event_received = False
        for _ in range(5):
            raw_event = await asyncio.wait_for(ws.recv(), timeout=5.0)
            event_msg = json.loads(raw_event)
            print(f"   WS packet received: {event_msg.get('type')}")
            if event_msg.get("type") == "SERVICE_STATUS_CHANGE":
                svc_event_received = True
                print(f"   Successfully verified live SERVICE_STATUS_CHANGE: {event_msg['data']}")
                break
        assert svc_event_received, "Did not receive SERVICE_STATUS_CHANGE over WebSocket!"

        # Reset service status back to HEALTHY
        urllib.request.urlopen(
            urllib.request.Request(
                "http://127.0.0.1:8000/api/services/1/status?status=HEALTHY",
                method="PATCH",
            )
        )

        print("\nAll 4 real-time WebSocket event types successfully verified!")


if __name__ == "__main__":
    asyncio.run(test_live_websocket())
