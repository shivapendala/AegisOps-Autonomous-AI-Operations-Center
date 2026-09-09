"""
AegisOps Incident Event Correlation Engine.
Implements deterministic 4-factor scoring rules without reliance on AI.
Rules = predictable; AI = investigation.

Scoring Rules:
    Same service:              +30
    Within 60 seconds:         +25
    Related metrics:           +30
    Severity relationship:     +15
    ------------------------------
    Maximum:                   100
    Threshold:                 >= 60 merges alerts into ONE incident
"""

from datetime import datetime, timedelta, timezone
import logging
from typing import Any, Dict, List, Optional, Set, Tuple
from sqlalchemy.orm import Session

from database.models.alert import AlertModel
from monitoring.correlation_engine import (
    are_metrics_related,
    are_severities_related,
    normalize_metric_name,
)

logger = logging.getLogger("aegisops.backend.incidents.correlation")

# 4-factor rule scoring weights
POINTS_SAME_SERVICE = 30.0
POINTS_TIME_WINDOW = 25.0
POINTS_RELATED_METRICS = 30.0
POINTS_SEVERITY_RELATION = 15.0
DEFAULT_WINDOW_SECONDS = 60
CORRELATION_THRESHOLD = 60.0


def _extract_field(obj: Any, field_name: str, default: Any = None) -> Any:
    """Helper to extract a field from a dictionary or SQLAlchemy model."""
    if isinstance(obj, dict):
        return obj.get(field_name, default)
    return getattr(obj, field_name, default)


def _extract_service_str(obj: Any) -> str:
    """Extracts clean service name string from dict, model, or relationship."""
    if isinstance(obj, dict):
        return str(obj.get("service") or obj.get("service_name") or "")
    svc = getattr(obj, "service", None)
    if svc is not None:
        if isinstance(svc, str):
            return svc
        if hasattr(svc, "name"):
            return str(svc.name)
    svc_name = getattr(obj, "service_name", None)
    if svc_name:
        return str(svc_name)
    return ""


def _extract_timestamp(obj: Any) -> datetime:
    """Helper to extract and standardize timestamp to UTC datetime."""
    ts = _extract_field(obj, "timestamp") or _extract_field(obj, "created_at") or _extract_field(obj, "updated_at")
    if isinstance(ts, str):
        try:
            ts = datetime.fromisoformat(ts)
        except Exception:
            ts = datetime.now(timezone.utc)
    elif not isinstance(ts, datetime):
        ts = datetime.now(timezone.utc)

    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(timezone.utc)


def normalize_service_name(service: Any) -> str:
    """Standardizes service names for comparison (strips whitespace, hyphens, and underscores)."""
    return str(service or "").strip().lower().replace("-", "_").replace(" ", "_")


# ---------------------------------------------------------------------------
# 1. Comparison Rule Functions
# ---------------------------------------------------------------------------

def compare_service(alert_a: Any, alert_b: Any) -> float:
    """
    Compares the service names of two alerts/incidents.
    Returns +30 points if services match, otherwise 0.0.
    """
    svc_a = normalize_service_name(_extract_service_str(alert_a))
    svc_b = normalize_service_name(_extract_service_str(alert_b))
    if svc_a and svc_b and svc_a == svc_b:
        return POINTS_SAME_SERVICE
    return 0.0


def compare_time_window(alert_a: Any, alert_b: Any, window_seconds: int = DEFAULT_WINDOW_SECONDS) -> float:
    """
    Compares the timestamps of two alerts/incidents.
    Returns +25 points if the time difference is within window_seconds (default: 60s), otherwise 0.0.
    """
    time_a = _extract_timestamp(alert_a)
    time_b = _extract_timestamp(alert_b)
    diff_sec = abs((time_a - time_b).total_seconds())
    if diff_sec <= window_seconds:
        return POINTS_TIME_WINDOW
    return 0.0


def compare_metric_relationship(alert_a: Any, alert_b: Any) -> float:
    """
    Compares metric affinities between two alerts or an alert and an incident.
    Returns +30 points if the metrics are semantically related in the operational cluster, otherwise 0.0.
    """
    # Can compare single metric to single metric, or metric to list of affected_metrics
    metrics_a = _extract_field(alert_a, "affected_metrics")
    if not metrics_a:
        m = _extract_field(alert_a, "metric")
        metrics_a = [m] if m else []

    metrics_b = _extract_field(alert_b, "affected_metrics")
    if not metrics_b:
        m = _extract_field(alert_b, "metric")
        metrics_b = [m] if m else []

    for ma in metrics_a:
        for mb in metrics_b:
            if are_metrics_related(str(ma), str(mb)):
                return POINTS_RELATED_METRICS
    return 0.0


def compare_severity_relationship(alert_a: Any, alert_b: Any) -> float:
    """
    Compares severity levels of two alerts/incidents.
    Returns +15 points if severities have an operational relationship (e.g. CRITICAL-CRITICAL, CRITICAL-HIGH, etc.).
    """
    sev_a = str(_extract_field(alert_a, "severity", "WARNING")).upper()
    sev_b = str(_extract_field(alert_b, "severity", "WARNING")).upper()
    if are_severities_related(sev_a, sev_b):
        return POINTS_SEVERITY_RELATION
    return 0.0


def calculate_score(
    alert_a: Any,
    alert_b: Any,
    window_seconds: int = DEFAULT_WINDOW_SECONDS,
) -> Tuple[float, Dict[str, float]]:
    """
    Calculates the 4-factor deterministic correlation score between two alerts.
    Formula:
        Same service:              +30
        Within 60 seconds:         +25
        Related metrics:           +30
        Severity relationship:     +15
        ------------------------------
        Total Score:               0 to 100

    Returns:
        (total_score, score_breakdown_dict)
    """
    same_service_pts = compare_service(alert_a, alert_b)
    time_window_pts = compare_time_window(alert_a, alert_b, window_seconds)
    metrics_pts = compare_metric_relationship(alert_a, alert_b)
    severity_pts = compare_severity_relationship(alert_a, alert_b)

    breakdown = {
        "same_service": same_service_pts,
        "time_window": time_window_pts,
        "related_metrics": metrics_pts,
        "severity_relationship": severity_pts,
    }
    total_score = sum(breakdown.values())
    return total_score, breakdown


# ---------------------------------------------------------------------------
# 2. Alert Query & Related Alerts Retrieval
# ---------------------------------------------------------------------------

def find_recent_alerts(
    db: Session,
    window_seconds: int = DEFAULT_WINDOW_SECONDS,
    service: Optional[str] = None,
    status: str = "ACTIVE",
    reference_time: Optional[datetime] = None,
) -> List[AlertModel]:
    """
    find_recent_alerts() queries active or recently triggered alerts within the sliding window.
    """
    ref_time = reference_time or datetime.now(timezone.utc)
    if ref_time.tzinfo is None:
        ref_time = ref_time.replace(tzinfo=timezone.utc)
    cutoff = ref_time - timedelta(seconds=window_seconds)

    query = db.query(AlertModel).filter(AlertModel.created_at >= cutoff)
    if status:
        query = query.filter(AlertModel.status == status)
    if service:
        query = query.filter(AlertModel.service == service)

    return query.order_by(AlertModel.created_at.desc()).all()


def find_related_alerts(
    target_alert: Any,
    candidate_alerts: List[Any],
    threshold: float = CORRELATION_THRESHOLD,
    window_seconds: int = DEFAULT_WINDOW_SECONDS,
) -> List[Tuple[Any, float, Dict[str, float]]]:
    """
    Flow:
        compare_service() -> compare_time_window() -> compare_metric_relationship() -> calculate_score()
    Returns candidate alerts with score >= threshold (default: 60.0), sorted by score descending.
    """
    target_id = _extract_field(target_alert, "id")
    related = []

    for candidate in candidate_alerts:
        cand_id = _extract_field(candidate, "id")
        if target_id is not None and cand_id is not None and target_id == cand_id:
            continue

        score, breakdown = calculate_score(target_alert, candidate, window_seconds)
        if score >= threshold:
            related.append((candidate, score, breakdown))

    related.sort(key=lambda item: item[1], reverse=True)
    return related


def synthesize_title(service: str, metrics: List[str]) -> str:
    """Generates intuitive human-readable incident title like 'Payment API degradation'."""
    svc_name = service.replace("-", " ").replace("_", " ").title()
    metric_set = {normalize_metric_name(m) for m in metrics}
    if {"api_latency", "http_500_errors"}.issubset(metric_set) or (
        "database_connections" in metric_set and ("api_latency" in metric_set or "http_500_errors" in metric_set)
    ) or ("cpu_usage" in metric_set and "database_connections" in metric_set):
        return f"{svc_name} degradation"
    elif "database_connections" in metric_set or "db_latency" in metric_set:
        return f"{svc_name} database contention & connection degradation"
    elif "cpu_usage" in metric_set and "memory_usage" in metric_set:
        return f"{svc_name} compute resource exhaustion"
    elif "disk_usage" in metric_set:
        return f"{svc_name} storage threshold critical"
    else:
        primary = metrics[0].replace("_", " ").title() if metrics else "Service"
        return f"{svc_name} {primary} degradation"


def synthesize_probable_cause(alerts: List[Any]) -> str:
    """Deterministic deduction of probable root cause based on alert telemetry."""
    if not alerts:
        return "Unknown root cause"

    metrics = [normalize_metric_name(_extract_field(a, "metric", "")) for a in alerts]
    service = _extract_field(alerts[0], "service", "service")

    if "database_connections" in metrics and ("api_latency" in metrics or "http_500_errors" in metrics or "cpu_usage" in metrics):
        return f"Resource saturation: Database connection pool exhaustion and cascading request contention on {service}"

    leading = alerts[0]
    metric = _extract_field(leading, "metric", "metric")
    val = _extract_field(leading, "value", "")
    return f"Resource saturation: Initial breach observed on {service} ({metric} = {val})."


def correlate_and_group_alerts(
    alerts: List[Any],
    threshold: float = CORRELATION_THRESHOLD,
    window_seconds: int = DEFAULT_WINDOW_SECONDS,
) -> List[Dict[str, Any]]:
    """
    Groups a list of incoming alerts into unified incident clusters.
    If score >= 60, alerts merge into ONE incident.
    """
    clusters: List[Dict[str, Any]] = []

    for alert in alerts:
        merged = False
        for cluster in clusters:
            score, breakdown = calculate_score(alert, cluster, window_seconds)
            if score >= threshold:
                cluster["alerts"].append(alert)
                m = _extract_field(alert, "metric")
                if m and m not in cluster["affected_metrics"]:
                    cluster["affected_metrics"].append(m)
                cluster["correlation_score"] = max(cluster["correlation_score"], score)
                cluster["title"] = synthesize_title(cluster["service"], cluster["affected_metrics"])
                cluster["probable_cause"] = synthesize_probable_cause(cluster["alerts"])
                merged = True
                break

        if not merged:
            svc = _extract_field(alert, "service", "system")
            m = _extract_field(alert, "metric")
            metrics = [m] if m else []
            cluster_data = {
                "service": svc,
                "title": synthesize_title(svc, metrics),
                "severity": _extract_field(alert, "severity", "WARNING"),
                "status": "OPEN",
                "correlation_score": 100.0,
                "probable_cause": synthesize_probable_cause([alert]),
                "affected_metrics": metrics,
                "alerts": [alert],
                "created_at": _extract_timestamp(alert),
                "updated_at": _extract_timestamp(alert),
            }
            clusters.append(cluster_data)

    return clusters
