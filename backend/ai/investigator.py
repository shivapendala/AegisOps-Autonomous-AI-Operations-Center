"""
Incident Investigator for AegisOps.
Orchestrates context aggregation, provider invocation, and database persistence.

Architecture:
Incident -> Investigator -> AIProvider -> (MockAIProvider | LLMProvider)
"""

import asyncio
from datetime import datetime, timezone
import logging
import os
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from backend.ai.base import AIProvider, IncidentInvestigation, RootCauseAnalysisResult
from backend.ai.mock_provider import MockAIProvider
from backend.ai.llm_provider import LLMProvider
from database.models.alert import AlertModel
from database.models.incident import IncidentModel
from database.models.incident_event import IncidentEventModel
from database.models.metric import MetricModel
from database.models.recommendation import IncidentRecommendationModel
from database.models.service import ServiceModel

logger = logging.getLogger("aegisops.ai.investigator")


def get_ai_provider(provider_type: Optional[str] = None) -> AIProvider:
    """Factory to instantiate the appropriate AIProvider backend."""
    ptype = (provider_type or os.getenv("AI_PROVIDER", "mock")).lower()
    if ptype in ["llm", "openai", "claude", "anthropic"]:
        return LLMProvider()
    return MockAIProvider()


class IncidentInvestigator:
    """
    Coordinates end-to-end Root Cause Analysis for operational incidents.
    Aggregates incident context, evaluates using pluggable AIProvider,
    and writes diagnostic conclusions and recommendations to the database.
    """

    def __init__(self, provider: Optional[AIProvider] = None):
        self.provider = provider or get_ai_provider()
        logger.info(
            "Initialized IncidentInvestigator with provider: %s",
            getattr(self.provider, "provider_name", type(self.provider).__name__),
        )

    def aggregate_context(self, incident_id: str, db: Session) -> IncidentInvestigation:
        """Aggregates all incident telemetry, correlated alerts, metrics, service data, and logs."""
        inc = (
            db.query(IncidentModel)
            .filter(
                (IncidentModel.id == str(incident_id))
                | (IncidentModel.id == f"INC-{incident_id}")
                | (IncidentModel.id.ilike(f"%{incident_id}%"))
            )
            .first()
        )
        if not inc:
            raise ValueError(f"Incident '{incident_id}' not found in database.")

        # 1. Correlated Alerts
        correlated_alerts = []
        events = db.query(IncidentEventModel).filter(IncidentEventModel.incident_id == inc.id).all()
        for evt in events:
            if evt.alert:
                correlated_alerts.append(evt.alert.to_dict())
            elif evt.alert_id:
                alt = db.query(AlertModel).filter(AlertModel.id == evt.alert_id).first()
                if alt:
                    correlated_alerts.append(alt.to_dict())
            elif evt.event_data:
                correlated_alerts.append(evt.event_data)

        if not correlated_alerts and inc.affected_events:
            correlated_alerts = list(inc.affected_events)

        # 2. Recent Telemetry Metrics
        recent_metrics = []
        svc_name = inc.service_name or (inc.service.name if inc.service else None)
        query = db.query(MetricModel)
        if inc.service_id:
            query = query.filter(MetricModel.service_id == inc.service_id)
        elif inc.service and hasattr(inc.service, "id"):
            query = query.filter(MetricModel.service_id == inc.service.id)
        metric_records = query.order_by(MetricModel.timestamp.desc()).limit(15).all()
        recent_metrics = [m.to_dict() for m in metric_records]

        # 3. Service Info
        service_info = inc.service.to_dict() if inc.service else {"name": svc_name, "status": "UNKNOWN"}

        # 4. Relevant Logs / Timeline
        relevant_logs = [e.to_dict() for e in events]

        return IncidentInvestigation(
            incident_id=inc.id,
            incident_info=inc.to_dict(),
            correlated_alerts=correlated_alerts,
            recent_metrics=recent_metrics,
            service_info=service_info,
            relevant_logs=relevant_logs,
            timestamp=datetime.now(timezone.utc),
        )

    async def investigate(
        self,
        incident_id: str,
        db: Session,
        persist: bool = True,
    ) -> RootCauseAnalysisResult:
        """Asynchronously executes RCA and optionally persists findings to the database."""
        investigation = self.aggregate_context(incident_id, db)
        analysis = await self.provider.analyze_incident(investigation)

        if persist:
            self._persist_analysis(incident_id, analysis, db)

        return analysis

    def investigate_sync(
        self,
        incident_id: str,
        db: Session,
        persist: bool = True,
    ) -> RootCauseAnalysisResult:
        """Synchronous version of investigate."""
        investigation = self.aggregate_context(incident_id, db)
        if hasattr(self.provider, "analyze_incident_sync"):
            analysis = self.provider.analyze_incident_sync(investigation)
        else:
            analysis = asyncio.run(self.provider.analyze_incident(investigation))

        if persist:
            self._persist_analysis(incident_id, analysis, db)

        return analysis

    def _persist_analysis(self, incident_id: str, analysis: RootCauseAnalysisResult, db: Session) -> None:
        """Persists RCA findings, recommendations, and audit trail to database."""
        inc = (
            db.query(IncidentModel)
            .filter(
                (IncidentModel.id == str(incident_id))
                | (IncidentModel.id == f"INC-{incident_id}")
                | (IncidentModel.id.ilike(f"%{incident_id}%"))
            )
            .first()
        )
        if not inc:
            return

        now = datetime.now(timezone.utc)
        inc.probable_cause = analysis.probable_root_cause
        inc.root_cause = analysis.probable_root_cause
        
        # Store confidence score as percentage (e.g. 91)
        conf = analysis.confidence_score
        if conf <= 1.0:
            conf = conf * 100.0
        inc.confidence_score = round(conf, 1)

        inc.impact_summary = analysis.impact_summary or inc.impact_summary

        meta = dict(inc.metadata_json or {})
        meta["ai_root_cause_analysis"] = analysis.to_dict()
        inc.metadata_json = meta
        inc.updated_at = now

        # Add or update IncidentRecommendationModel entries
        # IMPORTANT SAFETY RULE: All AI-generated recommendations start in status='PENDING'.
        # AI should NOT automatically execute server commands.
        action_items = getattr(analysis, "recommended_action_items", None)
        if not action_items and analysis.recommended_actions:
            action_items = [
                {
                    "action": str(act),
                    "priority": "HIGH" if idx < 2 else "MEDIUM",
                    "status": "PENDING",
                    "description": str(act),
                }
                for idx, act in enumerate(analysis.recommended_actions)
            ]

        for idx, item in enumerate(action_items or []):
            if isinstance(item, dict):
                act_text = item.get("action") or str(item)
                priority_val = item.get("priority", "HIGH" if idx < 2 else "MEDIUM")
                desc_val = item.get("description", act_text)
            else:
                act_text = str(item)
                priority_val = "HIGH" if idx < 2 else "MEDIUM"
                desc_val = act_text

            existing_rec = (
                db.query(IncidentRecommendationModel)
                .filter(
                    IncidentRecommendationModel.incident_id == inc.id,
                    IncidentRecommendationModel.action == act_text,
                )
                .first()
            )
            if not existing_rec:
                rec = IncidentRecommendationModel(
                    incident_id=inc.id,
                    action=act_text,
                    priority=priority_val,
                    status="PENDING",  # Strict Safety Guard: ALWAYS PENDING awaiting human operator review
                    title=act_text,
                    description=desc_val,
                    confidence=analysis.confidence_score,
                    generated_by=analysis.provider,
                )
                db.add(rec)

        # Add audit timeline event
        audit_evt = IncidentEventModel(
            incident_id=inc.id,
            event_type="AI_RCA_COMPLETED",
            description=f"AI RCA completed by {analysis.provider}: {analysis.probable_root_cause} (Confidence: {analysis.confidence_score*100:.0f}%)",
            actor=analysis.provider,
            event_data=analysis.to_dict(),
            created_at=now,
        )
        db.add(audit_evt)

        db.commit()
        db.refresh(inc)
        logger.info(
            "Persisted RCA for Incident %s (%s, confidence=%.2f)",
            inc.id,
            analysis.probable_root_cause,
            analysis.confidence_score,
        )
