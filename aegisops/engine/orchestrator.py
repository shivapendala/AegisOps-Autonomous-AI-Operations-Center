"""
Autonomous Operations Center Orchestration Engine.
Coordinates real-time telemetry ingestion, scikit-learn anomaly scoring,
AI root-cause diagnosis via the pluggable LLM layer, and mitigation recommendations.
"""

from datetime import datetime, timezone
import logging
from typing import Dict, List, Optional
import uuid

from aegisops.ai.anomaly_detector import AnomalyDetector
from aegisops.ai.llm_service import BaseLLMService, get_llm_service
from aegisops.models.events import (
    AnomalyScore,
    IncidentReport,
    IncidentStatus,
    RemediationAction,
    SeverityLevel,
    SystemTelemetry,
)

logger = logging.getLogger("aegisops.engine.orchestrator")


class OperationsOrchestrator:
    """
    Core Autonomous Orchestrator managing incident lifecycle.
    """

    def __init__(
        self,
        llm_service: Optional[BaseLLMService] = None,
        anomaly_detector: Optional[AnomalyDetector] = None,
    ):
        self.anomaly_detector = anomaly_detector or AnomalyDetector()
        self.llm_service = llm_service or get_llm_service("mock")
        self.active_incidents: Dict[str, IncidentReport] = {}
        self.incident_history: List[IncidentReport] = []
        self.telemetry_history: List[SystemTelemetry] = []

    def _determine_severity(self, telemetry: SystemTelemetry, score: AnomalyScore) -> SeverityLevel:
        if telemetry.cpu_percent > 95.0 or telemetry.memory_percent > 95.0 or telemetry.disk_percent > 95.0:
            return SeverityLevel.CRITICAL
        if telemetry.cpu_percent > 85.0 or telemetry.memory_percent > 85.0:
            return SeverityLevel.HIGH
        if score.is_anomaly:
            return SeverityLevel.MEDIUM
        return SeverityLevel.LOW

    async def process_telemetry(self, telemetry: SystemTelemetry) -> TupleAnomalyProcessResult:
        """
        Ingests a telemetry record, evaluates with scikit-learn, and triggers AI triage if anomalous.
        """
        # Maintain rolling window of 300 telemetry snapshots
        self.telemetry_history.append(telemetry)
        if len(self.telemetry_history) > 300:
            self.telemetry_history.pop(0)

        anomaly_score = self.anomaly_detector.evaluate_telemetry(telemetry)
        new_incident: Optional[IncidentReport] = None

        if anomaly_score.is_anomaly:
            severity = self._determine_severity(telemetry, anomaly_score)
            incident_id = f"INC-{uuid.uuid4().hex[:8].upper()}"
            title = f"Operational Anomaly Detected: {', '.join(anomaly_score.affected_metrics) if anomaly_score.affected_metrics else 'Telemetry Divergence'}"
            description = (
                f"Host {telemetry.host_name} reported abnormal telemetry. "
                f"CPU: {telemetry.cpu_percent:.1f}%, RAM: {telemetry.memory_percent:.1f}%, "
                f"Disk: {telemetry.disk_percent:.1f}%. Score: {anomaly_score.score:.3f}"
            )

            # Invoke pluggable LLM root cause analysis
            context = {
                "incident_id": incident_id,
                "title": title,
                "cpu_percent": telemetry.cpu_percent,
                "memory_percent": telemetry.memory_percent,
                "disk_percent": telemetry.disk_percent,
                "process_count": telemetry.process_count,
                "affected_metrics": anomaly_score.affected_metrics,
            }
            ai_analysis = await self.llm_service.analyze_incident(context)

            new_incident = IncidentReport(
                id=incident_id,
                title=title,
                description=description,
                severity=severity,
                status=IncidentStatus.OPEN,
                anomaly_score=anomaly_score,
                ai_analysis=ai_analysis,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            self.active_incidents[incident_id] = new_incident
            self.incident_history.insert(0, new_incident)
            logger.warning("Incident logged: %s [%s]", incident_id, severity.value)

        return TupleAnomalyProcessResult(
            telemetry=telemetry,
            anomaly_score=anomaly_score,
            incident=new_incident,
        )

    def get_active_incidents(self) -> List[IncidentReport]:
        return list(self.active_incidents.values())

    def get_recent_history(self, limit: int = 50) -> List[IncidentReport]:
        return self.incident_history[:limit]

    def resolve_incident(self, incident_id: str, resolution_notes: str = "Resolved by operator") -> Optional[IncidentReport]:
        if incident_id in self.active_incidents:
            inc = self.active_incidents.pop(incident_id)
            inc.status = IncidentStatus.RESOLVED
            inc.updated_at = datetime.now(timezone.utc)
            inc.metadata["resolution_notes"] = resolution_notes
            return inc
        return None


class TupleAnomalyProcessResult:
    """Return container for processed telemetry step."""

    def __init__(
        self,
        telemetry: SystemTelemetry,
        anomaly_score: AnomalyScore,
        incident: Optional[IncidentReport] = None,
    ):
        self.telemetry = telemetry
        self.anomaly_score = anomaly_score
        self.incident = incident
