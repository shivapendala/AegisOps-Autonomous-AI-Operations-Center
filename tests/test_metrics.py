"""Unit tests for System Telemetry and Metrics API."""
from monitoring.collector import SystemCollector


def test_system_collector_extracts_telemetry():
    collector = SystemCollector()
    telemetry = collector.collect()

    assert telemetry.cpu_percent >= 0.0
    assert telemetry.memory_percent >= 0.0
    assert telemetry.disk_percent >= 0.0
    assert telemetry.process_count > 0
    assert telemetry.host_name != ""


def test_system_collector_detailed_report():
    collector = SystemCollector()
    report = collector.get_detailed_report()

    assert "host_name" in report
    assert "memory" in report
    assert "top_processes" in report
    assert isinstance(report["top_processes"], list)


def test_metrics_current_endpoint(client):
    response = client.get("/api/v1/metrics/current")
    assert response.status_code == 200
    data = response.json()

    assert "cpu_percent" in data
    assert "memory_percent" in data
    assert "disk_percent" in data
    assert "process_count" in data


def test_metrics_diagnostics_endpoint(client):
    response = client.get("/api/v1/metrics/diagnostics")
    assert response.status_code == 200
    data = response.json()
    assert "top_processes" in data
