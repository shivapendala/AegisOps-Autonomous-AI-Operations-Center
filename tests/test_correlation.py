"""
tests/test_correlation.py
Validates event correlation logic as specified in Step 16:
- Test 1: CPU Alert + DB Alert on same service at same time -> ONE incident
- Test 2: CPU Alert + Auth Alert on different services -> Separate incidents
- Test 3: Alert 1 + Alert 2 5 minutes apart -> Don't correlate (exceeds window)
"""

from datetime import datetime, timedelta, timezone
import pytest

from monitoring.correlation_engine import EventCorrelationEngine


@pytest.fixture
def correlation_engine():
    """Provides a clean EventCorrelationEngine instance with default 60-second window."""
    return EventCorrelationEngine(window_seconds=60, threshold_score=60.0)


def test_test1_cpu_and_db_alert_same_service_same_time_correlates_to_one_incident(correlation_engine):
    """
    Test 1:
    CPU Alert
    DB Alert
    same service
    same time

    -> ONE incident
    """
    now = datetime.now(timezone.utc)

    cpu_alert = {
        "id": "alert-cpu-001",
        "service": "payment-api",
        "service_name": "payment-api",
        "metric": "cpu_usage",
        "metric_name": "cpu_usage",
        "severity": "CRITICAL",
        "value": 94.0,
        "timestamp": now,
        "message": "High CPU usage 94% on payment-api",
    }

    db_alert = {
        "id": "alert-db-001",
        "service": "payment-api",
        "service_name": "payment-api",
        "metric": "database_connections",
        "metric_name": "database_connections",
        "severity": "CRITICAL",
        "value": 96.0,
        "timestamp": now + timedelta(seconds=2),
        "message": "Database connection pool at 96% on payment-api",
    }

    inc1, is_new1 = correlation_engine.process_alert(cpu_alert)
    assert is_new1 is True
    assert inc1.service == "payment-api"

    inc2, is_new2 = correlation_engine.process_alert(db_alert)
    # Must correlate into the same incident
    assert is_new2 is False
    assert inc2.id == inc1.id

    # Must have exactly ONE active incident covering both metrics
    assert len(correlation_engine.active_incidents) == 1
    incident = list(correlation_engine.active_incidents.values())[0]
    assert "cpu_usage" in incident.affected_metrics
    assert "database_connections" in incident.affected_metrics
    assert len(incident.affected_events) == 2


def test_test2_cpu_and_auth_alert_different_services_separate_incidents(correlation_engine):
    """
    Test 2:
    CPU Alert
    Auth Alert
    different service

    -> Separate incidents
    """
    now = datetime.now(timezone.utc)

    payment_cpu_alert = {
        "id": "alert-pay-cpu-002",
        "service": "payment-api",
        "service_name": "payment-api",
        "metric": "cpu_usage",
        "metric_name": "cpu_usage",
        "severity": "CRITICAL",
        "value": 92.0,
        "timestamp": now,
        "message": "High CPU usage 92% on payment-api",
    }

    auth_alert = {
        "id": "alert-auth-002",
        "service": "auth-service",
        "service_name": "auth-service",
        "metric": "jwt_validation_errors",
        "metric_name": "jwt_validation_errors",
        "severity": "HIGH",
        "value": 45.0,
        "timestamp": now + timedelta(seconds=1),
        "message": "Elevated JWT validation failures on auth-service",
    }

    inc1, is_new1 = correlation_engine.process_alert(payment_cpu_alert)
    inc2, is_new2 = correlation_engine.process_alert(auth_alert)

    # Must produce separate incidents because services are different
    assert is_new1 is True
    assert is_new2 is True
    assert inc1.id != inc2.id
    assert len(correlation_engine.active_incidents) == 2

    services = {inc.service for inc in correlation_engine.active_incidents.values()}
    assert services == {"payment-api", "auth-service"}


def test_test3_alerts_five_minutes_apart_do_not_correlate(correlation_engine):
    """
    Test 3:
    Alert 1
    Alert 2

    5 minutes apart

    -> Don't correlate (exceeds window)
    """
    t0 = datetime(2026, 9, 9, 10, 0, 0, tzinfo=timezone.utc)
    t1 = t0 + timedelta(minutes=5)  # 300 seconds apart, window is 60 seconds

    alert_1 = {
        "id": "alert-time-001",
        "service": "payment-api",
        "service_name": "payment-api",
        "metric": "cpu_usage",
        "metric_name": "cpu_usage",
        "severity": "CRITICAL",
        "value": 95.0,
        "timestamp": t0,
        "message": "Initial CPU spike",
    }

    alert_2 = {
        "id": "alert-time-002",
        "service": "payment-api",
        "service_name": "payment-api",
        "metric": "database_connections",
        "metric_name": "database_connections",
        "severity": "CRITICAL",
        "value": 96.0,
        "timestamp": t1,
        "message": "Secondary DB spike 5 minutes later",
    }

    inc1, is_new1 = correlation_engine.process_alert(alert_1)
    inc2, is_new2 = correlation_engine.process_alert(alert_2)

    # Because they are 5 minutes apart (> 60s window), they must NOT correlate into one incident
    assert is_new1 is True
    assert is_new2 is True
    assert inc1.id != inc2.id
    assert len(correlation_engine.active_incidents) == 2
