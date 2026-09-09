"""
Alert Rule Evaluation and De-duplication Engine.
Applies warning and critical thresholds against telemetry streams,
generates structured alerts, and suppresses duplicates for ongoing conditions.
"""

from datetime import datetime, timezone
import logging
from typing import Dict, List, Optional, Tuple
import uuid

from aegisops.models.events import SystemTelemetry
from monitoring.thresholds import ThresholdConfig, MetricThreshold

logger = logging.getLogger("aegisops.monitoring.alert_engine")


class AlertRuleEngine:
    """
    Evaluates telemetry against operational thresholds and deduplicates alerts.
    """

    def __init__(self, thresholds: Optional[ThresholdConfig] = None, service_name: str = "system-host"):
        self.thresholds = thresholds or ThresholdConfig.default()
        self.service_name = service_name
        # Maps (service, metric) -> active alert dict
        self._active_alerts: Dict[Tuple[str, str], dict] = {}

    def _check_metric(
        self,
        metric_name: str,
        value: float,
        threshold_rule: MetricThreshold,
        unit: str = "%",
    ) -> Optional[Tuple[str, float, str]]:
        """
        Evaluates a metric against critical and warning thresholds.
        Returns (severity, threshold_value, message) if breached, or None if nominal.
        """
        if value >= threshold_rule.critical:
            msg = (
                f"{metric_name} reached critical level at {value:.1f}{unit} "
                f"(critical threshold: {threshold_rule.critical:.1f}{unit})"
            )
            return ("CRITICAL", threshold_rule.critical, msg)
        elif value >= threshold_rule.warning:
            msg = (
                f"{metric_name} exceeded warning threshold at {value:.1f}{unit} "
                f"(warning threshold: {threshold_rule.warning:.1f}{unit})"
            )
            return ("WARNING", threshold_rule.warning, msg)
        return None

    def evaluate(self, telemetry: SystemTelemetry) -> Tuple[List[dict], List[dict]]:
        """
        Evaluates current telemetry snapshot.
        Returns:
            new_alerts: list of newly generated or escalated alerts
            resolved_alerts: list of alerts that have recovered below threshold
        """
        checks = [
            ("cpu_usage", telemetry.cpu_percent, self.thresholds.cpu),
            ("memory_usage", telemetry.memory_percent, self.thresholds.memory),
            ("disk_usage", telemetry.disk_percent, self.thresholds.disk),
        ]

        new_alerts: List[dict] = []
        resolved_alerts: List[dict] = []
        now = datetime.now(timezone.utc)

        for metric_name, value, threshold_rule in checks:
            breach = self._check_metric(metric_name, value, threshold_rule)
            key = (self.service_name, metric_name)
            active_alert = self._active_alerts.get(key)

            if breach is not None:
                severity, threshold_val, message = breach

                if active_alert is None:
                    # New condition breach: create new alert
                    alert_id = f"ALT-{uuid.uuid4().hex[:8].upper()}"
                    alert = {
                        "id": alert_id,
                        "service": self.service_name,
                        "metric": metric_name,
                        "value": round(value, 2),
                        "threshold": round(threshold_val, 2),
                        "severity": severity,
                        "message": message,
                        "timestamp": now,
                        "status": "ACTIVE",
                    }
                    self._active_alerts[key] = alert
                    new_alerts.append(alert)
                    logger.warning("New Alert generated: [%s] %s - %s", severity, metric_name, message)

                elif active_alert["severity"] != severity:
                    # Severity change (e.g. escalated from WARNING to CRITICAL or vice versa)
                    active_alert["status"] = "SUPERSEDED"
                    active_alert["resolved_at"] = now
                    resolved_alerts.append(active_alert)

                    alert_id = f"ALT-{uuid.uuid4().hex[:8].upper()}"
                    alert = {
                        "id": alert_id,
                        "service": self.service_name,
                        "metric": metric_name,
                        "value": round(value, 2),
                        "threshold": round(threshold_val, 2),
                        "severity": severity,
                        "message": message,
                        "timestamp": now,
                        "status": "ACTIVE",
                    }
                    self._active_alerts[key] = alert
                    new_alerts.append(alert)
                    logger.warning("Alert escalated: [%s] %s - %s", severity, metric_name, message)

                else:
                    # Condition continues at the same severity -> DEDUPLICATE: do not create duplicate alert!
                    # Silently update current observed value in place
                    active_alert["value"] = round(value, 2)
                    active_alert["message"] = message

            else:
                # Nominal condition: if an active alert was open, resolve it
                if active_alert is not None:
                    active_alert["status"] = "RESOLVED"
                    active_alert["resolved_at"] = now
                    resolved_alerts.append(active_alert)
                    del self._active_alerts[key]
                    logger.info("Alert auto-resolved: %s on %s", metric_name, self.service_name)

        return new_alerts, resolved_alerts

    def get_active_alerts(self) -> List[dict]:
        """Returns all currently active alerts."""
        return list(self._active_alerts.values())

    def clear(self) -> None:
        """Resets active alert tracking."""
        self._active_alerts.clear()
