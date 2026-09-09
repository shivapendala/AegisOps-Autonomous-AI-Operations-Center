"""
Unit tests for the AegisOps Event Correlation Engine.
Validates:
- Unrelated alerts
- Related alerts
- Multiple cascading alerts becoming one incident (e.g. CPU + DB + API latency + HTTP 500)
- Alerts outside the time window
- Duplicate events suppression
- Correlation score calculation
"""

from datetime import datetime, timedelta, timezone
import pytest

from monitoring.correlation_engine import (
    CorrelatedIncident,
    EventCorrelationEngine,
    are_metrics_related,
    are_severities_related,
)


@pytest.fixture
def engine():
    """Provides a fresh EventCorrelationEngine instance with default 60s window."""
    return EventCorrelationEngine(window_seconds=60, threshold_score=60.0)


# ---------------------------------------------------------------------------
# 1. Scoring & Relationship Helper Tests
# ---------------------------------------------------------------------------

def test_metric_relationships_knowledge_base():
    """Test deterministic metric clustering."""
    # Compute cluster
    assert are_metrics_related("cpu_usage", "memory_usage") is True
    assert are_metrics_related("cpu", "process_count") is True

    # API performance cluster
    assert are_metrics_related("api_latency", "http_500_errors") is True
    assert are_metrics_related("api_latency", "cpu_usage") is True
    assert are_metrics_related("database_connections", "api_latency") is True

    # Database cluster
    assert are_metrics_related("database_connections", "db_latency") is True
    assert are_metrics_related("db_connections", "slow_queries") is True

    # Storage cluster
    assert are_metrics_related("disk_usage", "disk_io") is True

    # Unrelated across orthogonal domains
    assert are_metrics_related("disk_io", "http_500_errors") is False


def test_severity_relationships():
    """Test severity compatibility."""
    assert are_severities_related("CRITICAL", "CRITICAL") is True
    assert are_severities_related("CRITICAL", "HIGH") is True
    assert are_severities_related("CRITICAL", "WARNING") is True
    assert are_severities_related("HIGH", "MEDIUM") is True
    assert are_severities_related("LOW", "CRITICAL") is False


def test_correlation_score_breakdown(engine):
    """Test exact weights: service (+30), time window (+25), metrics (+30), severity (+15)."""
    base_time = datetime.now(timezone.utc)
    incident = CorrelatedIncident(
        id="INC-TEST01",
        title="Payment Service Degradation",
        service="payment-service",
        severity="HIGH",
        status="OPEN",
        correlation_score=100.0,
        probable_cause="Initial breach",
        affected_metrics=["cpu_usage"],
        affected_events=[],
        created_at=base_time,
        updated_at=base_time,
    )

    # 1. Perfectly related alert: same service (+30), within 10s (+25), related metric (+30), related severity (+15)
    alert_matching = {
        "id": "ALT-001",
        "service": "payment-service",
        "metric": "memory_usage",  # related to cpu_usage
        "value": 85.0,
        "severity": "CRITICAL",  # related to HIGH
        "timestamp": base_time + timedelta(seconds=10),
    }
    score, breakdown = engine.calculate_correlation_score(alert_matching, incident)
    assert score == 100.0
    assert breakdown["same_service"] == 30.0
    assert breakdown["time_window"] == 25.0
    assert breakdown["related_metrics"] == 30.0
    assert breakdown["severity_relationship"] == 15.0

    # 2. Alert with different service, but related metric, time, severity -> 25 + 30 + 15 = 70
    alert_diff_service = {
        "id": "ALT-002",
        "service": "auth-service",
        "metric": "memory_usage",
        "value": 82.0,
        "severity": "HIGH",
        "timestamp": base_time + timedelta(seconds=15),
    }
    score2, breakdown2 = engine.calculate_correlation_score(alert_diff_service, incident)
    assert score2 == 70.0
    assert breakdown2["same_service"] == 0.0
    assert breakdown2["time_window"] == 25.0
    assert breakdown2["related_metrics"] == 30.0
    assert breakdown2["severity_relationship"] == 15.0


# ---------------------------------------------------------------------------
# 2. Required Test Case 1: Unrelated Alerts
# ---------------------------------------------------------------------------

def test_unrelated_alerts_create_separate_incidents(engine):
    """
    Unrelated alerts (different services, unrelated metrics, or low score < 60)
    must create separate incidents.
    """
    now = datetime.now(timezone.utc)

    # Alert 1: Storage alert on backup service
    alert1 = {
        "id": "ALT-STORAGE-1",
        "service": "backup-worker",
        "metric": "disk_usage",
        "value": 95.0,
        "threshold": 80.0,
        "severity": "CRITICAL",
        "message": "Disk capacity nearly full on backup volume",
        "timestamp": now,
        "status": "ACTIVE",
    }
    inc1, is_new1 = engine.process_alert(alert1)
    assert is_new1 is True
    assert inc1.service == "backup-worker"
    assert "disk_usage" in inc1.affected_metrics

    # Alert 2: Network latency alert on search-cluster (different service, unrelated metric)
    alert2 = {
        "id": "ALT-NET-2",
        "service": "search-cluster",
        "metric": "network_latency",
        "value": 450.0,
        "threshold": 200.0,
        "severity": "LOW",  # Low severity, unrelated to disk_usage
        "message": "Network latency elevated",
        "timestamp": now + timedelta(seconds=5),
        "status": "ACTIVE",
    }
    inc2, is_new2 = engine.process_alert(alert2)

    # Must NOT group into inc1; must spawn separate incident!
    assert is_new2 is True
    assert inc2.id != inc1.id
    assert inc2.service == "search-cluster"
    assert len(engine.active_incidents) == 2


# ---------------------------------------------------------------------------
# 3. Required Test Case 2: Related Alerts
# ---------------------------------------------------------------------------

def test_related_alerts_grouped_into_same_incident(engine):
    """
    Two related alerts on the same service within the 60s window
    must merge into one incident with score >= 60.
    """
    now = datetime.now(timezone.utc)

    # First alert: High CPU
    alert1 = {
        "id": "ALT-CPU-1",
        "service": "order-service",
        "metric": "cpu_usage",
        "value": 91.0,
        "threshold": 70.0,
        "severity": "CRITICAL",
        "message": "CPU exceeded 90% critical threshold",
        "timestamp": now,
    }
    inc1, is_new1 = engine.process_alert(alert1)
    assert is_new1 is True
    initial_incident_id = inc1.id

    # Second alert: Memory usage spike on the same service 12 seconds later
    alert2 = {
        "id": "ALT-MEM-2",
        "service": "order-service",
        "metric": "memory_usage",
        "value": 88.0,
        "threshold": 75.0,
        "severity": "CRITICAL",
        "message": "Memory exceeded warning threshold",
        "timestamp": now + timedelta(seconds=12),
    }
    inc2, is_new2 = engine.process_alert(alert2)

    # Must be merged into the existing incident
    assert is_new2 is False
    assert inc2.id == initial_incident_id
    assert "cpu_usage" in inc2.affected_metrics
    assert "memory_usage" in inc2.affected_metrics
    assert len(inc2.affected_events) == 2
    assert len(engine.active_incidents) == 1


# ---------------------------------------------------------------------------
# 4. Required Test Case 3: Multiple Alerts Becoming ONE Incident (User Example)
# ---------------------------------------------------------------------------

def test_multiple_cascading_alerts_become_one_incident(engine):
    """
    Test exact prompt requirement:
    CPU = 92%
    Database connections = 95%
    API latency = 2.8 seconds
    HTTP 500 errors = high

    These should become:
    INCIDENT: Payment API degradation (or similar unified incident)
    instead of four unrelated incidents.
    """
    now = datetime.now(timezone.utc)
    service_name = "payment-api"

    alerts = [
        {
            "id": "ALT-PAY-01",
            "service": service_name,
            "metric": "cpu_usage",
            "value": 92.0,
            "threshold": 70.0,
            "severity": "CRITICAL",
            "message": "CPU usage critical at 92%",
            "timestamp": now,
        },
        {
            "id": "ALT-PAY-02",
            "service": service_name,
            "metric": "database_connections",
            "value": 95.0,
            "threshold": 80.0,
            "severity": "CRITICAL",
            "message": "Database connections pool exhausted at 95%",
            "timestamp": now + timedelta(seconds=5),
        },
        {
            "id": "ALT-PAY-03",
            "service": service_name,
            "metric": "api_latency",
            "value": 2.8,
            "threshold": 1.0,
            "severity": "HIGH",
            "message": "API latency spiked to 2.8s",
            "timestamp": now + timedelta(seconds=12),
        },
        {
            "id": "ALT-PAY-04",
            "service": service_name,
            "metric": "http_500_errors",
            "value": 142.0,
            "threshold": 10.0,
            "severity": "CRITICAL",
            "message": "HTTP 500 error rate high",
            "timestamp": now + timedelta(seconds=20),
        },
    ]

    incidents_returned = []
    for alert in alerts:
        inc, is_new = engine.process_alert(alert)
        incidents_returned.append((inc, is_new))

    # 1. First alert created the incident
    assert incidents_returned[0][1] is True
    master_incident_id = incidents_returned[0][0].id

    # 2. Remaining 3 alerts must ALL be merged (is_new == False)
    assert incidents_returned[1][1] is False
    assert incidents_returned[1][0].id == master_incident_id

    assert incidents_returned[2][1] is False
    assert incidents_returned[2][0].id == master_incident_id

    assert incidents_returned[3][1] is False
    assert incidents_returned[3][0].id == master_incident_id

    # 3. Only ONE incident exists in the correlation engine
    assert len(engine.active_incidents) == 1
    final_incident = engine.active_incidents[master_incident_id]

    # 4. Check unified incident properties
    assert final_incident.service == "payment-api"
    assert "Payment Api degradation" in final_incident.title or "degradation" in final_incident.title.lower()
    assert final_incident.severity == "CRITICAL"
    assert final_incident.status == "OPEN"
    assert final_incident.correlation_score >= 60.0
    assert len(final_incident.affected_events) == 4

    expected_metrics = {"cpu_usage", "database_connections", "api_latency", "http_500_errors"}
    assert expected_metrics.issubset(set(final_incident.affected_metrics))
    assert "Resource saturation" in final_incident.probable_cause
    assert "payment-api" in final_incident.probable_cause


# ---------------------------------------------------------------------------
# 5. Required Test Case 4: Alerts Outside the Time Window
# ---------------------------------------------------------------------------

def test_alerts_outside_time_window_do_not_merge(engine):
    """
    Default correlation window is 60 seconds.
    An alert occurring 75 seconds after the previous incident must fail
    time-window correlation (score drops below threshold) and create a separate incident.
    """
    now = datetime.now(timezone.utc)

    # Alert 1 at t = 0
    alert1 = {
        "id": "ALT-T0",
        "service": "checkout-service",
        "metric": "cpu_usage",
        "value": 88.0,
        "severity": "CRITICAL",
        "timestamp": now,
    }
    inc1, is_new1 = engine.process_alert(alert1)
    assert is_new1 is True

    # Alert 2 at t = +75s (> 60s window) with different service or without sufficient score
    # Note: Same service (+30) + related metric (+30) + severity (+15) without time (+0) = 75 >= 60.
    # But if service is different OR metrics are not perfectly clustered outside window:
    # E.g. Different service + related metrics + severity = 0 + 0 (time > 60s) + 30 + 15 = 45 (< 60)
    alert_outside_diff_svc = {
        "id": "ALT-T75",
        "service": "reporting-service",
        "metric": "cpu_usage",
        "value": 90.0,
        "severity": "CRITICAL",
        "timestamp": now + timedelta(seconds=75),
    }
    score, breakdown = engine.calculate_correlation_score(alert_outside_diff_svc, inc1)
    # Time window factor must be 0
    assert breakdown["time_window"] == 0.0
    # Total score should be 30 (metric) + 15 (sev) = 45 < 60
    assert score < 60.0

    inc2, is_new2 = engine.process_alert(alert_outside_diff_svc)
    assert is_new2 is True
    assert inc2.id != inc1.id
    assert len(engine.active_incidents) == 2


# ---------------------------------------------------------------------------
# 6. Required Test Case 5: Duplicate Events
# ---------------------------------------------------------------------------

def test_duplicate_events_are_suppressed(engine):
    """
    Duplicate alerts (same alert id or identical signature within window)
    must be recognized and suppressed without creating new incidents or inflating counts.
    """
    now = datetime.now(timezone.utc)
    alert = {
        "id": "ALT-DUP-01",
        "service": "inventory-service",
        "metric": "disk_usage",
        "value": 89.0,
        "severity": "WARNING",
        "message": "Disk usage threshold exceeded",
        "timestamp": now,
    }

    # First arrival: creates incident
    inc1, is_new1 = engine.process_alert(alert)
    assert is_new1 is True
    assert inc1 is not None
    assert len(inc1.affected_events) == 1

    # Second arrival: identical duplicate alert
    inc2, is_new2 = engine.process_alert(alert)
    assert inc2 is None
    assert is_new2 is False

    # Verify no second incident was spawned and incident event count did not artificially inflate
    assert len(engine.active_incidents) == 1
    assert len(engine.active_incidents[inc1.id].affected_events) == 1


def test_incident_to_dict_serialization(engine):
    """Verify CorrelatedIncident serializes all required fields."""
    now = datetime.now(timezone.utc)
    alert = {
        "id": "ALT-SER-1",
        "service": "payment-api",
        "metric": "api_latency",
        "value": 3.2,
        "severity": "CRITICAL",
        "timestamp": now,
    }
    inc, _ = engine.process_alert(alert)
    data = inc.to_dict()

    required_fields = [
        "id",
        "title",
        "service",
        "severity",
        "status",
        "correlation_score",
        "probable_cause",
        "affected_metrics",
        "affected_events",
        "created_at",
        "updated_at",
    ]
    for field_name in required_fields:
        assert field_name in data
        assert data[field_name] is not None
