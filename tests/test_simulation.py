"""
tests/test_simulation.py
Validates Payment Failure Simulation as specified in Step 16:
- Test 4: Payment Failure Simulation
  -> 4 alerts
  -> 1 incident
"""

import pytest


def test_test4_payment_failure_simulation_emits_4_alerts_and_1_incident(client):
    """
    Test 4:
    Payment Failure Simulation
    -> 4 alerts
    -> 1 incident

    Triggers POST /api/simulation/payment-failure and checks:
    - 4 cascading telemetry steps (CPU, DB, Latency, HTTP 500)
    - 4 alerts generated
    - Clustered by Correlation Engine into exactly 1 Incident
    """
    response = client.post("/api/simulation/payment-failure")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "success"
    assert "PAYMENT_FAILURE" in data["scenario"]

    # Verify 4 alerts were generated
    alerts_count = data.get("alerts_count", len(data.get("alerts", [])))
    assert alerts_count == 4, f"Expected 4 alerts, got {alerts_count}"

    # Verify 1 unified incident was created
    incident = data.get("incident")
    assert incident is not None
    assert incident["id"] is not None
    assert incident["service"] == "Payment API"
    assert incident["severity"] == "CRITICAL"
    assert incident["status"] in ("OPEN", "INVESTIGATING")

    # Fetch incident directly from API to confirm single unified incident persistence
    inc_res = client.get(f"/api/incidents/{incident['id']}")
    assert inc_res.status_code == 200
    fetched_inc = inc_res.json()
    assert fetched_inc["service"] in ("Payment API", "payment-api")
    assert len(fetched_inc["affected_events"]) == 4
