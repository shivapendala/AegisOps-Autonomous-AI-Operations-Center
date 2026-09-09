"""
Deterministic Mock AI Provider for AegisOps.
Enables full autonomous operations capability with:
- NO API KEY
- NO INTERNET
- NO EXTERNAL LLM
Ideal for zero-dependency demos, offline staging, and predictable unit testing.
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional

from backend.ai.base import AIProvider, IncidentInvestigation, RootCauseAnalysisResult

logger = logging.getLogger("aegisops.ai.mock_provider")


class MockAIProvider(AIProvider):
    """
    Deterministic SRE Reasoning Engine.
    Provides realistic, deterministic AI root cause analyses based on operational
    signals, metric thresholds, and alert correlations without requiring external API keys.
    """

    def __init__(self, provider_name: str = "MockAIProvider"):
        self.provider_name = provider_name
        logger.info("Initialized MockAIProvider (zero-external-dependency mode)")

    async def analyze_incident(self, investigation: IncidentInvestigation) -> RootCauseAnalysisResult:
        return self.analyze_incident_sync(investigation)

    def analyze_incident_sync(self, investigation: IncidentInvestigation) -> RootCauseAnalysisResult:
        """
        Deterministic operational rule engine evaluating metrics, alerts, and services.
        Produces realistic SRE root causes and mitigation actions.
        """
        info = investigation.incident_info or {}
        title = info.get("title", "").lower()
        
        # 1. Resolve Service Information
        svc_str = ""
        if isinstance(investigation.service_info, dict):
            svc_str = str(investigation.service_info.get("name") or investigation.service_info.get("service") or "")
        elif isinstance(investigation.service_info, str):
            svc_str = investigation.service_info
        if not svc_str:
            svc_str = str(info.get("service") or info.get("service_name") or "")
        service_lower = svc_str.lower()

        # 2. Extract Alerts
        alerts = investigation.correlated_alerts or []
        affected_metrics = set(info.get("affected_metrics") or [])

        # 3. Extract and normalize Metrics from both recent_metrics and correlated_alerts
        metric_values: Dict[str, float] = {}

        # From recent_metrics (handles both dict and list format)
        if isinstance(investigation.recent_metrics, dict):
            for k, v in investigation.recent_metrics.items():
                try:
                    norm_k = str(k).lower().replace("-", "_").replace(" ", "_").strip()
                    metric_values[norm_k] = float(v)
                    affected_metrics.add(norm_k)
                except (ValueError, TypeError):
                    pass
        elif isinstance(investigation.recent_metrics, list):
            for m in investigation.recent_metrics:
                if isinstance(m, dict):
                    raw_name = m.get("metric_name") or m.get("metric") or m.get("name") or ""
                    norm_k = str(raw_name).lower().replace("-", "_").replace(" ", "_").strip()
                    try:
                        metric_values[norm_k] = float(m.get("value", 0.0))
                        affected_metrics.add(norm_k)
                    except (ValueError, TypeError):
                        pass

        # From correlated_alerts
        for a in alerts:
            if isinstance(a, dict):
                raw_name = a.get("metric") or a.get("metric_name") or ""
                norm_k = str(raw_name).lower().replace("-", "_").replace(" ", "_").strip()
                if norm_k:
                    affected_metrics.add(norm_k)
                try:
                    metric_values[norm_k] = float(a.get("value", 0.0))
                except (ValueError, TypeError):
                    pass

        # Helper to query metric values
        def get_metric_val(*keywords, default=None):
            for k, val in metric_values.items():
                for kw in keywords:
                    if kw.lower() in k:
                        return val
            return default

        # 1. Primary Scenario: Database Connection Pool Exhaustion (Payment API cascade)
        is_payment_api = "payment" in service_lower or "payment" in title
        has_db = any("db" in m or "database" in m or "connection" in m or "query" in m for m in affected_metrics)
        has_latency = any("latenc" in m or "timeout" in m for m in affected_metrics)
        has_http_500 = any("500" in m or "error" in m for m in affected_metrics)
        has_cpu = any("cpu" in m for m in affected_metrics)

        db_val = get_metric_val("db", "database", "connection", default=96.0)
        lat_val = get_metric_val("latenc", "timeout", default=2.8)

        if (is_payment_api and (has_db or has_latency)) or (has_db and (has_latency or has_http_500)):
            probable_cause = "Database connection pool exhaustion"
            confidence = 0.91
            reasoning = (
                "Observed database connection pool saturation leading to incoming query queuing. "
                "Downstream worker threads blocked waiting for database connections, causing API latency "
                "to spike and cascading into HTTP 500 timeouts."
            )
            evidence = [
                f"DB connections reached {db_val:.0f}%",
                f"API latency increased to {lat_val:.1f} seconds",
                "HTTP 500 errors increased",
                "Payment requests timed out",
            ]
            recommended_actions = [
                "Increase database connection pool and investigate long-running queries.",
                "Increase database connection pool maximum limit",
                "Investigate long-running queries on payment database",
                "Restart stale database connection worker pool",
                "Enable query caching on payment transaction ledger",
            ]
            impact = "Critical degradation in transaction processing; ~18% payment request failure rate."

        # 2. High CPU Saturation
        elif has_cpu and not has_db:
            probable_cause = "Sustained CPU saturation from unconstrained compute loop"
            confidence = 0.94
            reasoning = (
                "Continuous high CPU utilization (>85%) across application worker threads. "
                "Indicates thread starvation or unbounded serialization loop."
            )
            evidence = [
                "CPU usage breached critical threshold (>90%)",
                "Load average 3x above available CPU core count",
                "Runaway process detected in worker container",
            ]
            recommended_actions = [
                "Profile top active worker PID CPU consumers",
                "Scale out additional worker replicas (HPA trigger)",
                "Throttle background batch ingestion pipelines",
            ]
            impact = "Elevated request queuing time and potential node eviction."

        # 3. Memory Leak / Exhaustion
        elif any("mem" in m for m in affected_metrics):
            probable_cause = "Heap memory exhaustion / cache buffer leak"
            confidence = 0.89
            reasoning = (
                "Monotonically increasing RSS memory footprint without stabilization during GC cycles. "
                "Risk of container OOMKilled termination."
            )
            evidence = [
                "Memory consumption exceeded 85% allocated limit",
                "Garbage collection pause times elevated",
            ]
            recommended_actions = [
                "Inspect memory heap profile for retain cycles or cache leaks",
                "Gracefully restart worker instances exceeding RSS threshold",
                "Purge expired in-memory cache partitions",
            ]
            impact = "Node stability threatened; high likelihood of abrupt OOMKill."

        # 4. Storage / Disk Volume Saturation
        elif any("disk" in m for m in affected_metrics):
            probable_cause = "Disk storage capacity exceeded from unrotated logs or temp artifacts"
            confidence = 0.93
            reasoning = (
                "Root partition storage usage exceeded 90%. Log rotation or temp directory cleanup failure."
            )
            evidence = [
                "Disk space utilization reached 92% on /var/log volume",
                "I/O wait elevated due to disk write throttling",
            ]
            recommended_actions = [
                "Purge archived container logs older than retention policy",
                "Remove dangling Docker images and build layers",
                "Expand block volume storage partition",
            ]
            impact = "Risk of read-only filesystem lock and service crash."

        # 5. Default Generic Anomaly
        else:
            probable_cause = f"Multi-metric telemetry divergence on {service or 'system'}"
            confidence = 0.85
            reasoning = "Operational anomalies detected across telemetry signals requiring operator triage."
            evidence = [
                f"Incident triggered with {len(alerts)} correlated alerts",
                f"Telemetry variance observed across {len(affected_metrics)} metrics",
            ]
            recommended_actions = [
                "Inspect recent application deployments and configuration diffs",
                "Verify network latency and upstream service dependencies",
                "Review application error logs for unhandled exceptions",
            ]
            impact = "Degraded operational performance."

        return RootCauseAnalysisResult(
            probable_root_cause=probable_cause,
            confidence_score=confidence,
            reasoning_summary=reasoning,
            evidence=evidence,
            recommended_actions=recommended_actions,
            impact_summary=impact,
            provider=self.provider_name,
            raw_response="Synthesized via AegisOps Deterministic Mock Operational Engine",
        )
