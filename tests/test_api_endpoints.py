"""
Integration tests for the required AegisOps REST APIs:
- GET /api/health
- GET /api/services
- GET /api/metrics
- GET /api/alerts
- GET /api/incidents
"""

from database.init_db import seed_initial_data


def test_api_health_endpoint(client, db_session):
    seed_initial_data(db_session)
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["healthy", "degraded"]
    assert "AegisOps" in data["app_name"]
    assert data["tables_ready"] is True
    assert "ai_engine" in data


def test_api_services_endpoint(client, db_session):
    seed_initial_data(db_session)
    response = client.get("/api/services")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 4

    names = [s["name"] for s in data]
    assert "api-gateway" in names
    assert "auth-service" in names
    assert "payment-processor" in names

    # Verify filter
    filtered_resp = client.get("/api/services?status=HEALTHY")
    assert filtered_resp.status_code == 200
    filtered_data = filtered_resp.json()
    assert all(s["status"] == "HEALTHY" for s in filtered_data)


def test_api_metrics_endpoint(client, db_session):
    seed_initial_data(db_session)
    response = client.get("/api/metrics")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    metric = data[0]
    assert "metric_name" in metric
    assert "value" in metric
    assert "timestamp" in metric


def test_api_alerts_endpoint(client, db_session):
    seed_initial_data(db_session)
    response = client.get("/api/alerts")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 3

    # Check alert structure
    alert = data[0]
    assert "service" in alert
    assert "metric" in alert
    assert "value" in alert
    assert "threshold" in alert
    assert "severity" in alert
    assert "message" in alert
    assert "timestamp" in alert
    assert "status" in alert

    # Check filtering
    high_resp = client.get("/api/alerts?severity=HIGH")
    assert high_resp.status_code == 200
    assert all(a["severity"] == "HIGH" for a in high_resp.json())


def test_api_incidents_endpoint(client, db_session):
    seed_initial_data(db_session)
    response = client.get("/api/incidents")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1

    incident = data[0]
    assert incident["id"].startswith("INC-")
    assert "title" in incident
    assert "severity" in incident
    assert "status" in incident
    assert "events" in incident
    assert "recommendations" in incident
    assert len(incident["events"]) > 0
    assert len(incident["recommendations"]) > 0


def test_post_alert_auto_correlates_incident(client, db_session):
    """Verify that posting alerts via HTTP automatically creates and merges incidents."""
    # 1. Post CPU alert -> Creates Incident #1
    alert1_payload = {
        "service": "Payment API",
        "metric": "CPU",
        "value": 94.0,
        "threshold": 80.0,
        "severity": "HIGH",
        "message": "Payment API CPU usage reached 94%",
    }
    resp1 = client.post("/api/alerts", json=alert1_payload)
    assert resp1.status_code == 201
    alert1_id = resp1.json()["id"]

    # Check incidents list
    inc_resp1 = client.get("/api/incidents")
    assert inc_resp1.status_code == 200
    incidents_after_1 = inc_resp1.json()
    inc1 = next((i for i in incidents_after_1 if i["service_name"] == "Payment API" or "Payment API" in i["title"]), None)
    assert inc1 is not None
    inc1_id = inc1["id"]

    # 2. Post DB Connections alert -> Correlated into existing Incident #1
    alert2_payload = {
        "service": "Payment API",
        "metric": "DB Connections",
        "value": 96.0,
        "threshold": 85.0,
        "severity": "HIGH",
        "message": "Payment API DB connections at 96%",
    }
    resp2 = client.post("/api/alerts", json=alert2_payload)
    assert resp2.status_code == 201

    # Check incident was updated, not duplicated
    inc_resp2 = client.get(f"/api/incidents/{inc1_id}")
    assert inc_resp2.status_code == 200
    inc_data2 = inc_resp2.json()
    assert "CPU" in inc_data2["affected_metrics"]
    assert "DB Connections" in inc_data2["affected_metrics"]
    assert len(inc_data2["events"]) >= 2


def test_step6_incident_apis(client, db_session):
    """
    STEP 6 Verification:
    - GET /api/incidents (Returns all incidents)
    - GET /api/incidents/{incident_id} (Returns complete incident: id, title, severity, status, correlation_score)
    - GET /api/incidents/{incident_id}/events (Returns related alerts)
    - GET /api/incidents/{incident_id}/recommendations (Returns recommended actions)
    - POST /api/incidents/{incident_id}/investigate (Starts AI investigation)
    - POST /api/incidents/{incident_id}/resolve (Resolves incident)
    - POST /api/incidents/{incident_id}/close (Closes incident)
    """
    seed_initial_data(db_session)

    # 1. GET /api/incidents
    resp_list = client.get("/api/incidents")
    assert resp_list.status_code == 200
    incidents = resp_list.json()
    assert isinstance(incidents, list)
    assert len(incidents) >= 1

    target_inc = next((i for i in incidents if i.get("status") == "OPEN"), incidents[0])
    inc_id = target_inc["id"]

    # 2. GET /api/incidents/{incident_id}
    resp_single = client.get(f"/api/incidents/{inc_id}")
    assert resp_single.status_code == 200
    inc_data = resp_single.json()
    assert inc_data["id"] == inc_id
    assert "title" in inc_data
    assert "severity" in inc_data
    assert "status" in inc_data
    assert "correlation_score" in inc_data
    assert inc_data["status"] in ["OPEN", "INVESTIGATING", "RESOLVED", "CLOSED"]

    # Test flexible ID lookup (e.g. stripped prefix or lowercase)
    suffix = inc_id.replace("INC-", "")
    resp_flexible = client.get(f"/api/incidents/{suffix}")
    assert resp_flexible.status_code == 200
    assert resp_flexible.json()["id"] == inc_id

    # 3. GET /api/incidents/{incident_id}/events (Returns related alerts)
    resp_events = client.get(f"/api/incidents/{inc_id}/events")
    assert resp_events.status_code == 200
    events_data = resp_events.json()
    assert isinstance(events_data, list)
    assert len(events_data) >= 1
    alert_item = events_data[0]
    assert "metric" in alert_item
    assert "severity" in alert_item
    assert "incident_id" in alert_item
    assert alert_item["incident_id"] == inc_id

    # 4. GET /api/incidents/{incident_id}/recommendations (Returns recommended actions)
    resp_recs = client.get(f"/api/incidents/{inc_id}/recommendations")
    assert resp_recs.status_code == 200
    recs_data = resp_recs.json()
    assert isinstance(recs_data, list)
    assert len(recs_data) >= 1
    rec_item = recs_data[0]
    assert "action" in rec_item
    assert "priority" in rec_item
    assert "status" in rec_item

    # 5. POST /api/incidents/{incident_id}/investigate (Starts AI investigation)
    resp_inv = client.post(f"/api/incidents/{inc_id}/investigate")
    assert resp_inv.status_code == 200
    inv_data = resp_inv.json()
    assert inv_data["status"] == "INVESTIGATING"

    # 6. POST /api/incidents/{incident_id}/resolve (Resolves incident)
    resp_res = client.post(f"/api/incidents/{inc_id}/resolve")
    assert resp_res.status_code == 200
    res_data = resp_res.json()
    assert res_data["status"] == "RESOLVED"
    assert res_data["resolved_at"] is not None

    # 7. POST /api/incidents/{incident_id}/close (Closes incident)
    resp_close = client.post(f"/api/incidents/{inc_id}/close")
    assert resp_close.status_code == 200
    close_data = resp_close.json()
    assert close_data["status"] == "CLOSED"


