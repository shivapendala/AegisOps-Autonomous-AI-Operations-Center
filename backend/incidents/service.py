"""
AegisOps Incident Service.
Orchestrates incident correlation, database persistence of incidents,
and links alerts to incidents via incident_events table.
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional, Tuple
import uuid
from sqlalchemy.orm import Session, joinedload

from database.models.alert import AlertModel
from database.models.audit_log import AuditLogModel
from database.models.incident import IncidentModel
from database.models.incident_event import IncidentEventModel
from database.models.recommendation import IncidentRecommendationModel
from database.models.service import ServiceModel
from backend.incidents.correlation import (
    calculate_score,
    find_recent_alerts,
    find_related_alerts,
    synthesize_probable_cause,
    synthesize_title,
    _extract_timestamp,
    CORRELATION_THRESHOLD,
    DEFAULT_WINDOW_SECONDS,
)

logger = logging.getLogger("aegisops.backend.incidents.service")


def _sanitize_alert(alert_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Ensures alert dictionary values like datetime are JSON serializable."""
    clean = {}
    for k, v in alert_dict.items():
        if isinstance(v, datetime):
            clean[k] = v.isoformat()
        else:
            clean[k] = v
    return clean


class IncidentService:
    """
    Incident Lifecycle & Correlation Service.
    Applies deterministic correlation rules to group alerts into unified incidents
    and persists incident_events with alert_id.
    """

    def __init__(self, window_seconds: int = DEFAULT_WINDOW_SECONDS, threshold_score: float = CORRELATION_THRESHOLD):
        self.window_seconds = window_seconds
        self.threshold_score = threshold_score

    def correlate_alert(
        self,
        db: Session,
        alert: Any,
        preferred_incident_id: Optional[str] = None,
    ) -> Tuple[IncidentModel, bool, float]:
        """
        Correlates an incoming alert against open operational incidents in the database.
        
        Flow:
            find_recent_alerts() -> compare_service() -> compare_time_window()
            -> compare_metric_relationship() -> calculate_score()
            -> return related alerts / merge into ONE incident
            
        Returns:
            (incident, is_new_incident, correlation_score)
        """
        alert_dict = alert if isinstance(alert, dict) else {
            "id": getattr(alert, "id", None),
            "service": getattr(alert, "service", ""),
            "metric": getattr(alert, "metric", ""),
            "value": getattr(alert, "value", 0.0),
            "severity": getattr(alert, "severity", "WARNING"),
            "timestamp": getattr(alert, "timestamp", None) or getattr(alert, "created_at", None) or datetime.now(timezone.utc),
        }
        sanitized_alert = _sanitize_alert(alert_dict)

        # 1. Fetch active open incidents within the sliding window
        open_incidents = (
            db.query(IncidentModel)
            .filter(IncidentModel.status.in_(["OPEN", "INVESTIGATING"]))
            .order_by(IncidentModel.updated_at.desc())
            .all()
        )

        best_incident: Optional[IncidentModel] = None
        best_score = 0.0

        alert_time = _extract_timestamp(alert_dict)
        for inc in open_incidents:
            # Temporal window constraint: alerts occurring outside the sliding window cannot merge
            inc_time = _extract_timestamp(inc)
            if abs((alert_time - inc_time).total_seconds()) > self.window_seconds:
                continue

            score, breakdown = calculate_score(alert_dict, inc, self.window_seconds)
            if score >= self.threshold_score and score > best_score:
                best_score = score
                best_incident = inc

        # 2. Correlated Match Found -> Merge into existing incident
        if best_incident is not None:
            metric = alert_dict.get("metric")
            affected_metrics = list(best_incident.affected_metrics or [])
            if metric and metric not in affected_metrics:
                affected_metrics.append(metric)
            best_incident.affected_metrics = affected_metrics

            # Append raw event (sanitized for JSON)
            events_json = list(best_incident.affected_events or [])
            events_json.append(sanitized_alert)
            best_incident.affected_events = events_json

            # Escalate severity if alert is more critical
            if alert_dict.get("severity") == "CRITICAL":
                best_incident.severity = "CRITICAL"

            best_incident.correlation_score = max(best_incident.correlation_score or 0.0, best_score)
            alert_time = _extract_timestamp(alert_dict)
            best_incident.title = synthesize_title(best_incident.service_name or alert_dict.get("service", ""), affected_metrics)
            best_incident.probable_cause = synthesize_probable_cause(events_json)
            best_incident.updated_at = alert_time

            # Connect alert to incident in incident_events table
            alert_id = alert_dict.get("id")
            evt = IncidentEventModel(
                incident_id=best_incident.id,
                alert_id=alert_id,
                event_type="ALERT_ATTACHED",
                description=f"Alert #{alert_id} ({metric}) correlated into incident (Score: {best_score:.0f}).",
                actor="CorrelationService",
                event_data={"score": best_score, "metric": metric},
                created_at=alert_time,
            )
            db.add(evt)
            db.commit()
            db.refresh(best_incident)
            logger.info("Alert %s correlated with Incident %s (score=%.1f)", alert_id, best_incident.id, best_score)
            try:
                from backend.core.websocket_manager import ws_manager
                import asyncio
                payload = best_incident.to_dict()
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(ws_manager.broadcast_incident_updated(payload))
                    loop.create_task(ws_manager.broadcast_incident(payload, "INCIDENT_UPDATE"))
                except RuntimeError:
                    pass
            except Exception:
                pass
            return best_incident, False, best_score

        # 3. No match -> Open a brand new incident
        inc_id = preferred_incident_id or alert_dict.get("preferred_incident_id")
        if inc_id:
            existing_inc = db.query(IncidentModel).filter(IncidentModel.id == inc_id).first()
            if existing_inc:
                db.delete(existing_inc)
                db.flush()
        else:
            inc_id = f"INC-{uuid.uuid4().hex[:8].upper()}"
        svc_name = alert_dict.get("service", "system")
        metric = alert_dict.get("metric")
        metrics = [metric] if metric else []
        alert_time = _extract_timestamp(alert_dict)

        # Find service_id if available
        svc_record = db.query(ServiceModel).filter(ServiceModel.name == svc_name).first()
        svc_id = svc_record.id if svc_record else None

        new_incident = IncidentModel(
            id=inc_id,
            service_id=svc_id,
            service_name=svc_name,
            title=synthesize_title(svc_name, metrics),
            description=f"Operational incident triggered by initial {metric} breach.",
            severity=alert_dict.get("severity", "HIGH"),
            status="OPEN",
            correlation_score=100.0,
            probable_cause=synthesize_probable_cause([sanitized_alert]),
            affected_metrics=metrics,
            affected_events=[sanitized_alert],
            created_at=alert_time,
            updated_at=alert_time,
        )
        db.add(new_incident)
        db.flush()

        # Connect initial alert to incident
        alert_id = alert_dict.get("id")
        initial_evt = IncidentEventModel(
            incident_id=inc_id,
            alert_id=alert_id,
            event_type="ALERT_ATTACHED",
            description=f"Initial alert #{alert_id} ({metric}) opened incident ticket.",
            actor="CorrelationService",
            event_data={"metric": metric, "value": alert_dict.get("value")},
        )
        db.add(initial_evt)
        db.commit()
        db.refresh(new_incident)
        logger.info("New Correlated Incident created: %s (%s)", inc_id, new_incident.title)
        try:
            from backend.core.websocket_manager import ws_manager
            import asyncio
            payload = new_incident.to_dict()
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(ws_manager.broadcast_incident_created(payload))
                loop.create_task(ws_manager.broadcast_incident(payload, "INCIDENT_UPDATE"))
            except RuntimeError:
                pass
        except Exception:
            pass
        return new_incident, True, 100.0

    @staticmethod
    def get_incidents(
        db: Session,
        status_filter: Optional[str] = None,
        severity_filter: Optional[str] = None,
        service_id: Optional[int] = None,
        limit: int = 50,
    ) -> List[IncidentModel]:
        """Queries incidents with joined service, events, and recommendations."""
        query = (
            db.query(IncidentModel)
            .options(
                joinedload(IncidentModel.service),
                joinedload(IncidentModel.events),
                joinedload(IncidentModel.recommendations),
            )
        )
        if status_filter:
            query = query.filter(IncidentModel.status == status_filter.upper())
        if severity_filter:
            query = query.filter(IncidentModel.severity == severity_filter.upper())
        if service_id is not None:
            query = query.filter(IncidentModel.service_id == service_id)

        return query.order_by(IncidentModel.created_at.desc()).limit(limit).all()

    @staticmethod
    def get_incident_by_id(db: Session, incident_id: str) -> Optional[IncidentModel]:
        """Retrieves a single incident by ID with all relations."""
        return (
            db.query(IncidentModel)
            .options(
                joinedload(IncidentModel.service),
                joinedload(IncidentModel.events),
                joinedload(IncidentModel.recommendations),
            )
            .filter(IncidentModel.id == incident_id)
            .first()
        )

    @staticmethod
    def investigate_incident(db: Session, incident_id: str, operator: str, notes: str) -> Optional[IncidentModel]:
        """Transitions incident status to INVESTIGATING."""
        inc = db.query(IncidentModel).filter(IncidentModel.id == incident_id).first()
        if not inc:
            return None

        inc.status = "INVESTIGATING"
        inc.updated_at = datetime.now(timezone.utc)

        evt = IncidentEventModel(
            incident_id=inc.id,
            event_type="INCIDENT_INVESTIGATING",
            description=f"Triage sequence engaged by {operator}: {notes}",
            actor=operator,
            event_data={"notes": notes},
        )
        db.add(evt)
        db.commit()
        db.refresh(inc)
        return inc

    @staticmethod
    def resolve_incident(db: Session, incident_id: str, operator: str, resolution_notes: str) -> Optional[IncidentModel]:
        """Transitions incident status to RESOLVED."""
        inc = db.query(IncidentModel).filter(IncidentModel.id == incident_id).first()
        if not inc:
            return None

        now = datetime.now(timezone.utc)
        inc.status = "RESOLVED"
        inc.resolved_at = now
        inc.updated_at = now

        evt = IncidentEventModel(
            incident_id=inc.id,
            event_type="INCIDENT_RESOLVED",
            description=f"Incident marked RESOLVED by {operator}: {resolution_notes}",
            actor=operator,
            event_data={"resolution_notes": resolution_notes},
        )
        db.add(evt)
        db.commit()
        db.refresh(inc)
        return inc

    @staticmethod
    def close_incident(db: Session, incident_id: str, operator: str, closure_notes: str) -> Optional[IncidentModel]:
        """Transitions incident status to CLOSED."""
        inc = db.query(IncidentModel).filter(IncidentModel.id == incident_id).first()
        if not inc:
            return None

        inc.status = "CLOSED"
        inc.updated_at = datetime.now(timezone.utc)

        evt = IncidentEventModel(
            incident_id=inc.id,
            event_type="INCIDENT_CLOSED",
            description=f"Incident CLOSED by {operator}: {closure_notes}",
            actor=operator,
            event_data={"closure_notes": closure_notes},
        )
        db.add(evt)
        db.commit()
        db.refresh(inc)
        return inc
