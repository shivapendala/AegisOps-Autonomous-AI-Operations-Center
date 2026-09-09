"""
tests/test_incidents.py
Validates Incident management lifecycle as specified in Step 16:
- Test 6: OPEN -> INVESTIGATING -> RESOLVED -> CLOSED
- Verifies forbidden skipping, rollbacks, and modifications on terminal CLOSED state
"""

import pytest
from database.models.incident import IncidentModel


def test_test6_incident_lifecycle_open_investigating_resolved_closed(client, db_session):
    """
    Test 6:
    OPEN
     ↓
    INVESTIGATING
     ↓
    RESOLVED
     ↓
    CLOSED

    Verify that:
    1. Initial status is OPEN.
    2. POST /api/incidents/{id}/investigate moves status to INVESTIGATING.
    3. POST /api/incidents/{id}/resolve moves status to RESOLVED.
    4. POST /api/incidents/{id}/close moves status to CLOSED.
    5. Disallowed transitions (e.g. jumping from OPEN to RESOLVED directly, or mutating CLOSED) fail with 400.
    """
    incident_id = "INC-TEST-16-001"
    inc = IncidentModel(
        id=incident_id,
        title="Test Incident Lifecycle",
        service_name="payment-api",
        severity="CRITICAL",
        status="OPEN",
        correlation_score=91.0,
        probable_cause="Database connection pool exhaustion",
        affected_metrics=["cpu_usage", "database_connections"],
        affected_events=[
            {"metric": "cpu_usage", "value": 94.0, "severity": "CRITICAL"},
            {"metric": "database_connections", "value": 96.0, "severity": "CRITICAL"},
        ],
    )
    db_session.add(inc)
    db_session.commit()
    db_session.refresh(inc)

    # Step 1: Initial state is OPEN
    get_res = client.get(f"/api/incidents/{incident_id}")
    assert get_res.status_code == 200
    assert get_res.json()["status"] == "OPEN"

    # Step 1.1: Verify disallowed skip from OPEN directly to RESOLVED or CLOSED fails with 400
    res_bad_resolve = client.post(f"/api/incidents/{incident_id}/resolve")
    assert res_bad_resolve.status_code == 400
    assert "invalid transition" in res_bad_resolve.json()["detail"].lower()

    res_bad_close = client.post(f"/api/incidents/{incident_id}/close")
    assert res_bad_close.status_code == 400
    assert "invalid transition" in res_bad_close.json()["detail"].lower()

    # Step 2: Transition OPEN -> INVESTIGATING
    res_investigate = client.post(f"/api/incidents/{incident_id}/investigate")
    assert res_investigate.status_code == 200
    assert res_investigate.json()["status"] == "INVESTIGATING"

    # Step 2.1: Verify disallowed skip from INVESTIGATING directly to CLOSED
    res_bad_close2 = client.post(f"/api/incidents/{incident_id}/close")
    assert res_bad_close2.status_code == 400

    # Step 3: Transition INVESTIGATING -> RESOLVED
    res_resolve = client.post(f"/api/incidents/{incident_id}/resolve")
    assert res_resolve.status_code == 200
    assert res_resolve.json()["status"] == "RESOLVED"
    assert res_resolve.json()["resolved_at"] is not None

    # Step 3.1: Verify disallowed rollback from RESOLVED -> INVESTIGATING
    res_bad_investigate = client.post(f"/api/incidents/{incident_id}/investigate")
    assert res_bad_investigate.status_code == 400

    # Step 4: Transition RESOLVED -> CLOSED
    res_close = client.post(f"/api/incidents/{incident_id}/close")
    assert res_close.status_code == 200
    assert res_close.json()["status"] == "CLOSED"

    # Step 5: Terminal state CLOSED cannot be mutated
    res_reopen = client.post(f"/api/incidents/{incident_id}/investigate")
    assert res_reopen.status_code == 400
    res_reresolve = client.post(f"/api/incidents/{incident_id}/resolve")
    assert res_reresolve.status_code == 400
    res_reclose = client.post(f"/api/incidents/{incident_id}/close")
    assert res_reclose.status_code == 400
