"""Unit tests for Database ORM models and Incident Management API."""
from database.models.incident import IncidentModel
from database.models.metric_log import MetricLogModel
from database.models.audit_log import AuditLogModel


def test_database_incident_orm(db_session):
    incident = IncidentModel(
        id="INC-TEST01",
        title="Database Connection Latency Spike",
        description="P99 response time exceeded 2500ms",
        severity="HIGH",
        status="OPEN",
        root_cause="Connection pool exhaustion",
    )
    db_session.add(incident)
    db_session.commit()

    retrieved = db_session.query(IncidentModel).filter(IncidentModel.id == "INC-TEST01").first()
    assert retrieved is not None
    assert retrieved.title == "Database Connection Latency Spike"
    assert retrieved.severity == "HIGH"
    assert retrieved.to_dict()["status"] == "OPEN"


def test_database_metric_and_audit_logs(db_session):
    metric = MetricLogModel(
        host_name="worker-node-01",
        cpu_percent=45.2,
        memory_percent=60.1,
        disk_percent=72.0,
    )
    audit = AuditLogModel(
        action="SERVICE_RESTART",
        actor="Autopilot",
        target="worker-node-01",
        details="Triggered graceful worker restart",
    )
    db_session.add(metric)
    db_session.add(audit)
    db_session.commit()

    saved_metric = db_session.query(MetricLogModel).filter(MetricLogModel.host_name == "worker-node-01").first()
    assert saved_metric is not None
    assert saved_metric.cpu_percent == 45.2

    saved_audit = db_session.query(AuditLogModel).filter(AuditLogModel.action == "SERVICE_RESTART").first()
    assert saved_audit is not None
    assert saved_audit.status == "SUCCESS"


def test_incidents_api_endpoints(client):
    # Create incident
    create_resp = client.post(
        "/api/v1/incidents",
        json={
            "title": "API Gateway 502 Rate Spike",
            "description": "502 Bad Gateway rate exceeded 5% over 2 minutes",
            "severity": "CRITICAL",
        },
    )
    assert create_resp.status_code == 201
    created_data = create_resp.json()
    inc_id = created_data["id"]
    assert inc_id.startswith("INC-")

    # List incidents
    list_resp = client.get("/api/v1/incidents")
    assert list_resp.status_code == 200
    incidents = list_resp.json()
    assert any(i["id"] == inc_id for i in incidents)

    # Get single incident
    get_resp = client.get(f"/api/v1/incidents/{inc_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["title"] == "API Gateway 502 Rate Spike"

    # Start investigation (OPEN -> INVESTIGATING)
    inv_resp = client.post(f"/api/v1/incidents/{inc_id}/investigate")
    assert inv_resp.status_code == 200
    assert inv_resp.json()["status"] == "INVESTIGATING"

    # Resolve incident (INVESTIGATING -> RESOLVED)
    resolve_resp = client.post(
        f"/api/v1/incidents/{inc_id}/resolve",
        json={"resolution_notes": "Upstream proxy pool recycled", "actor": "DevOps Lead"},
    )
    assert resolve_resp.status_code == 200
    assert resolve_resp.json()["status"] == "RESOLVED"
