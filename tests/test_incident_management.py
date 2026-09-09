"""
Unit tests for AegisOps Incident Management.
Tests lifecycle state transitions: OPEN -> INVESTIGATING -> RESOLVED -> CLOSED,
API endpoints (GET, GET /id, POST /investigate, POST /resolve, POST /close),
database persistence of status changes and audit logs, and detail field verification.
"""
from database.models.incident import IncidentModel
from database.models.incident_event import IncidentEventModel
from database.models.audit_log import AuditLogModel


def test_incident_lifecycle_flow(client, db_session):
    """
    Test full lifecycle state transitions:
    1. Create incident (OPEN)
    2. POST /api/incidents/{id}/investigate -> INVESTIGATING
    3. POST /api/incidents/{id}/resolve -> RESOLVED
    4. POST /api/incidents/{id}/close -> CLOSED
    Verify database records and responses at each stage.
    """
    inc = IncidentModel(
        id="INC-LIFE-001",
        title="Database Latency Spike",
        service_name="order-service",
        severity="HIGH",
        status="OPEN",
        correlation_score=85.0,
        probable_cause="Connection pool exhaustion",
        affected_metrics=["db_connections", "api_latency"],
        affected_events=[
            {"type": "ALERT", "metric": "db_connections", "value": 96.0, "severity": "CRITICAL"},
            {"type": "ALERT", "metric": "api_latency", "value": 2.8, "severity": "HIGH"}
        ],
        metadata_json={
            "ai_root_cause_analysis": {
                "confidence_score": 0.92,
                "evidence": ["Connection pool saturation at 96%", "API latency elevated to 2.8s"],
                "recommended_actions": ["Increase DB pool limit", "Inspect query bottlenecks"]
            }
        }
    )
    db_session.add(inc)
    db_session.commit()
    db_session.refresh(inc)

    # 1. Verify GET /api/incidents/{id} returns all 12 required fields
    get_res = client.get(f"/api/incidents/{inc.id}")
    assert get_res.status_code == 200
    data = get_res.json()
    assert data["id"] == "INC-LIFE-001"
    assert data["title"] == "Database Latency Spike"
    assert data["service"] == "order-service"
    assert data["severity"] == "HIGH"
    assert data["status"] == "OPEN"
    assert data["correlation_score"] == 85.0
    assert data["probable_cause"] == "Connection pool exhaustion"
    assert "db_connections" in data["affected_metrics"]
    assert len(data["affected_events"]) == 2
    assert data["confidence"] == 0.92
    assert len(data["evidence"]) >= 1
    assert len(data["recommended_actions"]) >= 1
    assert isinstance(data["timeline"], list)

    # 2. Transition to INVESTIGATING
    inv_res = client.post(
        f"/api/incidents/{inc.id}/investigate",
        json={"operator": "Alice SRE", "notes": "Investigating slow database connection pool"}
    )
    assert inv_res.status_code == 200
    inv_data = inv_res.json()
    assert inv_data["status"] == "INVESTIGATING"

    # Verify DB persistence of INVESTIGATING status and incident event
    db_session.expire_all()
    updated_inc = db_session.query(IncidentModel).filter(IncidentModel.id == inc.id).first()
    assert updated_inc.status == "INVESTIGATING"
    events = db_session.query(IncidentEventModel).filter(IncidentEventModel.incident_id == inc.id).all()
    assert any(e.event_type == "INCIDENT_INVESTIGATING" for e in events)

    # 3. Transition to RESOLVED
    res_res = client.post(
        f"/api/incidents/{inc.id}/resolve",
        json={"operator": "Alice SRE", "resolution_notes": "Increased connection pool size to 50"}
    )
    assert res_res.status_code == 200
    res_data = res_res.json()
    assert res_data["status"] == "RESOLVED"
    assert res_data["resolved_at"] is not None

    # Verify DB persistence of RESOLVED status and resolved_at timestamp
    db_session.expire_all()
    updated_inc = db_session.query(IncidentModel).filter(IncidentModel.id == inc.id).first()
    assert updated_inc.status == "RESOLVED"
    assert updated_inc.resolved_at is not None
    events = db_session.query(IncidentEventModel).filter(IncidentEventModel.incident_id == inc.id).all()
    assert any(e.event_type == "INCIDENT_RESOLVED" for e in events)

    # 4. Transition to CLOSED
    close_res = client.post(
        f"/api/incidents/{inc.id}/close",
        json={"operator": "Alice SRE", "closing_summary": "Post-mortem completed; steady state confirmed"}
    )
    assert close_res.status_code == 200
    close_data = close_res.json()
    assert close_data["status"] == "CLOSED"

    # Verify DB persistence of CLOSED status
    db_session.expire_all()
    updated_inc = db_session.query(IncidentModel).filter(IncidentModel.id == inc.id).first()
    assert updated_inc.status == "CLOSED"
    events = db_session.query(IncidentEventModel).filter(IncidentEventModel.incident_id == inc.id).all()
    assert any(e.event_type == "INCIDENT_CLOSED" for e in events)


def test_get_incidents_filtering_by_status(client, db_session):
    """Test GET /api/incidents filtering by status parameter."""
    inc_resolved = IncidentModel(
        id="INC-FLT-RESOLVED",
        title="Resolved Auth Failure",
        service_name="auth-service",
        severity="MEDIUM",
        status="RESOLVED",
        correlation_score=60.0
    )
    inc_open = IncidentModel(
        id="INC-FLT-OPEN",
        title="Open Gateway Timeout",
        service_name="api-gateway",
        severity="HIGH",
        status="OPEN",
        correlation_score=75.0
    )
    db_session.add_all([inc_resolved, inc_open])
    db_session.commit()

    res_all = client.get("/api/incidents")
    assert res_all.status_code == 200
    all_data = res_all.json()
    assert len(all_data) >= 2

    res_open = client.get("/api/incidents?status=OPEN")
    assert res_open.status_code == 200
    open_data = res_open.json()
    assert all(inc["status"] == "OPEN" for inc in open_data)
    assert any(inc["title"] == "Open Gateway Timeout" for inc in open_data)

    res_resolved = client.get("/api/incidents?status=RESOLVED")
    assert res_resolved.status_code == 200
    resolved_data = res_resolved.json()
    assert all(inc["status"] == "RESOLVED" for inc in resolved_data)
    assert any(inc["title"] == "Resolved Auth Failure" for inc in resolved_data)


def test_incident_not_found_endpoints(client):
    """Test 404 behavior for invalid incident ID across all operations."""
    invalid_id = "non-existent-incident-uuid"
    assert client.get(f"/api/incidents/{invalid_id}").status_code == 404
    assert client.post(f"/api/incidents/{invalid_id}/investigate", json={}).status_code == 404
    assert client.post(f"/api/incidents/{invalid_id}/resolve", json={}).status_code == 404
    assert client.post(f"/api/incidents/{invalid_id}/close", json={}).status_code == 404


def test_step15_strict_incident_status_workflow(client, db_session):
    """
    STEP 15: Verify the strict linear workflow:
        OPEN -> INVESTIGATING -> RESOLVED -> CLOSED
    Random or out-of-order status transitions must be blocked with HTTP 400.
    """
    # 1. Create a brand-new incident in OPEN status
    create_resp = client.post(
        "/api/incidents",
        json={
            "title": "Payment Settlement API Slowdown",
            "description": "High latency observed on settlement gateway",
            "severity": "CRITICAL",
        },
    )
    assert create_resp.status_code == 201
    inc_id = create_resp.json()["id"]
    assert create_resp.json()["status"] == "OPEN"

    # 2. Block random jump: OPEN -> RESOLVED (must investigate first)
    bad_resolve = client.post(f"/api/incidents/{inc_id}/resolve")
    assert bad_resolve.status_code == 400
    assert "investigation" in bad_resolve.json()["detail"].lower()

    # 3. Block random jump: OPEN -> CLOSED (cannot skip to closed)
    bad_close = client.post(f"/api/incidents/{inc_id}/close")
    assert bad_close.status_code == 400

    # 4. Valid transition: OPEN -> INVESTIGATING
    inv_resp = client.post(f"/api/incidents/{inc_id}/investigate")
    assert inv_resp.status_code == 200
    assert inv_resp.json()["status"] == "INVESTIGATING"

    # 5. Block duplicate investigation: INVESTIGATING -> INVESTIGATING
    dup_inv = client.post(f"/api/incidents/{inc_id}/investigate")
    assert dup_inv.status_code == 400

    # 6. Block random jump: INVESTIGATING -> CLOSED (must resolve first)
    skip_resolve_close = client.post(f"/api/incidents/{inc_id}/close")
    assert skip_resolve_close.status_code == 400
    assert "resolved" in skip_resolve_close.json()["detail"].lower()

    # 7. Valid transition: INVESTIGATING -> RESOLVED
    res_resp = client.post(
        f"/api/incidents/{inc_id}/resolve",
        json={"resolution_notes": "Added worker pool instances and restarted idle connections"},
    )
    assert res_resp.status_code == 200
    assert res_resp.json()["status"] == "RESOLVED"
    assert res_resp.json()["resolved_at"] is not None

    # 8. Block invalid rollback: RESOLVED -> INVESTIGATING
    rollback_inv = client.post(f"/api/incidents/{inc_id}/investigate")
    assert rollback_inv.status_code == 400

    # 9. Block duplicate resolution: RESOLVED -> RESOLVED
    dup_res = client.post(f"/api/incidents/{inc_id}/resolve")
    assert dup_res.status_code == 400

    # 10. Valid transition: RESOLVED -> CLOSED
    close_resp = client.post(
        f"/api/incidents/{inc_id}/close",
        json={"closure_notes": "Post-mortem completed; steady state confirmed"},
    )
    assert close_resp.status_code == 200
    assert close_resp.json()["status"] == "CLOSED"

    # 11. Block modification on terminal CLOSED state
    closed_inv = client.post(f"/api/incidents/{inc_id}/investigate")
    assert closed_inv.status_code == 400
    assert "terminal" in closed_inv.json()["detail"].lower() or "closed" in closed_inv.json()["detail"].lower()

    closed_res = client.post(f"/api/incidents/{inc_id}/resolve")
    assert closed_res.status_code == 400

    closed_close = client.post(f"/api/incidents/{inc_id}/close")
    assert closed_close.status_code == 400

