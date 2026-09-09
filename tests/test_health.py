"""Unit tests for the Health Check API."""
def test_health_check_returns_200(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["healthy", "degraded"]
    assert "AegisOps" in data["app_name"]
    assert "uptime_seconds" in data
    assert "ai_engine" in data
    assert data["ai_engine"]["provider"] == "mock"


def test_root_endpoint_returns_operational_metadata(client):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "operational"
    assert "/docs" in data["docs"]
    assert "health" in data["endpoints"]
    assert data["endpoints"]["health"] == "/api/health"
