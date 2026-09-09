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

