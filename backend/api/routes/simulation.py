"""
Simulation and Presentation Demo Control API Endpoints.
Exposes controls for presentation drills:
- GET /api/simulation/status
- POST /api/simulation/scenario
- POST /api/simulation/reset
"""

from typing import Any, Dict
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from monitoring.simulation import simulation_engine, FailureScenario

router = APIRouter(prefix="/simulation", tags=["Simulation & Demos"])


class ScenarioTriggerRequest(BaseModel):
    scenario: str = Field(
        ...,
        description="Scenario to trigger: NORMAL, HIGH_CPU, DATABASE_OVERLOAD, API_LATENCY_SPIKE, ERROR_RATE_SPIKE, COMBINED_PAYMENT_FAILURE, RECOVER",
        example="COMBINED_PAYMENT_FAILURE",
    )


class SimulationStatusResponse(BaseModel):
    active_scenario: str
    scenario_start_time: str
    active_simulated_alerts: int
    services: list
    is_simulation: bool = True
    label: str = "DEMO/SIMULATION"


@router.get("/status", response_model=SimulationStatusResponse, summary="Get Simulation Engine Status")
def get_simulation_status():
    """Returns current simulated service telemetry, active scenario, and demo markers."""
    status_data = simulation_engine.get_status()
    # If no snapshots have been taken yet, run one step
    if not status_data.get("services"):
        simulation_engine.step()
        status_data = simulation_engine.get_status()
    return status_data


@router.post("/scenario", response_model=SimulationStatusResponse, summary="Trigger Failure Scenario")
def trigger_scenario(payload: ScenarioTriggerRequest):
    """
    Activates a specific operational failure scenario for presentation demonstrations:
    - NORMAL / RECOVER: Return all services to normal baseline
    - HIGH_CPU: Severe CPU utilization spike on Order Service
    - DATABASE_OVERLOAD: PostgreSQL connection saturation & query latency degradation
    - API_LATENCY_SPIKE: Authentication API token verification latency surge
    - ERROR_RATE_SPIKE: Notification Service delivery failure surge
    - COMBINED_PAYMENT_FAILURE: Cascading Payment API failure (CPU 92%, DB 95%, Latency 2.8s, 500 errors)
      grouped into ONE unified incident by the Correlation Engine.
    """
    result = simulation_engine.set_scenario(payload.scenario)
    return result


@router.post("/reset", response_model=SimulationStatusResponse, summary="Reset Simulation to Normal")
def reset_simulation():
    """Recovers the entire system back to clean healthy NORMAL baseline."""
    result = simulation_engine.set_scenario("NORMAL")
    return result


@router.post("/high-cpu", response_model=SimulationStatusResponse, summary="Trigger High CPU Simulation Drill")
def trigger_high_cpu():
    """Triggers severe CPU utilization overload drill across monitored services."""
    return simulation_engine.set_scenario("HIGH_CPU")


@router.post("/high-memory", response_model=SimulationStatusResponse, summary="Trigger High Memory Simulation Drill")
def trigger_high_memory():
    """Triggers memory saturation and database connection pressure drill."""
    return simulation_engine.set_scenario("HIGH_MEMORY")


@router.post("/high-disk", response_model=SimulationStatusResponse, summary="Trigger High Disk Simulation Drill")
def trigger_high_disk():
    """Triggers disk volume saturation and storage threshold breach drill."""
    return simulation_engine.set_scenario("HIGH_DISK")
