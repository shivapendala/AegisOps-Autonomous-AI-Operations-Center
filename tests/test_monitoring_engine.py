"""
Comprehensive test suite for AegisOps Real-time Monitoring Engine.
Tests:
- Telemetry collection via psutil (CPU, RAM, Disk, Network, Process count, Uptime)
- Configurable thresholds (CPU: 70/90, Memory: 75/90, Disk: 80/90)
- Threshold breach detection and Alert generation
- Alert schema compliance (id, service, metric, value, threshold, severity, message, timestamp, status)
- Alert de-duplication (preventing duplicate alerts for ongoing conditions)
- Alert severity escalation (WARNING -> CRITICAL)
- Alert auto-recovery and resolution
- Simulated telemetry injection
- Database persistence of metrics and alerts
"""

from datetime import datetime, timezone
import pytest

from aegisops.models.events import SystemTelemetry
from database.models.alert import AlertModel
from database.models.metric import MetricModel
from monitoring.alert_engine import AlertRuleEngine
from monitoring.collector import SystemCollector
from monitoring.service import MonitoringService
from monitoring.thresholds import MetricThreshold, ThresholdConfig


def test_collector_extracts_all_required_metrics():
    """Verify collector harvests CPU, RAM, Disk, Network, Process count, and Uptime."""
    collector = SystemCollector()
    telemetry = collector.collect()

    assert isinstance(telemetry.cpu_percent, float)
    assert isinstance(telemetry.memory_percent, float)
    assert isinstance(telemetry.disk_percent, float)
    assert isinstance(telemetry.process_count, int)
    assert telemetry.process_count > 0
    assert isinstance(telemetry.uptime_seconds, float)
    assert telemetry.uptime_seconds > 0
    assert isinstance(telemetry.network_sent_mb, float)
    assert isinstance(telemetry.network_recv_mb, float)


def test_configurable_thresholds_defaults():
    """Verify default thresholds match exact specifications."""
    thresholds = ThresholdConfig.default()
    assert thresholds.cpu.warning == 70.0
    assert thresholds.cpu.critical == 90.0

    assert thresholds.memory.warning == 75.0
    assert thresholds.memory.critical == 90.0

    assert thresholds.disk.warning == 80.0
    assert thresholds.disk.critical == 90.0


def test_custom_threshold_configuration():
    """Verify thresholds can be configured dynamically."""
    custom = ThresholdConfig(
        cpu=MetricThreshold(warning=65.0, critical=85.0),
        memory=MetricThreshold(warning=70.0, critical=88.0),
        disk=MetricThreshold(warning=75.0, critical=85.0),
    )
    assert custom.cpu.warning == 65.0
    assert custom.cpu.critical == 85.0


def test_nominal_metrics_produce_no_alerts():
    """Nominal system telemetry should trigger zero alerts."""
    engine = AlertRuleEngine()
    nominal = SystemTelemetry(
        host_name="test-server",
        cpu_percent=45.0,
        memory_percent=55.0,
        disk_percent=60.0,
        process_count=150,
        uptime_seconds=3600.0,
    )
    new_alerts, resolved_alerts = engine.evaluate(nominal)
    assert len(new_alerts) == 0
    assert len(resolved_alerts) == 0
    assert len(engine.get_active_alerts()) == 0


def test_threshold_breach_generates_alert_with_required_fields():
    """
    When CPU exceeds 70%, a WARNING alert must be generated with:
    id, service, metric, value, threshold, severity, message, timestamp, status.
    """
    engine = AlertRuleEngine(service_name="payment-svc")
    high_cpu = SystemTelemetry(
        host_name="test-server",
        cpu_percent=78.5,
        memory_percent=50.0,
        disk_percent=50.0,
        process_count=150,
        uptime_seconds=3600.0,
    )
    new_alerts, resolved_alerts = engine.evaluate(high_cpu)
    assert len(new_alerts) == 1
    alert = new_alerts[0]

    # Verify all required fields
    required_fields = ["id", "service", "metric", "value", "threshold", "severity", "message", "timestamp", "status"]
    for field in required_fields:
        assert field in alert, f"Missing required field '{field}' in alert"

    assert alert["service"] == "payment-svc"
    assert alert["metric"] == "cpu_usage"
    assert alert["value"] == 78.5
    assert alert["threshold"] == 70.0
    assert alert["severity"] == "WARNING"
    assert alert["status"] == "ACTIVE"
    assert "78.5%" in alert["message"]


def test_alert_deduplication():
    """Subsequent cycles with continuing threshold breach must NOT generate duplicate alerts."""
    engine = AlertRuleEngine(service_name="auth-svc")

    # Tick 1: Trigger warning alert
    t1 = SystemTelemetry(
        host_name="auth-01",
        cpu_percent=75.0,
        memory_percent=40.0,
        disk_percent=50.0,
        process_count=100,
        uptime_seconds=100.0,
    )
    new_alerts_1, _ = engine.evaluate(t1)
    assert len(new_alerts_1) == 1
    first_id = new_alerts_1[0]["id"]

    # Tick 2: Same condition still ongoing (CPU 76.0%) -> Must be suppressed (deduplicated)
    t2 = SystemTelemetry(
        host_name="auth-01",
        cpu_percent=76.0,
        memory_percent=42.0,
        disk_percent=50.0,
        process_count=100,
        uptime_seconds=102.0,
    )
    new_alerts_2, _ = engine.evaluate(t2)
    assert len(new_alerts_2) == 0, "Duplicate alert was wrongly created on tick 2!"

    # Tick 3: Same condition still ongoing (CPU 74.5%) -> Must be suppressed
    t3 = SystemTelemetry(
        host_name="auth-01",
        cpu_percent=74.5,
        memory_percent=41.0,
        disk_percent=50.0,
        process_count=100,
        uptime_seconds=104.0,
    )
    new_alerts_3, _ = engine.evaluate(t3)
    assert len(new_alerts_3) == 0, "Duplicate alert was wrongly created on tick 3!"

    # Exactly 1 active alert tracked
    active = engine.get_active_alerts()
    assert len(active) == 1
    assert active[0]["id"] == first_id


def test_alert_escalation_from_warning_to_critical():
    """If condition deteriorates from warning to critical, an escalated CRITICAL alert is generated."""
    engine = AlertRuleEngine(service_name="api-gateway")

    # Tick 1: Warning level (Memory 78%)
    t1 = SystemTelemetry(
        host_name="gw-01",
        cpu_percent=30.0,
        memory_percent=78.0,
        disk_percent=40.0,
        process_count=100,
        uptime_seconds=500.0,
    )
    new_alerts_1, _ = engine.evaluate(t1)
    assert len(new_alerts_1) == 1
    assert new_alerts_1[0]["severity"] == "WARNING"

    # Tick 2: Critical spike (Memory 93%)
    t2 = SystemTelemetry(
        host_name="gw-01",
        cpu_percent=35.0,
        memory_percent=93.0,
        disk_percent=40.0,
        process_count=100,
        uptime_seconds=502.0,
    )
    new_alerts_2, resolved_2 = engine.evaluate(t2)
    assert len(new_alerts_2) == 1
    assert new_alerts_2[0]["severity"] == "CRITICAL"
    assert new_alerts_2[0]["threshold"] == 90.0

    # Old warning alert should be superseded
    assert len(resolved_2) == 1
    assert resolved_2[0]["status"] == "SUPERSEDED"


def test_alert_auto_recovery_when_metric_normalizes():
    """When a breached metric returns below threshold, active alert transitions to RESOLVED."""
    engine = AlertRuleEngine(service_name="database-node")

    # Tick 1: High disk utilization (85%)
    t1 = SystemTelemetry(
        host_name="db-01",
        cpu_percent=30.0,
        memory_percent=40.0,
        disk_percent=85.0,
        process_count=80,
        uptime_seconds=1000.0,
    )
    new_alerts_1, _ = engine.evaluate(t1)
    assert len(new_alerts_1) == 1
    assert len(engine.get_active_alerts()) == 1

    # Tick 2: Disk cleaned up (65%)
    t2 = SystemTelemetry(
        host_name="db-01",
        cpu_percent=30.0,
        memory_percent=40.0,
        disk_percent=65.0,
        process_count=80,
        uptime_seconds=1002.0,
    )
    new_alerts_2, resolved_2 = engine.evaluate(t2)
    assert len(new_alerts_2) == 0
    assert len(resolved_2) == 1
    assert resolved_2[0]["status"] == "RESOLVED"
    assert "resolved_at" in resolved_2[0]

    # No more active alerts
    assert len(engine.get_active_alerts()) == 0


def test_monitoring_service_simulation_and_database_persistence(db_session):
    """
    Test MonitoringService step execution with simulated high CPU/memory values
    and verify persistence into PostgreSQL / SQLAlchemy tables.
    """
    # Create service using isolated test db session factory
    service = MonitoringService(
        interval_seconds=2.0,
        db_factory=lambda: db_session,
        service_name="simulated-cluster",
    )

    # Injected simulated telemetry with High CPU (92% - CRITICAL) and High Memory (82% - WARNING)
    simulated_spike = SystemTelemetry(
        host_name="sim-node-01",
        cpu_percent=92.0,
        memory_percent=82.0,
        disk_percent=45.0,
        process_count=210,
        uptime_seconds=7200.0,
        network_sent_mb=320.5,
        network_recv_mb=890.2,
    )

    telemetry, new_alerts, resolved_alerts = service.step(telemetry_override=simulated_spike)

    assert telemetry.cpu_percent == 92.0
    assert telemetry.memory_percent == 82.0
    assert len(new_alerts) == 2

    severities = {a["metric"]: a["severity"] for a in new_alerts}
    assert severities["cpu_usage"] == "CRITICAL"
    assert severities["memory_usage"] == "WARNING"

    # Verify metrics persisted to database
    cpu_metrics = db_session.query(MetricModel).filter(MetricModel.metric_name == "cpu_usage").all()
    assert len(cpu_metrics) > 0
    assert any(m.value == 92.0 for m in cpu_metrics)

    uptime_metrics = db_session.query(MetricModel).filter(MetricModel.metric_name == "system_uptime").all()
    assert len(uptime_metrics) > 0
    assert any(m.value == 7200.0 for m in uptime_metrics)

    # Verify alerts persisted to database
    db_alerts = db_session.query(AlertModel).filter(AlertModel.service == "simulated-cluster").all()
    assert len(db_alerts) >= 2
    alert_metrics = {a.metric: a.severity for a in db_alerts}
    assert alert_metrics.get("cpu_usage") == "CRITICAL"
    assert alert_metrics.get("memory_usage") == "WARNING"
