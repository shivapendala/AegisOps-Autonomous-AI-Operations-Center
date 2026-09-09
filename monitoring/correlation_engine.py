"""
AegisOps Event Correlation Engine.
Deterministic grouping of cascading, related alerts into unified incidents.
Avoids alert fatigue by clustering alerts across service, time-window, metric affinity, and severity.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional, Set, Tuple
import uuid

logger = logging.getLogger("aegisops.monitoring.correlation_engine")

# Metric aliases dictionary for normalizing user and system telemetry keys
METRIC_ALIASES: Dict[str, str] = {
    "cpu": "cpu_usage",
    "cpu_percent": "cpu_usage",
    "cpu_load": "cpu_usage",
    "processor": "cpu_usage",
    "memory": "memory_usage",
    "ram": "memory_usage",
    "mem": "memory_usage",
    "db_connections": "database_connections",
    "db_connection": "database_connections",
    "db_conn": "database_connections",
    "database_connection": "database_connections",
    "connection_pool": "database_connections",
    "api_latency": "api_latency",
    "latency": "api_latency",
    "response_time": "api_latency",
    "latency_p99": "api_latency",
    "p99_latency": "api_latency",
    "http_500": "http_500_errors",
    "http_500_error": "http_500_errors",
    "http_500_errors": "http_500_errors",
    "500_errors": "http_500_errors",
    "500_error": "http_500_errors",
    "http_5xx": "http_500_errors",
    "error_rate": "http_500_errors",
    "http_error_rate": "http_500_errors",
    "disk": "disk_usage",
    "disk_percent": "disk_usage",
}


def normalize_metric_name(metric: str) -> str:
    """Normalizes raw metric names into standard snake_case tokens."""
    m = str(metric).lower().strip().replace(" ", "_").replace("-", "_")
    return METRIC_ALIASES.get(m, m)


# Metric relationship knowledge base (deterministic affinity groups)
# Metrics within the same cluster or linked clusters are semantically related.
RELATED_METRIC_CLUSTERS: List[Set[str]] = [
    # Cascading Web API, Application Tier & Database Layer (CPU, DB, Latency, HTTP 500)
    {
        "cpu_usage",
        "memory_usage",
        "database_connections",
        "api_latency",
        "http_500_errors",
        "request_timeout",
        "slow_queries",
        "db_latency",
        "load_average",
        "thread_count",
    },
    # System Compute & Process
    {"cpu_usage", "memory_usage", "process_count", "thread_count", "load_average"},
    # Database Layer
    {
        "database_connections",
        "db_latency",
        "query_time",
        "slow_queries",
        "memory_usage",
        "disk_usage",
    },
    # Storage & I/O
    {"disk_usage", "disk_io", "disk_iops", "disk_free_gb", "disk_read", "disk_write"},
    # Network
    {"network_sent", "network_recv", "network_latency", "packet_drop", "connection_errors"},
]


def are_metrics_related(metric_a: str, metric_b: str) -> bool:
    """Checks whether two metrics belong to a shared operational relationship cluster."""
    ma = normalize_metric_name(metric_a)
    mb = normalize_metric_name(metric_b)
    if ma == mb:
        return True

    for cluster in RELATED_METRIC_CLUSTERS:
        norm_cluster = {normalize_metric_name(item) for item in cluster}
        if ma in norm_cluster and mb in norm_cluster:
            return True
        if ma in cluster and mb in cluster:
            return True
    return False


def are_severities_related(severity_a: str, severity_b: str) -> bool:
    """
    Checks whether two severities have an operational relationship.
    CRITICAL-CRITICAL, CRITICAL-HIGH, HIGH-HIGH, WARNING-HIGH, etc.
    """
    sa = severity_a.upper().strip()
    sb = severity_b.upper().strip()
    if sa == sb:
        return True

    high_critical = {"CRITICAL", "HIGH"}
    warning_high = {"WARNING", "HIGH", "MEDIUM"}
    operational_alarms = {"CRITICAL", "HIGH", "WARNING", "MEDIUM"}

    if sa in high_critical and sb in high_critical:
        return True
    if sa in warning_high and sb in warning_high:
        return True
    if sa in operational_alarms and sb in operational_alarms:
        return True

    return False


@dataclass
class CorrelatedIncident:
    """Represents a unified operational incident grouping multiple related alerts."""

    id: str
    title: str
    service: str
    severity: str
    status: str
    correlation_score: float
    probable_cause: str
    affected_metrics: List[str] = field(default_factory=list)
    affected_events: List[Dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "service": self.service,
            "severity": self.severity,
            "status": self.status,
            "correlation_score": round(self.correlation_score, 2),
            "probable_cause": self.probable_cause,
            "affected_metrics": list(self.affected_metrics),
            "affected_events": list(self.affected_events),
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else str(self.created_at),
            "updated_at": self.updated_at.isoformat() if isinstance(self.updated_at, datetime) else str(self.updated_at),
        }


class EventCorrelationEngine:
    """
    Deterministic Event Correlation Engine.
    Evaluates incoming alerts against active incidents within a configurable time window
    using 4-factor scoring:
        - Same service: +30
        - Same time window: +25
        - Related metrics: +30
        - Severity relationship: +15
    Threshold: score >= 60 merges alert into existing incident.
    """

    # Scoring weights
    WEIGHT_SAME_SERVICE = 30.0
    WEIGHT_TIME_WINDOW = 25.0
    WEIGHT_RELATED_METRICS = 30.0
    WEIGHT_SEVERITY_RELATION = 15.0

    SEVERITY_ORDER = {
        "INFO": 1,
        "LOW": 2,
        "MEDIUM": 3,
        "WARNING": 4,
        "HIGH": 5,
        "CRITICAL": 6,
    }

    def __init__(
        self,
        window_seconds: int = 60,
        threshold_score: float = 60.0,
    ):
        self.window_seconds = window_seconds
        self.threshold_score = threshold_score
        # Active open incidents tracked in memory: id -> CorrelatedIncident
        self.active_incidents: Dict[str, CorrelatedIncident] = {}
        # Set of seen alert event keys for duplicate prevention: (alert_id) or (service, metric, value, timestamp_rounded)
        self._seen_alert_ids: Set[str] = set()

    def calculate_correlation_score(
        self,
        alert: Dict[str, Any],
        incident: CorrelatedIncident,
    ) -> Tuple[float, Dict[str, float]]:
        """
        Calculates correlation score (0 to 100) between an incoming alert and an active incident.
        Returns:
            total_score: float between 0 and 100
            breakdown: dict of individual factor scores
        """
        breakdown = {
            "same_service": 0.0,
            "time_window": 0.0,
            "related_metrics": 0.0,
            "severity_relationship": 0.0,
        }

        # 1. Same service correlation (+30)
        alert_service = str(alert.get("service", "")).strip().lower().replace("-", "_").replace(" ", "_")
        inc_service = str(incident.service).strip().lower().replace("-", "_").replace(" ", "_")
        if alert_service and inc_service and alert_service == inc_service:
            breakdown["same_service"] = self.WEIGHT_SAME_SERVICE

        # 2. Time-window correlation (+25)
        # Check time delta between alert and incident updated_at / created_at
        alert_time = alert.get("timestamp")
        if isinstance(alert_time, str):
            try:
                alert_time = datetime.fromisoformat(alert_time)
            except Exception:
                alert_time = datetime.now(timezone.utc)
        elif not isinstance(alert_time, datetime):
            alert_time = datetime.now(timezone.utc)

        if alert_time.tzinfo is None:
            alert_time = alert_time.replace(tzinfo=timezone.utc)

        inc_time = incident.updated_at
        if inc_time.tzinfo is None:
            inc_time = inc_time.replace(tzinfo=timezone.utc)

        time_diff = abs((alert_time - inc_time).total_seconds())
        if time_diff <= self.window_seconds:
            breakdown["time_window"] = self.WEIGHT_TIME_WINDOW

        # 3. Related metric correlation (+30)
        # Check if alert metric is related to any metric already in the incident
        alert_metric = str(alert.get("metric", "")).strip()
        metric_matched = False
        for inc_metric in incident.affected_metrics:
            if are_metrics_related(alert_metric, inc_metric):
                metric_matched = True
                break

        if metric_matched:
            breakdown["related_metrics"] = self.WEIGHT_RELATED_METRICS

        # 4. Severity correlation (+15)
        alert_sev = str(alert.get("severity", "WARNING")).strip()
        if are_severities_related(alert_sev, incident.severity):
            breakdown["severity_relationship"] = self.WEIGHT_SEVERITY_RELATION

        total_score = sum(breakdown.values())
        return total_score, breakdown

    def _is_duplicate_event(self, alert: Dict[str, Any]) -> bool:
        """
        Checks whether the alert has already been recorded or is an identical duplicate event.
        """
        alert_id = alert.get("id")
        if alert_id and str(alert_id) in self._seen_alert_ids:
            return True

        # Secondary signature check: service + metric + value + timestamp minute
        service = alert.get("service", "")
        metric = alert.get("metric", "")
        value = alert.get("value", "")
        ts = alert.get("timestamp")
        ts_str = ts.isoformat()[:16] if isinstance(ts, datetime) else str(ts)[:16]
        sig = f"{service}:{metric}:{value}:{ts_str}"
        if sig in self._seen_alert_ids:
            return True

        return False

    def _mark_seen(self, alert: Dict[str, Any]) -> None:
        """Records an alert signature to avoid duplicate reprocessing."""
        alert_id = alert.get("id")
        if alert_id:
            self._seen_alert_ids.add(str(alert_id))
        service = alert.get("service", "")
        metric = alert.get("metric", "")
        value = alert.get("value", "")
        ts = alert.get("timestamp")
        ts_str = ts.isoformat()[:16] if isinstance(ts, datetime) else str(ts)[:16]
        sig = f"{service}:{metric}:{value}:{ts_str}"
        self._seen_alert_ids.add(sig)

    def _determine_highest_severity(self, sev_a: str, sev_b: str) -> str:
        """Returns the higher of two severity levels."""
        rank_a = self.SEVERITY_ORDER.get(sev_a.upper(), 1)
        rank_b = self.SEVERITY_ORDER.get(sev_b.upper(), 1)
        return sev_a.upper() if rank_a >= rank_b else sev_b.upper()

    def _synthesize_title(self, service: str, metrics: List[str]) -> str:
        """Synthesizes an intuitive human-readable incident title."""
        svc_name = service.replace("-", " ").replace("_", " ").title()

        # Check domain-specific patterns using normalized metrics
        metric_set = {normalize_metric_name(m) for m in metrics}
        if {"api_latency", "http_500_errors"}.issubset(metric_set) or (
            "database_connections" in metric_set and ("api_latency" in metric_set or "http_500_errors" in metric_set)
        ) or (
            "cpu_usage" in metric_set and "database_connections" in metric_set
        ):
            return f"{svc_name} degradation"
        elif "database_connections" in metric_set or "db_latency" in metric_set:
            return f"{svc_name} database contention & connection degradation"
        elif "cpu_usage" in metric_set and "memory_usage" in metric_set:
            return f"{svc_name} compute resource exhaustion"
        elif "disk_usage" in metric_set:
            return f"{svc_name} storage threshold critical"
        elif "cpu_usage" in metric_set:
            return f"{svc_name} elevated CPU load"
        elif "memory_usage" in metric_set:
            return f"{svc_name} elevated memory pressure"
        else:
            primary_metric = metrics[0].replace("_", " ").title() if metrics else "Service"
            return f"{svc_name} {primary_metric} degradation"

    def _infer_probable_cause(self, alerts: List[Dict[str, Any]]) -> str:
        """
        Infers the most probable root cause deterministically based on
        chronological leading alert, resource saturation signatures, and severity.
        """
        if not alerts:
            return "Unknown root cause"

        service = alerts[0].get("service", "service") if alerts else "service"
        metric_names = {normalize_metric_name(a.get("metric", "")) for a in alerts}
        if "database_connections" in metric_names and (
            "api_latency" in metric_names or "http_500_errors" in metric_names or "cpu_usage" in metric_names
        ):
            return f"Resource saturation: Database connection pool exhaustion and cascading request contention on {service}"

        # Find earliest alert or highest severity alert
        sorted_by_time = sorted(
            alerts,
            key=lambda a: a.get("timestamp") if isinstance(a.get("timestamp"), datetime) else datetime.min.replace(tzinfo=timezone.utc),
        )
        leading = sorted_by_time[0]
        metric = leading.get("metric", "metric")
        value = leading.get("value", "")
        service = leading.get("service", "service")

        affected = [a.get("metric") for a in alerts if a.get("metric") != metric]
        cascade_desc = f", cascading into {', '.join(affected)}" if affected else ""

        return (
            f"Resource saturation: Initial breach observed on {service} "
            f"({metric} = {value}){cascade_desc}."
        )

    def _sanitize_event(self, alert: Dict[str, Any]) -> Dict[str, Any]:
        """Ensures all values in alert dictionary (such as datetimes) are JSON serializable."""
        clean = {}
        for k, v in alert.items():
            if isinstance(v, datetime):
                clean[k] = v.isoformat()
            else:
                clean[k] = v
        return clean

    def process_alert(self, alert: Dict[str, Any]) -> Tuple[Optional[CorrelatedIncident], bool]:
        """
        Processes an incoming alert.
        Checks active incidents for correlation:
            - If duplicate: returns None, False (suppressed)
            - If score >= threshold_score: merges into existing incident (returns incident, False)
            - If score < threshold_score or no active incident: creates new incident (returns incident, True)

        Returns:
            (incident, is_new_incident)
        """
        # 1. Duplicate check
        if self._is_duplicate_event(alert):
            logger.info("Duplicate alert event detected and suppressed: %s", alert.get("id"))
            return None, False

        self._mark_seen(alert)

        # Parse alert timestamp
        alert_time = alert.get("timestamp")
        if isinstance(alert_time, str):
            try:
                alert_time = datetime.fromisoformat(alert_time)
            except Exception:
                alert_time = datetime.now(timezone.utc)
        elif not isinstance(alert_time, datetime):
            alert_time = datetime.now(timezone.utc)

        if alert_time.tzinfo is None:
            alert_time = alert_time.replace(tzinfo=timezone.utc)

        sanitized_alert = self._sanitize_event(alert)

        # 2. Evaluate correlation against active incidents
        best_match: Optional[CorrelatedIncident] = None
        best_score = 0.0

        for inc_id, incident in list(self.active_incidents.items()):
            if incident.status.upper() == "RESOLVED":
                continue

            score, _ = self.calculate_correlation_score(alert, incident)
            if score >= self.threshold_score and score > best_score:
                best_score = score
                best_match = incident

        # 3. If correlated match found: Merge into existing incident
        if best_match is not None:
            alert_metric = str(alert.get("metric", "")).strip()
            if alert_metric and alert_metric not in best_match.affected_metrics:
                best_match.affected_metrics.append(alert_metric)

            # Record sanitized event in affected_events
            best_match.affected_events.append(sanitized_alert)

            # Escalate incident severity if alert is higher
            alert_sev = str(alert.get("severity", "WARNING"))
            best_match.severity = self._determine_highest_severity(best_match.severity, alert_sev)

            # Update timestamp and correlation score
            best_match.updated_at = alert_time
            best_match.correlation_score = round(max(best_match.correlation_score, best_score), 2)

            # Re-synthesize title and probable cause
            best_match.title = self._synthesize_title(best_match.service, best_match.affected_metrics)
            best_match.probable_cause = self._infer_probable_cause(best_match.affected_events)

            logger.info(
                "Alert %s correlated with Incident %s (score=%.1f). Total metrics: %d",
                alert.get("id"),
                best_match.id,
                best_score,
                len(best_match.affected_metrics),
            )
            return best_match, False

        # 4. Otherwise: Create a brand new incident
        inc_id = f"INC-{uuid.uuid4().hex[:8].upper()}"
        alert_metric = str(alert.get("metric", "")).strip()
        metrics = [alert_metric] if alert_metric else []
        service = str(alert.get("service", "system-host")).strip()
        severity = str(alert.get("severity", "WARNING")).upper()

        new_incident = CorrelatedIncident(
            id=inc_id,
            title=self._synthesize_title(service, metrics),
            service=service,
            severity=severity,
            status="OPEN",
            correlation_score=100.0,  # Base initial score
            probable_cause=self._infer_probable_cause([sanitized_alert]),
            affected_metrics=metrics,
            affected_events=[sanitized_alert],
            created_at=alert_time,
            updated_at=alert_time,
        )

        self.active_incidents[inc_id] = new_incident
        logger.info("New Correlated Incident created: %s (%s)", inc_id, new_incident.title)
        return new_incident, True

    def get_incident(self, incident_id: str) -> Optional[CorrelatedIncident]:
        """Retrieves an active incident by ID."""
        return self.active_incidents.get(incident_id)

    def resolve_incident(self, incident_id: str) -> Optional[CorrelatedIncident]:
        """Marks an active incident as resolved."""
        inc = self.active_incidents.get(incident_id)
        if inc:
            inc.status = "RESOLVED"
            inc.updated_at = datetime.now(timezone.utc)
        return inc

    def clear(self) -> None:
        """Resets engine state."""
        self.active_incidents.clear()
        self._seen_alert_ids.clear()
