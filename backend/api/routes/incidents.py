"""
Incident Management API Endpoints.
Provides incident lifecycle tracking, timeline events, and AI remediation recommendations.
"""

from datetime import datetime, timezone
from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session, joinedload

from backend.core.exceptions import ResourceNotFoundError
from backend.schemas.incident import (
    IncidentCreate,
    IncidentDetailResponse,
    IncidentResponse,
    IncidentResolveRequest,
)
from database.models.audit_log import AuditLogModel
from database.models.incident import IncidentModel
from database.models.incident_event import IncidentEventModel
from database.session import get_sync_db

router = APIRouter(prefix="/incidents", tags=["Incidents"])


@router.get("", response_model=List[IncidentDetailResponse], summary="List Operational Incidents")
def list_incidents(
    status_filter: Optional[str] = Query(default=None, alias="status", description="Filter by status (e.g. OPEN, INVESTIGATING, RESOLVED)"),
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
    # Map to schema response
    return [
        IncidentDetailResponse(
            id=inc.id,
            service_id=inc.service_id,
            service_name=inc.service.name if inc.service else None,
            title=inc.title,
            description=inc.description,
            severity=inc.severity,
            status=inc.status,
            root_cause=inc.root_cause,
            impact_summary=inc.impact_summary,
            ai_remediation=inc.ai_remediation,
            anomaly_score=inc.anomaly_score,
            metadata_json=inc.metadata_json,
            created_at=inc.created_at,
            updated_at=inc.updated_at,
            resolved_at=inc.resolved_at,
            events=inc.events,
            recommendations=inc.recommendations,
        )
        for inc in incidents
    ]


@router.get("/{incident_id}", response_model=IncidentDetailResponse, summary="Get Incident Details")
def get_incident(incident_id: str, db: Session = Depends(get_sync_db)):
    """Retrieves full incident details, event audit history, and AI recommendations."""
    inc = (
        db.query(IncidentModel)
        .options(
            joinedload(IncidentModel.service),
            joinedload(IncidentModel.events),
            joinedload(IncidentModel.recommendations),
        )
        .filter(IncidentModel.id == incident_id)
        .first()
    )
    if not inc:
        raise ResourceNotFoundError("Incident", incident_id)

    return IncidentDetailResponse(
        id=inc.id,
        service_id=inc.service_id,
        service_name=inc.service.name if inc.service else None,
        title=inc.title,
        description=inc.description,
        severity=inc.severity,
        status=inc.status,
        root_cause=inc.root_cause,
        impact_summary=inc.impact_summary,
        ai_remediation=inc.ai_remediation,
        anomaly_score=inc.anomaly_score,
        metadata_json=inc.metadata_json,
        created_at=inc.created_at,
        updated_at=inc.updated_at,
        resolved_at=inc.resolved_at,
        events=inc.events,
        recommendations=inc.recommendations,
    )


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
        await ws_manager.broadcast_incident(new_inc.to_dict(), event_type="INCIDENT_UPDATE")
    except Exception as exc:
        logger.debug("Failed to broadcast new incident: %s", exc)
    return new_inc


@router.post("/{incident_id}/resolve", response_model=IncidentResponse, summary="Resolve Incident")
async def resolve_incident(
    incident_id: str,
    payload: IncidentResolveRequest,
    db: Session = Depends(get_sync_db),
):
    """Resolves an open incident and logs an audit trail event."""
    inc = db.query(IncidentModel).filter(IncidentModel.id == incident_id).first()
    if not inc:
        raise ResourceNotFoundError("Incident", incident_id)

    now = datetime.now(timezone.utc)
    inc.status = "RESOLVED"
    inc.resolved_at = now
    inc.updated_at = now

    resolve_event = IncidentEventModel(
        incident_id=incident_id,
        event_type="INCIDENT_RESOLVED",
        description=payload.resolution_notes,
        actor=payload.actor,
    )
    db.add(resolve_event)

    audit = AuditLogModel(
        action="INCIDENT_RESOLVED",
        actor=payload.actor,
        target=incident_id,
        details=payload.resolution_notes,
    )
    db.add(audit)

    db.commit()
    db.refresh(inc)

    try:
        from backend.core.websocket_manager import ws_manager
        await ws_manager.broadcast_incident(inc.to_dict(), event_type="INCIDENT_UPDATE")
    except Exception as exc:
        logger.debug("Failed to broadcast resolved incident: %s", exc)

    return inc
