import logging
from datetime import datetime, timezone
from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from backend.core.exceptions import ResourceNotFoundError
from backend.schemas.incident import (
    IncidentCloseRequest,
    IncidentCreate,
    IncidentDetailResponse,
    IncidentInvestigateRequest,
    IncidentRelatedAlertResponse,
    IncidentResponse,
    IncidentResolveRequest,
)
from backend.schemas.recommendation import (
    RecommendationResponse,
    RecommendationApprovalRequest,
    RecommendationRejectRequest,
    RecommendationExecuteRequest,
)
from database.models.alert import AlertModel
from database.models.audit_log import AuditLogModel
from database.models.incident import IncidentModel
from database.models.incident_event import IncidentEventModel
from database.models.recommendation import IncidentRecommendationModel
from database.session import get_sync_db
from backend.incidents.workflow import validate_status_transition

logger = logging.getLogger("aegisops.backend.api.incidents")
router = APIRouter(prefix="/incidents", tags=["Incidents"])


def _get_incident_or_404(incident_id: str, db: Session) -> IncidentModel:
    """Helper to locate incident by exact ID, prefix match (INC-), or partial identifier."""
    inc = (
        db.query(IncidentModel)
        .options(
            joinedload(IncidentModel.service),
            joinedload(IncidentModel.events).joinedload(IncidentEventModel.alert),
            joinedload(IncidentModel.recommendations),
        )
        .filter(
            (IncidentModel.id == str(incident_id))
            | (IncidentModel.id == f"INC-{incident_id}")
            | (IncidentModel.id.ilike(f"%{incident_id}%"))
        )
        .first()
    )
    if not inc:
        raise ResourceNotFoundError("Incident", str(incident_id))
    return inc



def _map_incident_detail(inc: IncidentModel) -> IncidentDetailResponse:
    """Helper to map SQLAlchemy IncidentModel to comprehensive IncidentDetailResponse."""
    resolved_svc = inc.service.name if inc.service else inc.service_name
    meta = inc.metadata_json or {}
    rca = meta.get("ai_root_cause_analysis", {})
    confidence = rca.get("confidence_score")
    evidence = rca.get("evidence", [])
    recommended_actions = rca.get("recommended_actions")
    if not recommended_actions and inc.recommendations:
        recommended_actions = [r.description for r in inc.recommendations]

    return IncidentDetailResponse(
        id=inc.id,
        service_id=inc.service_id,
        service_name=resolved_svc,
        service=resolved_svc,
        title=inc.title,
        description=inc.description,
        severity=inc.severity,
        status=inc.status,
        root_cause=inc.root_cause,
        probable_cause=inc.probable_cause or inc.root_cause,
        impact_summary=inc.impact_summary,
        ai_remediation=inc.ai_remediation,
        anomaly_score=inc.anomaly_score,
        correlation_score=inc.correlation_score if inc.correlation_score is not None else 100.0,
        affected_metrics=inc.affected_metrics or [],
        affected_events=inc.affected_events or [],
        confidence=confidence,
        evidence=evidence,
        recommended_actions=recommended_actions or [],
        metadata_json=inc.metadata_json,
        created_at=inc.created_at,
        updated_at=inc.updated_at,
        resolved_at=inc.resolved_at,
        events=inc.events,
        recommendations=inc.recommendations,
    )


@router.get("", response_model=List[IncidentDetailResponse], summary="List Operational Incidents")
def list_incidents(
    status_filter: Optional[str] = Query(default=None, alias="status", description="Filter by status (OPEN, INVESTIGATING, RESOLVED, CLOSED)"),
    severity_filter: Optional[str] = Query(default=None, alias="severity", description="Filter by severity"),
    service_id: Optional[int] = Query(default=None, description="Filter by service ID"),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_sync_db),
):
    """Retrieves operational incidents with associated timeline events and AI recommendations."""
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

    incidents = query.order_by(IncidentModel.created_at.desc()).limit(limit).all()
    return [_map_incident_detail(inc) for inc in incidents]


@router.get("/{incident_id}", response_model=IncidentDetailResponse, summary="Get Incident Details")
def get_incident(incident_id: str, db: Session = Depends(get_sync_db)):
    """Retrieves full incident details, event audit history, and AI recommendations."""
    inc = _get_incident_or_404(incident_id, db)
    return _map_incident_detail(inc)


@router.get("/{incident_id}/events", response_model=List[IncidentRelatedAlertResponse], summary="Get Incident Related Alerts")
def get_incident_events(incident_id: str, db: Session = Depends(get_sync_db)):
    """
    Returns related alerts connected to this incident ticket.
    Traverses incident_events and resolves associated Alert records.
    """
    inc = _get_incident_or_404(incident_id, db)

    events = (
        db.query(IncidentEventModel)
        .options(joinedload(IncidentEventModel.alert))
        .filter(IncidentEventModel.incident_id == inc.id)
        .order_by(IncidentEventModel.created_at.asc())
        .all()
    )

    related_alerts: List[IncidentRelatedAlertResponse] = []
    for evt in events:
        alt = evt.alert
        if alt:
            related_alerts.append(
                IncidentRelatedAlertResponse(
                    id=alt.id,
                    alert_id=alt.id,
                    event_id=evt.id,
                    incident_id=inc.id,
                    service=alt.service,
                    metric=alt.metric,
                    value=alt.value,
                    threshold=alt.threshold,
                    severity=alt.severity,
                    message=alt.message,
                    status=alt.status,
                    source=alt.source,
                    timestamp=alt.timestamp,
                    created_at=evt.created_at,
                    event_type=evt.event_type or "ALERT_ATTACHED",
                    actor=evt.actor,
                )
            )
        elif evt.alert_id:
            alt = db.query(AlertModel).filter(AlertModel.id == evt.alert_id).first()
            if alt:
                related_alerts.append(
                    IncidentRelatedAlertResponse(
                        id=alt.id,
                        alert_id=alt.id,
                        event_id=evt.id,
                        incident_id=inc.id,
                        service=alt.service,
                        metric=alt.metric,
                        value=alt.value,
                        threshold=alt.threshold,
                        severity=alt.severity,
                        message=alt.message,
                        status=alt.status,
                        source=alt.source,
                        timestamp=alt.timestamp,
                        created_at=evt.created_at,
                        event_type=evt.event_type or "ALERT_ATTACHED",
                        actor=evt.actor,
                    )
                )
            else:
                m_data = evt.event_data or {}
                related_alerts.append(
                    IncidentRelatedAlertResponse(
                        id=evt.id,
                        alert_id=evt.alert_id,
                        event_id=evt.id,
                        incident_id=inc.id,
                        service=inc.service_name or "system",
                        metric=m_data.get("metric", "system"),
                        value=m_data.get("value", 0.0),
                        threshold=0.0,
                        severity=inc.severity,
                        message=evt.description or f"Alert #{evt.alert_id}",
                        status="ACTIVE",
                        source="event-stream",
                        timestamp=evt.created_at,
                        created_at=evt.created_at,
                        event_type=evt.event_type,
                        actor=evt.actor,
                    )
                )
        else:
            m_data = evt.event_data or {}
            related_alerts.append(
                IncidentRelatedAlertResponse(
                    id=evt.id,
                    alert_id=None,
                    event_id=evt.id,
                    incident_id=inc.id,
                    service=inc.service_name or "system",
                    metric=m_data.get("metric", "system"),
                    value=m_data.get("value", 0.0),
                    threshold=0.0,
                    severity=inc.severity,
                    message=evt.description or "Timeline event",
                    status="ACTIVE",
                    source=evt.actor or "event-stream",
                    timestamp=evt.created_at,
                    created_at=evt.created_at,
                    event_type=evt.event_type,
                    actor=evt.actor,
                )
            )

    # Fallback to affected_events JSON if no relational events logged
    if not related_alerts and inc.affected_events:
        for idx, a_dict in enumerate(inc.affected_events):
            a_id = a_dict.get("id") or (idx + 1)
            related_alerts.append(
                IncidentRelatedAlertResponse(
                    id=a_id,
                    alert_id=a_id,
                    event_id=idx + 1,
                    incident_id=inc.id,
                    service=a_dict.get("service", inc.service_name),
                    metric=a_dict.get("metric", "system"),
                    value=a_dict.get("value", 0.0),
                    threshold=a_dict.get("threshold", 0.0),
                    severity=a_dict.get("severity", inc.severity),
                    message=a_dict.get("message", f"Breach on {a_dict.get('metric')}"),
                    status=a_dict.get("status", "ACTIVE"),
                    source=a_dict.get("source", "simulation"),
                    timestamp=inc.created_at,
                    created_at=inc.created_at,
                    event_type="ALERT_ATTACHED",
                    actor="EventCorrelationEngine",
                )
            )

    return related_alerts


@router.get("/{incident_id}/recommendations", response_model=List[RecommendationResponse], summary="Get Incident Recommended Actions")
def get_incident_recommendations(incident_id: str, db: Session = Depends(get_sync_db)):
    """
    Returns recommended actions for remediation of the specified incident.
    """
    inc = _get_incident_or_404(incident_id, db)

    recs = (
        db.query(IncidentRecommendationModel)
        .filter(IncidentRecommendationModel.incident_id == inc.id)
        .order_by(IncidentRecommendationModel.created_at.desc())
        .all()
    )

    # Auto-synthesize recommendations from AI RCA if not yet persisted
    if not recs:
        meta = inc.metadata_json or {}
        rca_meta = meta.get("ai_root_cause_analysis", {})
        action_items = rca_meta.get("recommended_action_items")
        rca_actions = rca_meta.get("recommended_actions") or []
        if not rca_actions and inc.ai_remediation:
            rca_actions = [inc.ai_remediation]

        if action_items:
            for item in action_items:
                act = item.get("action")
                rec = IncidentRecommendationModel(
                    incident_id=inc.id,
                    action=act,
                    priority=item.get("priority", "HIGH"),
                    status="PENDING",
                    title=act,
                    description=item.get("description", act),
                )
                db.add(rec)
            db.commit()
            recs = (
                db.query(IncidentRecommendationModel)
                .filter(IncidentRecommendationModel.incident_id == inc.id)
                .all()
            )
        elif rca_actions:
            for idx, act in enumerate(rca_actions):
                rec = IncidentRecommendationModel(
                    incident_id=inc.id,
                    action=str(act),
                    priority="HIGH" if idx < 2 else "MEDIUM",
                    status="PENDING",
                    title=f"Action: {act[:40]}...",
                    description=str(act),
                )
                db.add(rec)
            db.commit()
            recs = (
                db.query(IncidentRecommendationModel)
                .filter(IncidentRecommendationModel.incident_id == inc.id)
                .all()
            )

    return recs


@router.post(
    "/{incident_id}/recommendations/{rec_id}/approve",
    response_model=RecommendationResponse,
    summary="Approve Incident Recommendation (Human Operator)",
)
def approve_recommendation(
    incident_id: str,
    rec_id: int,
    payload: Optional[RecommendationApprovalRequest] = None,
    db: Session = Depends(get_sync_db),
):
    """
    Human Operator approves an AI-generated recommendation.
    Enforces Safety Rule: AI recommends -> Human Operator approves -> Action.
    Transitions status from PENDING to APPROVED.
    """
    inc = _get_incident_or_404(incident_id, db)
    rec = (
        db.query(IncidentRecommendationModel)
        .filter(
            IncidentRecommendationModel.id == rec_id,
            IncidentRecommendationModel.incident_id == inc.id,
        )
        .first()
    )
    if not rec:
        raise ResourceNotFoundError("IncidentRecommendation", str(rec_id))

    req = payload or RecommendationApprovalRequest()
    rec.status = "APPROVED"
    now = datetime.now(timezone.utc)
    rec.updated_at = now

    event = IncidentEventModel(
        incident_id=inc.id,
        event_type="RECOMMENDATION_APPROVED",
        description=f"Operator '{req.operator}' approved action: {rec.action}. Notes: {req.notes}",
        actor=req.operator,
        event_data={"recommendation_id": rec.id, "action": rec.action, "priority": rec.priority},
        created_at=now,
    )
    db.add(event)

    audit = AuditLogModel(
        action="RECOMMENDATION_APPROVED",
        actor=req.operator,
        target=f"REC-{rec.id}",
        details=f"Approved recommendation {rec.id} for incident {inc.id}: {rec.action}",
    )
    db.add(audit)
    db.commit()
    db.refresh(rec)
    return rec


@router.post(
    "/{incident_id}/recommendations/{rec_id}/reject",
    response_model=RecommendationResponse,
    summary="Reject Incident Recommendation (Human Operator)",
)
def reject_recommendation(
    incident_id: str,
    rec_id: int,
    payload: Optional[RecommendationRejectRequest] = None,
    db: Session = Depends(get_sync_db),
):
    """
    Human Operator rejects an AI-generated recommendation.
    Transitions status to REJECTED.
    """
    inc = _get_incident_or_404(incident_id, db)
    rec = (
        db.query(IncidentRecommendationModel)
        .filter(
            IncidentRecommendationModel.id == rec_id,
            IncidentRecommendationModel.incident_id == inc.id,
        )
        .first()
    )
    if not rec:
        raise ResourceNotFoundError("IncidentRecommendation", str(rec_id))

    req = payload or RecommendationRejectRequest()
    rec.status = "REJECTED"
    now = datetime.now(timezone.utc)
    rec.updated_at = now

    event = IncidentEventModel(
        incident_id=inc.id,
        event_type="RECOMMENDATION_REJECTED",
        description=f"Operator '{req.operator}' rejected action: {rec.action}. Reason: {req.reason}",
        actor=req.operator,
        event_data={"recommendation_id": rec.id, "action": rec.action},
        created_at=now,
    )
    db.add(event)

    audit = AuditLogModel(
        action="RECOMMENDATION_REJECTED",
        actor=req.operator,
        target=f"REC-{rec.id}",
        details=f"Rejected recommendation {rec.id} for incident {inc.id}: {rec.action}",
    )
    db.add(audit)
    db.commit()
    db.refresh(rec)
    return rec


@router.post(
    "/{incident_id}/recommendations/{rec_id}/execute",
    response_model=RecommendationResponse,
    summary="Execute Recommendation (Human Operator Action)",
)
def execute_recommendation(
    incident_id: str,
    rec_id: int,
    payload: Optional[RecommendationExecuteRequest] = None,
    db: Session = Depends(get_sync_db),
):
    """
    Executes an action following human operator approval.
    IMPORTANT SAFETY RULE:
    AI should NOT automatically execute commands on servers.
    Execution is strictly disallowed unless the recommendation has been APPROVED by a human operator.
    Flow: AI -> Recommendation -> Human Operator -> Approval -> Action.
    """
    inc = _get_incident_or_404(incident_id, db)
    rec = (
        db.query(IncidentRecommendationModel)
        .filter(
            IncidentRecommendationModel.id == rec_id,
            IncidentRecommendationModel.incident_id == inc.id,
        )
        .first()
    )
    if not rec:
        raise ResourceNotFoundError("IncidentRecommendation", str(rec_id))

    # SAFETY CHECK: Block execution if not approved by a human operator
    if rec.status != "APPROVED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Safety Violation: Cannot execute recommendation #{rec.id} with status '{rec.status}'. "
                f"Human Operator approval is strictly required before executing remediation commands."
            ),
        )

    req = payload or RecommendationExecuteRequest()
    now = datetime.now(timezone.utc)
    rec.status = "EXECUTED"
    rec.updated_at = now

    event = IncidentEventModel(
        incident_id=inc.id,
        event_type="RECOMMENDATION_EXECUTED",
        description=f"Action executed by '{req.operator}': {rec.action}. Notes: {req.execution_notes}",
        actor=req.operator,
        event_data={"recommendation_id": rec.id, "action": rec.action},
        created_at=now,
    )
    db.add(event)

    audit = AuditLogModel(
        action="RECOMMENDATION_EXECUTED",
        actor=req.operator,
        target=f"REC-{rec.id}",
        details=f"Executed approved recommendation {rec.id} for incident {inc.id}: {rec.action}",
    )
    db.add(audit)
    db.commit()
    db.refresh(rec)
    return rec


@router.post("", response_model=IncidentResponse, status_code=status.HTTP_201_CREATED, summary="Create Incident")
async def create_incident(payload: IncidentCreate, db: Session = Depends(get_sync_db)):
    """Creates a new operational incident ticket and logs an initial event."""
    incident_id = payload.id or f"INC-{uuid.uuid4().hex[:8].upper()}"
    new_inc = IncidentModel(
        id=incident_id,
        service_id=payload.service_id,
        title=payload.title,
        description=payload.description,
        severity=payload.severity.upper(),
        status=payload.status.upper(),
        root_cause=payload.root_cause or "Automated triage in progress",
        impact_summary=payload.impact_summary,
        ai_remediation=payload.ai_remediation or "Evaluating remediation playbooks",
        anomaly_score=payload.anomaly_score,
        metadata_json=payload.metadata_json,
    )
    db.add(new_inc)

    # Automatically add initial creation event
    initial_event = IncidentEventModel(
        incident_id=incident_id,
        event_type="INCIDENT_OPENED",
        description=f"Incident {incident_id} registered: {payload.title}",
        actor="AegisOps-Autopilot",
        event_data={"severity": payload.severity},
    )
    db.add(initial_event)

    db.commit()
    db.refresh(new_inc)
    try:
        from backend.core.websocket_manager import ws_manager
        await ws_manager.broadcast_incident_created(new_inc.to_dict())
        await ws_manager.broadcast_incident(new_inc.to_dict(), event_type="INCIDENT_UPDATE")
    except Exception as exc:
        logger.debug("Failed to broadcast new incident: %s", exc)
    return new_inc


@router.post("/{incident_id}/investigate", response_model=IncidentDetailResponse, summary="Start AI Investigation")
async def investigate_incident(
    incident_id: str,
    payload: Optional[IncidentInvestigateRequest] = None,
    db: Session = Depends(get_sync_db),
):
    """
    Starts automated AI investigation for the incident.
    Transitions status to INVESTIGATING and triggers AI root cause analysis.
    """
    inc = _get_incident_or_404(incident_id, db)
    validate_status_transition(inc.status, "INVESTIGATING", incident_id=inc.id)
    req = payload or IncidentInvestigateRequest()

    now = datetime.now(timezone.utc)
    inc.status = "INVESTIGATING"
    inc.updated_at = now

    investigate_event = IncidentEventModel(
        incident_id=inc.id,
        event_type="INCIDENT_INVESTIGATING",
        description=req.investigation_notes,
        actor=req.actor,
    )
    db.add(investigate_event)

    audit = AuditLogModel(
        action="INCIDENT_INVESTIGATING",
        actor=req.actor,
        target=inc.id,
        details=req.investigation_notes,
    )
    db.add(audit)
    db.commit()

    # Automatically refresh AI RCA
    try:
        from backend.ai.investigator import IncidentInvestigator
        investigator = IncidentInvestigator()
        await investigator.investigate(incident_id=inc.id, db=db, persist=True)
    except Exception as e:
        logger.debug("Failed to run automated RCA on investigation: %s", e)

    db.refresh(inc)

    try:
        from backend.core.websocket_manager import ws_manager
        await ws_manager.broadcast_incident_updated(inc.to_dict())
        await ws_manager.broadcast_incident(inc.to_dict(), event_type="INCIDENT_UPDATE")
    except Exception as exc:
        logger.debug("Failed to broadcast investigated incident: %s", exc)

    return _map_incident_detail(inc)


@router.post("/{incident_id}/resolve", response_model=IncidentDetailResponse, summary="Resolve Incident")
async def resolve_incident(
    incident_id: str,
    payload: Optional[IncidentResolveRequest] = None,
    db: Session = Depends(get_sync_db),
):
    """
    Resolves an open or investigating incident.
    Transitions status to RESOLVED and records resolution timestamp.
    """
    inc = _get_incident_or_404(incident_id, db)
    validate_status_transition(inc.status, "RESOLVED", incident_id=inc.id)
    req = payload or IncidentResolveRequest()

    now = datetime.now(timezone.utc)
    inc.status = "RESOLVED"
    inc.resolved_at = now
    inc.updated_at = now

    resolve_event = IncidentEventModel(
        incident_id=inc.id,
        event_type="INCIDENT_RESOLVED",
        description=req.resolution_notes,
        actor=req.actor,
    )
    db.add(resolve_event)

    audit = AuditLogModel(
        action="INCIDENT_RESOLVED",
        actor=req.actor,
        target=inc.id,
        details=req.resolution_notes,
    )
    db.add(audit)

    db.commit()
    db.refresh(inc)

    try:
        from backend.core.websocket_manager import ws_manager
        await ws_manager.broadcast_incident_resolved(inc.to_dict())
        await ws_manager.broadcast_incident(inc.to_dict(), event_type="INCIDENT_UPDATE")
    except Exception as exc:
        logger.debug("Failed to broadcast resolved incident: %s", exc)

    return _map_incident_detail(inc)


@router.post("/{incident_id}/close", response_model=IncidentDetailResponse, summary="Close Incident")
async def close_incident(
    incident_id: str,
    payload: Optional[IncidentCloseRequest] = None,
    db: Session = Depends(get_sync_db),
):
    """
    Closes an incident ticket.
    Transitions status to CLOSED and logs an audit trail event.
    """
    inc = _get_incident_or_404(incident_id, db)
    validate_status_transition(inc.status, "CLOSED", incident_id=inc.id)
    req = payload or IncidentCloseRequest()

    now = datetime.now(timezone.utc)
    inc.status = "CLOSED"
    inc.updated_at = now

    close_event = IncidentEventModel(
        incident_id=inc.id,
        event_type="INCIDENT_CLOSED",
        description=req.closure_notes,
        actor=req.actor,
    )
    db.add(close_event)

    audit = AuditLogModel(
        action="INCIDENT_CLOSED",
        actor=req.actor,
        target=inc.id,
        details=req.closure_notes,
    )
    db.add(audit)

    db.commit()
    db.refresh(inc)

    try:
        from backend.core.websocket_manager import ws_manager
        await ws_manager.broadcast_incident_updated(inc.to_dict())
        await ws_manager.broadcast_incident(inc.to_dict(), event_type="INCIDENT_UPDATE")
    except Exception as exc:
        logger.debug("Failed to broadcast closed incident: %s", exc)

    return _map_incident_detail(inc)


@router.post("/{incident_id}/analyze", summary="Trigger Deep AI Root Cause Analysis")
async def trigger_incident_rca(
    incident_id: str,
    db: Session = Depends(get_sync_db),
):
    """
    Executes automated AI Root Cause Analysis on the specified incident.
    Aggregates incident info, correlated alerts, recent metrics, service info, and logs,
    invokes the AI provider (MockAIProvider or LLMProvider), and persists the findings.
    """
    from backend.ai.investigator import IncidentInvestigator
    inc = _get_incident_or_404(incident_id, db)

    investigator = IncidentInvestigator()
    analysis = await investigator.investigate(incident_id=inc.id, db=db, persist=True)
    if not analysis:
        raise ResourceNotFoundError("Incident Context", incident_id)

    db.refresh(inc)

    try:
        from backend.core.websocket_manager import ws_manager
        await ws_manager.broadcast_incident_updated(inc.to_dict())
        await ws_manager.broadcast_incident(inc.to_dict(), event_type="INCIDENT_UPDATE")
    except Exception as exc:
        logger.debug("Failed to broadcast analyzed incident: %s", exc)

    return {
        "incident_id": inc.id,
        "analysis": analysis.to_dict(),
        "incident": _map_incident_detail(inc),
    }
