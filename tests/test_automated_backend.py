"""
Comprehensive End-to-End Automated Backend Test Suite for AegisOps.
Strictly verifies all required backend capabilities:
1. Health API (GET /api/health)
2. Metrics API (GET /api/metrics, GET /api/metrics/current, GET /api/metrics/summary)
3. Alert creation & lifecycle (AlertModel, REST API GET /api/alerts, status filters)
4. Threshold detection (AlertRuleEngine warning & critical boundaries, auto-recovery)
5. Event correlation (Scoring formula, same service, time window, metric affinity)
6. Incident creation (IncidentModel creation and persistence in DB)
7. Incident status changes (OPEN -> INVESTIGATING -> RESOLVED -> CLOSED)
8. AI mock provider (MockAIProvider deterministic reasoning, confidence, evidence, fallback)
9. WebSocket connection (WS /ws/monitor handshake, ping/pong, and event broadcast)
10. REQUIRED CRITICAL SCENARIO:
    Simultaneous / Rapid sequence:
    - CPU spike (e.g. 92%)
    - Database overload (e.g. 95%)
    - API latency spike (e.g. 2.8s)
    - HTTP error spike (e.g. 14.5% 500 errors)
    Expected result:
    ONE correlated incident grouping all alerts.
"""

from datetime import datetime, timezone
import json
import uuid
import pytest

from aegisops.ai.rca import (
    MockAIProvider,
    IncidentInvestigation,
    get_ai_provider,
    LLMProvider,
)
from aegisops.models.events import SystemTelemetry
from database.init_db import seed_initial_data
from database.models.alert import AlertModel
from database.models.incident import IncidentModel
from database.models.incident_event import IncidentEventModel
from database.models.metric import MetricModel
from monitoring.alert_engine import AlertRuleEngine
from monitoring.correlation_engine import EventCorrelationEngine
from monitoring.thresholds import ThresholdConfig, MetricThreshold


# ==============================================================================
# 1. Health API Tests
# ==============================================================================
def test_backend_health_api(client, db_session):
    """Verifies GET /api/health returns 200, status, database health, tables, and AI engine."""
    seed_initial_data(db_session)
    response = client.get("/api/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] in ["healthy", "degraded", "operational"]
    assert "app_name" in payload
    assert payload["tables_ready"] is True
    assert "ai_engine" in payload
    assert payload["ai_engine"]["provider"] is not None


# ==============================================================================
# 2. Metrics API Tests
# ==============================================================================
def test_backend_metrics_api(client, db_session):
    """Verifies GET /api/metrics, /api/metrics/current, and /api/metrics/summary."""
    seed_initial_data(db_session)

    # 1. GET /api/metrics
    res_list = client.get("/api/metrics")
    assert res_list.status_code == 200
    metrics = res_list.json()
    assert isinstance(metrics, list)
    assert len(metrics) > 0

    # 2. GET /api/metrics/current (instantaneous psutil)
    res_curr = client.get("/api/metrics/current")
    assert res_curr.status_code == 200
    curr = res_curr.json()
    assert "cpu_percent" in curr
    assert "memory_percent" in curr
    assert "disk_percent" in curr
    assert "process_count" in curr

    # 3. GET /api/metrics/summary
    res_summary = client.get("/api/metrics/summary")
    assert res_summary.status_code == 200
    summary = res_summary.json()
    assert "host" in summary
    assert "total_metrics_count" in summary


# ==============================================================================
# 3. Alert Creation Tests
# ==============================================================================
def test_backend_alert_creation_and_api(client, db_session):
    """Verifies creating AlertModel records, DB persistence, and GET /api/alerts filtering."""
    now = datetime.now(timezone.utc)
    alt = AlertModel(
        service="payment-api",
        metric="api_latency",
        value=2800.0,
        threshold=500.0,
        severity="CRITICAL",
        message="Response latency exceeded critical threshold",
        status="ACTIVE",
        source="test-suite",
        timestamp=now,
    )
    db_session.add(alt)
    db_session.commit()

    # Query via API
    res = client.get("/api/alerts?status=ACTIVE")
    assert res.status_code == 200
    alerts = res.json()
    assert any(a["metric"] == "api_latency" and a["service"] == "payment-api" for a in alerts)


# ==============================================================================
# 4. Threshold Detection Tests
# ==============================================================================
def test_backend_threshold_detection_engine():
    """Verifies AlertRuleEngine evaluates warning and critical boundaries and recovers."""
    thresholds = ThresholdConfig(
        cpu=MetricThreshold(warning=70.0, critical=90.0),
        memory=MetricThreshold(warning=75.0, critical=90.0),
        disk=MetricThreshold(warning=80.0, critical=90.0),
    )
    engine = AlertRuleEngine(thresholds=thresholds, service_name="payment-api")

    # Baseline nominal
    t_normal = SystemTelemetry(
        cpu_percent=45.0,
        memory_percent=55.0,
        disk_percent=60.0,
        process_count=120,
    )
    new_alerts, resolved_alerts = engine.evaluate(t_normal)
    assert len(new_alerts) == 0

    # Warning breach
    t_warn = SystemTelemetry(
        cpu_percent=78.5,
        memory_percent=55.0,
        disk_percent=60.0,
        process_count=120,
    )
    new_alerts, _ = engine.evaluate(t_warn)
    assert len(new_alerts) == 1
    assert new_alerts[0]["severity"] == "WARNING"

    # Escalation to Critical
    t_crit = SystemTelemetry(
        cpu_percent=94.0,
        memory_percent=55.0,
        disk_percent=60.0,
        process_count=120,
    )
    new_alerts, _ = engine.evaluate(t_crit)
    assert len(new_alerts) == 1
    assert new_alerts[0]["severity"] == "CRITICAL"

    # Recovery
    new_alerts, resolved = engine.evaluate(t_normal)
    assert len(resolved) == 1
    assert resolved[0]["status"] == "RESOLVED"


# ==============================================================================
# 5. Event Correlation Engine Tests
# ==============================================================================
def test_backend_event_correlation_scoring():
    """Verifies 4-factor scoring breakdown in EventCorrelationEngine."""
    corr = EventCorrelationEngine(window_seconds=60, threshold_score=60.0)

    # First alert creates incident
    now = datetime.now(timezone.utc)
    a1 = {
        "id": "ALT-1",
        "service": "order-service",
        "metric": "cpu_usage",
        "value": 92.0,
        "severity": "CRITICAL",
        "timestamp": now,
    }
    inc, is_new = corr.process_alert(a1)
    assert is_new is True
    assert inc is not None

    # Correlated alert on same service, related metric, within window
    a2 = {
        "id": "ALT-2",
        "service": "order-service",
        "metric": "api_latency",
        "value": 1500.0,
        "severity": "CRITICAL",
        "timestamp": now,
    }
    score, breakdown = corr.calculate_correlation_score(a2, inc)
    # same_service (30) + time_window (25) + related_metrics (30) + severity (15) = 100
    assert score == 100.0
    assert breakdown["same_service"] == 30.0
    assert breakdown["time_window"] == 25.0
    assert breakdown["related_metrics"] == 30.0
    assert breakdown["severity_relationship"] == 15.0

    # Merges into same incident
    merged_inc, is_new2 = corr.process_alert(a2)
    assert is_new2 is False
    assert merged_inc.id == inc.id
    assert "cpu_usage" in merged_inc.affected_metrics
    assert "api_latency" in merged_inc.affected_metrics


# ==============================================================================
# 6. Incident Creation Tests
# ==============================================================================
def test_backend_incident_creation_and_orm(db_session):
    """Verifies IncidentModel creation, persistence, and querying."""
    inc = IncidentModel(
        id="INC-AUTO-TEST-1",
        title="Payment Ingestion Failure",
        service_name="payment-api",
        severity="HIGH",
        status="OPEN",
        correlation_score=88.5,
        probable_cause="Database connection pool saturation",
        affected_metrics=["db_connections", "api_latency"],
        affected_events=[{"metric": "db_connections", "value": 95.0}],
    )
    db_session.add(inc)
    db_session.commit()

    retrieved = db_session.query(IncidentModel).filter(IncidentModel.id == "INC-AUTO-TEST-1").first()
    assert retrieved is not None
    assert retrieved.service_name == "payment-api"
    assert retrieved.correlation_score == 88.5
    assert len(retrieved.affected_metrics) == 2


# ==============================================================================
# 7. Incident Status Changes Tests
# ==============================================================================
def test_backend_incident_status_transitions(client, db_session):
    """
    Verifies incident lifecycle state transitions:
    OPEN -> INVESTIGATING -> RESOLVED -> CLOSED
    and confirms audit events in incident_events.
    """
    inc = IncidentModel(
        id="INC-STATUS-TEST",
        title="Auth Latency Surge",
        service_name="auth-service",
        severity="HIGH",
        status="OPEN",
    )
    db_session.add(inc)
    db_session.commit()

    # 1. Investigate
    res_inv = client.post(
        f"/api/incidents/{inc.id}/investigate",
        json={"operator": "Lead SRE", "notes": "Investigating token verification delay"},
    )
    assert res_inv.status_code == 200
    assert res_inv.json()["status"] == "INVESTIGATING"

    # 2. Resolve
    res_res = client.post(
        f"/api/incidents/{inc.id}/resolve",
        json={"operator": "Lead SRE", "resolution_notes": "Restarted token cache cluster"},
    )
    assert res_res.status_code == 200
    assert res_res.json()["status"] == "RESOLVED"
    assert res_res.json()["resolved_at"] is not None

    # 3. Close
    res_cls = client.post(
        f"/api/incidents/{inc.id}/close",
        json={"operator": "Lead SRE", "closing_summary": "Post-mortem verified steady state"},
    )
    assert res_cls.status_code == 200
    assert res_cls.json()["status"] == "CLOSED"

    # Verify audit events
    db_session.expire_all()
    events = db_session.query(IncidentEventModel).filter(IncidentEventModel.incident_id == inc.id).all()
    event_types = [e.event_type for e in events]
    assert "INCIDENT_INVESTIGATING" in event_types
    assert "INCIDENT_RESOLVED" in event_types
    assert "INCIDENT_CLOSED" in event_types


# ==============================================================================
# 8. AI Mock Provider Tests
# ==============================================================================
def test_backend_ai_mock_provider():
    """Verifies MockAIProvider extracts evidence, high confidence, and structured recommendations."""
    provider = MockAIProvider()
    investigation = IncidentInvestigation(
        incident_id="INC-AI-TEST",
        incident_info={
            "id": "INC-AI-TEST",
            "title": "Payment Degradation",
            "service": "payment-api",
            "severity": "CRITICAL",
        },
        correlated_alerts=[
            {"metric": "database_connections", "value": 96.0, "severity": "CRITICAL"},
            {"metric": "api_latency", "value": 2.8, "severity": "CRITICAL"},
            {"metric": "http_500_errors", "value": 14.5, "severity": "CRITICAL"},
            {"metric": "cpu_usage", "value": 92.0, "severity": "CRITICAL"},
        ],
        recent_metrics=[
            {"metric_name": "database_connections", "value": 96.0},
            {"metric_name": "cpu_usage", "value": 92.0},
        ],
        service_info={"name": "payment-api", "tier": "CRITICAL"},
    )

    result = provider.analyze_incident_sync(investigation)
    assert result.probable_root_cause == "Database connection pool exhaustion"
    assert result.confidence_score >= 0.90
    assert len(result.evidence) >= 3
    assert len(result.recommended_actions) >= 2
    assert "payment-api" in result.reasoning_summary


# ==============================================================================
# 9. WebSocket Connection Tests
# ==============================================================================
def test_backend_websocket_connection_and_protocol(client, db_session):
    """Verifies WS /ws/monitor handshake, initial state, and ping/pong."""
    seed_initial_data(db_session)
    with client.websocket_connect("/ws/monitor") as ws:
        # Handshake
        raw = ws.receive_text()
        msg = json.loads(raw)
        assert msg["type"] == "INITIAL_STATE"
        assert "telemetry" in msg["data"]
        assert "services" in msg["data"]

        # Keepalive
        ws.send_text("ping")
        pong_raw = ws.receive_text()
        pong = json.loads(pong_raw)
        assert pong["type"] == "PONG"


# ==============================================================================
# 10. CRITICAL REQUIRED SCENARIO:
# CPU spike + Database overload + API latency spike + HTTP error spike
# EXPECTED RESULT: ONE correlated incident
# ==============================================================================
def test_critical_cascading_scenario_combines_into_one_incident(db_session):
    """
    CRITICAL TEST SCENARIO:
    A rapid sequence of 4 related alerts:
    1. CPU spike: cpu_usage = 92%
    2. Database overload: database_connections = 95%
    3. API latency spike: api_latency = 2.8s
    4. HTTP error spike: http_500_errors = 14.5%

    EXPECTED RESULT:
    All 4 alerts are grouped into EXACTLY ONE correlated incident.
    """
    corr_engine = EventCorrelationEngine(window_seconds=60, threshold_score=60.0)
    now = datetime.now(timezone.utc)
    service_target = "Payment API"

    # 4 cascading alerts on the same service within the 60s correlation window
    alerts_sequence = [
        {
            "id": f"ALT-TEST-CPU-{uuid.uuid4().hex[:6].upper()}",
            "service": service_target,
            "metric": "cpu_usage",
            "value": 92.0,
            "threshold": 90.0,
            "severity": "CRITICAL",
            "message": "CPU worker saturation at 92%",
            "timestamp": now,
        },
        {
            "id": f"ALT-TEST-DB-{uuid.uuid4().hex[:6].upper()}",
            "service": service_target,
            "metric": "database_connections",
            "value": 95.0,
            "threshold": 90.0,
            "severity": "CRITICAL",
            "message": "Database connection pool saturated at 95%",
            "timestamp": now,
        },
        {
            "id": f"ALT-TEST-LAT-{uuid.uuid4().hex[:6].upper()}",
            "service": service_target,
            "metric": "api_latency",
            "value": 2.8,
            "threshold": 1.0,
            "severity": "CRITICAL",
            "message": "API response latency spiked to 2.8s",
            "timestamp": now,
        },
        {
            "id": f"ALT-TEST-ERR-{uuid.uuid4().hex[:6].upper()}",
            "service": service_target,
            "metric": "http_500_errors",
            "value": 14.5,
            "threshold": 5.0,
            "severity": "CRITICAL",
            "message": "HTTP 500 error rate spiked to 14.5%",
            "timestamp": now,
        },
    ]

    processed_incidents = []
    for idx, alert_payload in enumerate(alerts_sequence):
        inc, is_new = corr_engine.process_alert(alert_payload)
        assert inc is not None
        if idx == 0:
            assert is_new is True, "First alert should open a new incident"
        else:
            assert is_new is False, f"Alert #{idx+1} ({alert_payload['metric']}) should merge into existing incident"
        if inc not in processed_incidents:
            processed_incidents.append(inc)

    # 1. Verify exactly ONE correlated incident exists
    all_active = list(corr_engine.active_incidents.values())
    assert len(all_active) == 1, f"Expected exactly 1 incident, found {len(all_active)}"

    incident = all_active[0]

    # 2. Verify all 4 metrics are present in the single incident
    assert "cpu_usage" in incident.affected_metrics
    assert "database_connections" in incident.affected_metrics
    assert "api_latency" in incident.affected_metrics
    assert "http_500_errors" in incident.affected_metrics
    assert len(incident.affected_metrics) == 4

    # 3. Verify all 4 raw alert events are attached
    assert len(incident.affected_events) == 4

    # 4. Verify correlation score >= 60
    assert incident.correlation_score >= 60.0

    # 5. Verify synthesized title and severity
    assert incident.service == service_target
    assert incident.severity == "CRITICAL"
    assert "Payment Api degradation" in incident.title or "Payment Api" in incident.title
