"""
AegisOps Real-Time Monitoring Service.
Decoupled service running on a 2-second sampling interval.
Collects psutil system telemetry, evaluates operational thresholds,
persists metric time-series to PostgreSQL, and records deduplicated alerts.
"""

import asyncio
from datetime import datetime, timezone
import logging
from typing import Callable, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from aegisops.models.events import SystemTelemetry
from database.models.alert import AlertModel
from database.models.metric import MetricModel
from database.session import SessionLocal
from monitoring.alert_engine import AlertRuleEngine
from monitoring.collector import SystemCollector
from monitoring.thresholds import ThresholdConfig

logger = logging.getLogger("aegisops.monitoring.service")


class MonitoringService:
    """
    Autonomous monitoring service.
    Orchestrates telemetry harvesting, PostgreSQL persistence, and threshold-based alert generation.
    """

    def __init__(
        self,
        interval_seconds: float = 2.0,
        thresholds: Optional[ThresholdConfig] = None,
        db_factory: Optional[Callable[[], Session]] = None,
        service_name: str = "system-host",
    ):
        self.interval_seconds = interval_seconds
        self.service_name = service_name
        self.collector = SystemCollector()
        self.alert_engine = AlertRuleEngine(thresholds=thresholds, service_name=service_name)
        self.db_factory = db_factory or SessionLocal

        self._running: bool = False
        self._task: Optional[asyncio.Task] = None
        self._recent_telemetry: List[SystemTelemetry] = []
        self._max_in_memory_history: int = 120

    def step(
        self, telemetry_override: Optional[SystemTelemetry] = None
    ) -> Tuple[SystemTelemetry, List[dict], List[dict]]:
        """
        Executes a single monitoring cycle.
        If telemetry_override is provided, uses that snapshot instead of probing psutil.
        Enables deterministic testing with simulated high CPU/memory/disk values.
        """
        # 1. Harvest telemetry
        telemetry = telemetry_override or self.collector.collect()

        # Cache in-memory
        self._recent_telemetry.append(telemetry)
        if len(self._recent_telemetry) > self._max_in_memory_history:
            self._recent_telemetry.pop(0)

        # 2. Evaluate thresholds and get new / resolved alerts
        new_alerts, resolved_alerts = self.alert_engine.evaluate(telemetry)

        # 3. Persist metrics and alerts to PostgreSQL
        self._persist_to_database(telemetry, new_alerts, resolved_alerts)

        # 4. Broadcast real-time events to connected dashboard clients
        self._broadcast_updates(telemetry, new_alerts, resolved_alerts)

        return telemetry, new_alerts, resolved_alerts

    def _broadcast_updates(
        self,
        telemetry: SystemTelemetry,
        new_alerts: List[dict],
        resolved_alerts: List[dict],
    ) -> None:
        """Dispatches metrics and alert changes over WebSocket."""
        try:
            from backend.core.websocket_manager import ws_manager
            if ws_manager.client_count == 0:
                return

            loop = None
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                pass

            if loop and loop.is_running():
                loop.create_task(ws_manager.broadcast_metrics(telemetry))
                for a in new_alerts:
                    loop.create_task(ws_manager.broadcast_alert(a, "NEW_ALERT"))
                for r in resolved_alerts:
                    loop.create_task(ws_manager.broadcast_alert(r, "ALERT_RESOLVED"))
        except Exception as e:
            logger.debug("Failed to broadcast monitoring update via WebSocket: %s", e)

    def _persist_to_database(
        self,
        telemetry: SystemTelemetry,
        new_alerts: List[dict],
        resolved_alerts: List[dict],
    ) -> None:
        """Stores collected metrics and alert changes in PostgreSQL."""
        if not self.db_factory:
            return

        db: Optional[Session] = None
        try:
            db = self.db_factory()

            # Record standard timeseries metrics
            now = telemetry.timestamp or datetime.now(timezone.utc)
            metrics_records = [
                MetricModel(
                    metric_name="cpu_usage",
                    value=float(telemetry.cpu_percent),
                    unit="%",
                    dimensions={"host": telemetry.host_name, "type": "processor"},
                    timestamp=now,
                ),
                MetricModel(
                    metric_name="memory_usage",
                    value=float(telemetry.memory_percent),
                    unit="%",
                    dimensions={"host": telemetry.host_name, "used_gb": telemetry.memory_used_gb},
                    timestamp=now,
                ),
                MetricModel(
                    metric_name="disk_usage",
                    value=float(telemetry.disk_percent),
                    unit="%",
                    dimensions={"host": telemetry.host_name, "free_gb": telemetry.disk_free_gb},
                    timestamp=now,
                ),
                MetricModel(
                    metric_name="process_count",
                    value=float(telemetry.process_count),
                    unit="processes",
                    dimensions={"host": telemetry.host_name},
                    timestamp=now,
                ),
                MetricModel(
                    metric_name="system_uptime",
                    value=float(telemetry.uptime_seconds),
                    unit="seconds",
                    dimensions={"host": telemetry.host_name},
                    timestamp=now,
                ),
                MetricModel(
                    metric_name="network_sent_mb",
                    value=float(telemetry.network_sent_mb),
                    unit="MB",
                    dimensions={"host": telemetry.host_name},
                    timestamp=now,
                ),
                MetricModel(
                    metric_name="network_recv_mb",
                    value=float(telemetry.network_recv_mb),
                    unit="MB",
                    dimensions={"host": telemetry.host_name},
                    timestamp=now,
                ),
            ]
            db.add_all(metrics_records)

            # Persist newly triggered alerts
            for alert_dict in new_alerts:
                alert_model = AlertModel(
                    service=alert_dict["service"],
                    metric=alert_dict["metric"],
                    value=alert_dict["value"],
                    threshold=alert_dict["threshold"],
                    severity=alert_dict["severity"],
                    message=alert_dict["message"],
                    status=alert_dict["status"],
                    source="psutil-monitoring-engine",
                    timestamp=alert_dict["timestamp"],
                )
                db.add(alert_model)

            # Update resolved alerts in database
            for resolved_dict in resolved_alerts:
                db.query(AlertModel).filter(
                    AlertModel.service == resolved_dict["service"],
                    AlertModel.metric == resolved_dict["metric"],
                    AlertModel.status == "ACTIVE",
                ).update(
                    {
                        "status": "RESOLVED",
                        "resolved_at": resolved_dict.get("resolved_at", datetime.now(timezone.utc)),
                    }
                )

            db.commit()
        except Exception as exc:
            if db:
                db.rollback()
            logger.error("Failed to persist telemetry/alerts to database: %s", exc)
        finally:
            if db:
                db.close()

    async def start(self) -> None:
        """Starts the asynchronous 2-second background monitoring loop."""
        if self._running:
            return
        self._running = True
        logger.info(
            "Starting MonitoringService loop (interval: %.1fs, service: %s)...",
            self.interval_seconds,
            self.service_name,
        )

        async def _loop():
            while self._running:
                try:
                    self.step()
                except Exception as err:
                    logger.error("Error during monitoring loop execution: %s", err, exc_info=True)
                await asyncio.sleep(self.interval_seconds)

        self._task = asyncio.create_task(_loop())

    async def stop(self) -> None:
        """Stops the background monitoring loop."""
        if not self._running:
            return
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("MonitoringService loop stopped.")

    def get_latest_telemetry(self) -> Optional[SystemTelemetry]:
        """Returns the most recent harvested telemetry snapshot."""
        return self._recent_telemetry[-1] if self._recent_telemetry else None

    def get_active_alerts(self) -> List[dict]:
        """Returns all currently open threshold alerts."""
        return self.alert_engine.get_active_alerts()
