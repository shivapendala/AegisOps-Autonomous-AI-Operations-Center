"""
Unit and Integration Tests for AegisOps Monitoring Simulation System.
Tests:
1. All 5 simulated microservices exist and model realistic metrics (latency, request_rate, error_rate, cpu, memory, database_connections)
2. Normal scenario maintains healthy telemetry
3. Individual failure scenarios:
   - High CPU (Order Service)
   - Database overload (PostgreSQL Database)
   - API latency spike (Authentication API)
   - Error-rate spike (Notification Service)
4. Combined Payment API failure:
   - Generates CPU (92%), DB connections (95%), Latency (2.8s), HTTP 500s (high)
   - Verifies EventCorrelationEngine clusters them into ONE unified incident
5. System recovery clears active simulated alerts and restores healthy baseline
6. REST API endpoints (/api/simulation/status, /api/simulation/scenario, /api/simulation/reset)
"""

import pytest
from monitoring.simulation import (
    SimulationEngine,
    FailureScenario,
    SIMULATED_SERVICES_SPEC,
)
from monitoring.correlation_engine import EventCorrelationEngine


def test_simulation_services_specification():
    """Verify all 5 required services are specified with baseline metrics."""
    service_names = [s["name"] for s in SIMULATED_SERVICES_SPEC]
    assert "Payment API" in service_names
    assert "Authentication API" in service_names
    assert "Order Service" in service_names
    assert "PostgreSQL Database" in service_names
    assert "Notification Service" in service_names
    assert len(service_names) == 5

    for spec in SIMULATED_SERVICES_SPEC:
        assert "base_latency" in spec
        assert "base_request_rate" in spec
        assert "base_error_rate" in spec
        assert "base_cpu" in spec
        assert "base_memory" in spec
        assert "base_db_conn" in spec


def test_simulation_engine_step_normal(db_session):
    """Verify NORMAL scenario produces healthy snapshots for all 5 services."""
    engine = SimulationEngine(
        db_factory=lambda: db_session,
        correlation_engine=EventCorrelationEngine(window_seconds=60),
    )
    res = engine.set_scenario("NORMAL")
    assert res["active_scenario"] == "NORMAL"
    assert res["is_simulation"] is True
    assert res["label"] == "DEMO/SIMULATION"

    step_data = engine.step()
    snapshots = step_data["snapshots"]
    assert len(snapshots) == 5

    for snap in snapshots:
        # Check all 6 dimensions
        assert "latency" in snap
        assert "request_rate" in snap
        assert "error_rate" in snap
        assert "cpu" in snap
        assert "memory" in snap
        assert "database_connections" in snap
        assert snap["status"] == "HEALTHY"
        assert snap["is_simulation"] is True


def test_simulation_high_cpu_scenario(db_session):
    """Verify HIGH_CPU scenario triggers CPU alert on Order Service."""
    engine = SimulationEngine(
        db_factory=lambda: db_session,
        correlation_engine=EventCorrelationEngine(window_seconds=60),
    )
    engine.set_scenario("HIGH_CPU")
    step_data = engine.step()

    order_snap = next(s for s in step_data["snapshots"] if s["service_name"] == "Order Service")
    assert order_snap["cpu"] >= 90.0
    assert order_snap["status"] == "CRITICAL"


def test_simulation_database_overload_scenario(db_session):
    """Verify DATABASE_OVERLOAD scenario triggers DB connections alert on PostgreSQL Database."""
    engine = SimulationEngine(
        db_factory=lambda: db_session,
        correlation_engine=EventCorrelationEngine(window_seconds=60),
    )
    engine.set_scenario("DATABASE_OVERLOAD")
    step_data = engine.step()

    db_snap = next(s for s in step_data["snapshots"] if s["service_name"] == "PostgreSQL Database")
    assert db_snap["database_connections"] >= 90.0
    assert db_snap["status"] == "CRITICAL"


def test_simulation_api_latency_spike_scenario(db_session):
    """Verify API_LATENCY_SPIKE scenario triggers latency surge on Authentication API."""
    engine = SimulationEngine(
        db_factory=lambda: db_session,
        correlation_engine=EventCorrelationEngine(window_seconds=60),
    )
    engine.set_scenario("API_LATENCY_SPIKE")
    step_data = engine.step()

    auth_snap = next(s for s in step_data["snapshots"] if s["service_name"] == "Authentication API")
    assert auth_snap["latency"] >= 1000.0
    assert auth_snap["status"] == "DEGRADED"


def test_simulation_error_rate_spike_scenario(db_session):
    """Verify ERROR_RATE_SPIKE scenario triggers high error rate on Notification Service."""
    engine = SimulationEngine(
        db_factory=lambda: db_session,
        correlation_engine=EventCorrelationEngine(window_seconds=60),
    )
    engine.set_scenario("ERROR_RATE_SPIKE")
    step_data = engine.step()

    notif_snap = next(s for s in step_data["snapshots"] if s["service_name"] == "Notification Service")
    assert notif_snap["error_rate"] >= 15.0
    assert notif_snap["status"] == "DEGRADED"


def test_combined_payment_failure_correlation_into_one_incident(db_session):
    """
    CRITICAL REQUIREMENT:
    Combined Payment API failure must generate:
    - CPU = 92%
    - Database connections = 95%
    - API latency = 2.8 seconds
    - HTTP 500 errors = high
    And the correlation engine must combine them into ONE single incident.
    """
    corr_engine = EventCorrelationEngine(window_seconds=60, threshold_score=60.0)
    engine = SimulationEngine(
        db_factory=lambda: db_session,
        correlation_engine=corr_engine,
    )

    # Trigger COMBINED_PAYMENT_FAILURE
    engine.set_scenario("COMBINED_PAYMENT_FAILURE")
    step_data = engine.step()

    pay_snap = next(s for s in step_data["snapshots"] if s["service_name"] == "Payment API")
    assert 91.0 <= pay_snap["cpu"] <= 95.0
    assert 94.0 <= pay_snap["database_connections"] <= 98.0
    assert 2700.0 <= pay_snap["latency"] <= 3000.0
    assert pay_snap["error_rate"] >= 14.0
    assert pay_snap["status"] == "CRITICAL"

    # Verify correlation engine combined all payment alerts into ONE active incident
    active_incs = [inc for inc in corr_engine.active_incidents.values() if inc.service == "Payment API"]
    assert len(active_incs) == 1, f"Expected exactly 1 correlated incident, got {len(active_incs)}"

    single_inc = active_incs[0]
    assert single_inc.service == "Payment API"
    # Should contain the correlated metrics
    assert "cpu_usage" in single_inc.affected_metrics
    assert "database_connections" in single_inc.affected_metrics
    assert "api_latency" in single_inc.affected_metrics
    assert "http_500_errors" in single_inc.affected_metrics
    assert len(single_inc.affected_events) == 4
    assert single_inc.correlation_score >= 60.0


def test_simulation_system_recovery(db_session):
    """Verify RECOVER_SYSTEM restores all services to HEALTHY and clears active simulated alerts."""
    engine = SimulationEngine(
        db_factory=lambda: db_session,
        correlation_engine=EventCorrelationEngine(window_seconds=60),
    )
    # First trigger failure
    engine.set_scenario("COMBINED_PAYMENT_FAILURE")
    engine.step()

    # Now recover
    res = engine.set_scenario("RECOVER_SYSTEM")
    assert res["active_scenario"] == "NORMAL"
    assert res["active_simulated_alerts"] == 0

    snap_step = engine.step()
    for snap in snap_step["snapshots"]:
        assert snap["status"] == "HEALTHY"


def test_simulation_api_endpoints(client):
    """Verify REST APIs: GET /api/simulation/status, POST /api/simulation/scenario, POST /api/simulation/reset."""
    # 1. GET status
    res = client.get("/api/simulation/status")
    assert res.status_code == 200
    data = res.json()
    assert "active_scenario" in data
    assert data["is_simulation"] is True
    assert data["label"] == "DEMO/SIMULATION"
    assert len(data["services"]) == 5

    # 2. Trigger CPU Spike
    post_res = client.post("/api/simulation/scenario", json={"scenario": "HIGH_CPU"})
    assert post_res.status_code == 200
    assert post_res.json()["active_scenario"] == "HIGH_CPU"

    # 3. Trigger Combined Payment Failure
    pay_res = client.post("/api/simulation/scenario", json={"scenario": "COMBINED_PAYMENT_FAILURE"})
    assert pay_res.status_code == 200
    assert pay_res.json()["active_scenario"] == "COMBINED_PAYMENT_FAILURE"

    # 4. Reset simulation
    reset_res = client.post("/api/simulation/reset")
    assert reset_res.status_code == 200
    assert reset_res.json()["active_scenario"] == "NORMAL"
