"""
Unit tests for backend/incidents correlation and incident service.
Tests:
- find_recent_alerts()
- compare_service()
- compare_time_window()
- compare_metric_relationship()
- calculate_score()
- find_related_alerts()
- IncidentService.correlate_alert()
- Lifecycle transitions
"""

from datetime import datetime, timedelta, timezone
import pytest

from backend.incidents.correlation import (
    compare_service,
    compare_time_window,
    compare_metric_relationship,
    compare_severity_relationship,
    calculate_score,
    find_recent_alerts,
    find_related_alerts,
    correlate_and_group_alerts,
    POINTS_SAME_SERVICE,
    POINTS_TIME_WINDOW,
    POINTS_RELATED_METRICS,
    POINTS_SEVERITY_RELATION,
)
from backend.incidents.service import IncidentService
from database.models.alert import AlertModel
from database.models.incident import IncidentModel
from database.models.incident_event import IncidentEventModel


def test_comparison_functions():
    """Verify each comparison rule function independently."""
    now = datetime.now(timezone.utc)
    a1 = {"id": 1, "service": "payment-api", "metric": "cpu_usage", "severity": "CRITICAL", "timestamp": now}
    a2 = {"id": 2, "service": "payment-api", "metric": "database_connections", "severity": "HIGH", "timestamp": now + timedelta(seconds=15)}
    a3 = {"id": 3, "service": "auth-service", "metric": "disk_usage", "severity": "LOW", "timestamp": now + timedelta(seconds=120)}

    # Same service
    assert compare_service(a1, a2) == POINTS_SAME_SERVICE
    assert compare_service(a1, a3) == 0.0

    # Time window
    assert compare_time_window(a1, a2, window_seconds=60) == POINTS_TIME_WINDOW
    assert compare_time_window(a1, a3, window_seconds=60) == 0.0

    # Metric relationship
    assert compare_metric_relationship(a1, a2) == POINTS_RELATED_METRICS
    assert compare_metric_relationship(a1, a3) == 0.0

    # Severity relationship
    assert compare_severity_relationship(a1, a2) == POINTS_SEVERITY_RELATION
    assert compare_severity_relationship(a1, a3) == 0.0


def test_calculate_score_and_find_related():
    """Test full score calculation and related alerts retrieval."""
    now = datetime.now(timezone.utc)
    target = {"id": 10, "service": "Payment API", "metric": "CPU", "severity": "HIGH", "timestamp": now}
    candidate_match = {"id": 11, "service": "Payment API", "metric": "DB Connections", "severity": "HIGH", "timestamp": now + timedelta(seconds=10)}
    candidate_unrelated = {"id": 12, "service": "Other Svc", "metric": "disk", "severity": "LOW", "timestamp": now + timedelta(seconds=80)}

    score, breakdown = calculate_score(target, candidate_match)
    assert score == 100.0
    assert breakdown["same_service"] == 30.0
    assert breakdown["time_window"] == 25.0
    assert breakdown["related_metrics"] == 30.0
    assert breakdown["severity_relationship"] == 15.0

    related = find_related_alerts(target, [candidate_match, candidate_unrelated], threshold=60.0)
    assert len(related) == 1
    assert related[0][0]["id"] == 11
    assert related[0][1] == 100.0


def test_incident_service_correlate_alert_db_flow(db_session):
    """Test IncidentService creating, merging, and attaching incident_events in database."""
    now = datetime.now(timezone.utc)
    service = IncidentService(window_seconds=60, threshold_score=60.0)

    # 1. Alert 1: CPU spike
    alert1 = {"id": 501, "service": "Payment API", "metric": "CPU", "value": 94.0, "severity": "HIGH", "timestamp": now}
    inc1, is_new1, score1 = service.correlate_alert(db_session, alert1)
    assert is_new1 is True
    master_id = inc1.id

    # Verify initial incident_event
    events1 = db_session.query(IncidentEventModel).filter(IncidentEventModel.incident_id == master_id).all()
    assert len(events1) == 1
    assert events1[0].alert_id == 501

    # 2. Alert 2: DB Connections
    alert2 = {"id": 502, "service": "Payment API", "metric": "DB Connections", "value": 96.0, "severity": "HIGH", "timestamp": now + timedelta(seconds=5)}
    inc2, is_new2, score2 = service.correlate_alert(db_session, alert2)
    assert is_new2 is False
    assert inc2.id == master_id
    assert score2 == 100.0

    # 3. Alert 3: API Latency
    alert3 = {"id": 503, "service": "Payment API", "metric": "API Latency", "value": 2.8, "severity": "HIGH", "timestamp": now + timedelta(seconds=12)}
    inc3, is_new3, score3 = service.correlate_alert(db_session, alert3)
    assert is_new3 is False
    assert inc3.id == master_id

    # 4. Alert 4: HTTP 500
    alert4 = {"id": 504, "service": "Payment API", "metric": "HTTP 500", "value": 14.2, "severity": "CRITICAL", "timestamp": now + timedelta(seconds=20)}
    inc4, is_new4, score4 = service.correlate_alert(db_session, alert4)
    assert is_new4 is False
    assert inc4.id == master_id

    # Verify ONE incident exists with all 4 alerts connected in incident_events table
    events_all = db_session.query(IncidentEventModel).filter(IncidentEventModel.incident_id == master_id).all()
    assert len(events_all) == 4
    connected_alert_ids = [e.alert_id for e in events_all]
    assert set(connected_alert_ids) == {501, 502, 503, 504}

    # Verify final incident state
    assert "Payment Api degradation" in inc4.title or "Payment API degradation" in inc4.title or "degradation" in inc4.title.lower()
    assert inc4.severity == "CRITICAL"
    assert len(inc4.affected_metrics) == 4
    assert len(inc4.affected_events) == 4

    # Lifecycle transitions
    inv = IncidentService.investigate_incident(db_session, master_id, operator="Lead SRE", notes="Triage in progress")
    assert inv.status == "INVESTIGATING"

    res = IncidentService.resolve_incident(db_session, master_id, operator="Lead SRE", resolution_notes="Pool scale deployed")
    assert res.status == "RESOLVED"

    cls = IncidentService.close_incident(db_session, master_id, operator="Lead SRE", closure_notes="Closed post-mortem")
    assert cls.status == "CLOSED"
