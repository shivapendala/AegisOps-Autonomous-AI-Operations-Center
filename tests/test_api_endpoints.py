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
    assert "title" in alert
    assert "severity" in alert
    assert "status" in alert
    assert "source" in alert

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
