"""Unit tests for AI Anomaly Detector and Pluggable LLM Service."""
import pytest
from datetime import datetime, timezone
from aegisops.ai.anomaly_detector import AnomalyDetector
from aegisops.ai.llm_service import BaseLLMService, MockLLMService, get_llm_service
from aegisops.models.events import SystemTelemetry


def test_anomaly_detector_nominal_telemetry():
    detector = AnomalyDetector()
    nominal = SystemTelemetry(
        timestamp=datetime.now(timezone.utc),
        host_name="test-host",
        cpu_percent=22.0,
        memory_percent=35.0,
        disk_percent=45.0,
        process_count=120,
    )
    result = detector.evaluate_telemetry(nominal)
    assert not result.is_anomaly
    assert result.confidence > 0.5


def test_anomaly_detector_detects_severe_spike():
    detector = AnomalyDetector()
    spike = SystemTelemetry(
        timestamp=datetime.now(timezone.utc),
        host_name="test-host",
        cpu_percent=98.5,
        memory_percent=96.0,
        disk_percent=95.0,
        process_count=450,
    )
    result = detector.evaluate_telemetry(spike)
    assert result.is_anomaly
    assert len(result.affected_metrics) > 0


def test_llm_service_interface_and_mock():
    import asyncio
    service = get_llm_service("mock")
    assert isinstance(service, BaseLLMService)
    assert isinstance(service, MockLLMService)

    incident_data = {
        "title": "CPU Exhaustion on Worker-01",
        "cpu_percent": 95.0,
        "memory_percent": 40.0,
        "disk_percent": 30.0,
    }

    analysis = asyncio.run(service.analyze_incident(incident_data))
    assert analysis.probable_root_cause != ""
    assert len(analysis.suggested_mitigation_steps) > 0
    assert analysis.provider == "mock-aegis-engine"

    remediations = asyncio.run(service.suggest_remediation(incident_data))
    assert isinstance(remediations, list)
    assert len(remediations) > 0


def test_ai_api_endpoints(client):
    info_resp = client.get("/api/v1/ai/info")
    assert info_resp.status_code == 200
    info_data = info_resp.json()
    assert "anomaly_detector" in info_data
    assert "llm_service" in info_data

    eval_resp = client.post("/api/v1/ai/evaluate", json={})
    assert eval_resp.status_code == 200
    eval_data = eval_resp.json()
    assert "is_anomaly" in eval_data
    assert "confidence" in eval_data
