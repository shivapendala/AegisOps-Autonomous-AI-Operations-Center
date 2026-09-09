"""
Alerts Management API Endpoints.
Provides listing, filtering, threshold breach evaluation, and lifecycle tracking for operational alerts.
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from backend.core.exceptions import ResourceNotFoundError
from backend.schemas.alert import AlertCreate, AlertResponse, AlertUpdate
from database.models.alert import AlertModel
from database.session import get_sync_db
from backend.incidents.service import IncidentService

logger = logging.getLogger("aegisops.backend.api.alerts")
router = APIRouter(prefix="/alerts", tags=["Alerts"])


@router.get("", response_model=List[AlertResponse], summary="List Operational Alerts")
def list_alerts(
    status_filter: Optional[str] = Query(default=None, alias="status", description="Filter by status (e.g. ACTIVE, RESOLVED)"),
    severity_filter: Optional[str] = Query(default=None, alias="severity", description="Filter by severity (e.g. INFO, LOW, MEDIUM, HIGH, CRITICAL)"),
    service_id: Optional[int] = Query(default=None, description="Filter alerts by associated service"),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_sync_db),
):
    """Retrieves operational alerts matching the given filter criteria."""
    query = db.query(AlertModel)
    if status_filter:
        query = query.filter(AlertModel.status == status_filter.upper())
    if severity_filter:
        query = query.filter(AlertModel.severity == severity_filter.upper())
    if service_id is not None:
        query = query.filter(AlertModel.service_id == service_id)
    alerts = query.order_by(AlertModel.created_at.desc()).limit(limit).all()
    return alerts


@router.get("/active", response_model=List[AlertResponse], summary="Get Active Operational Alerts")
def get_active_alerts(
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_sync_db),
):
    """Retrieves all currently active operational alerts."""
    return (
        db.query(AlertModel)
        .filter(AlertModel.status == "ACTIVE")
        .order_by(AlertModel.created_at.desc())
        .limit(limit)
        .all()
    )


@router.get("/{alert_id}", response_model=AlertResponse, summary="Get Alert Details")
def get_alert(alert_id: int, db: Session = Depends(get_sync_db)):
    """Retrieves specific alert information."""
    alert = db.query(AlertModel).filter(AlertModel.id == alert_id).first()
    if not alert:
        raise ResourceNotFoundError("Alert", str(alert_id))
    return alert


@router.post("", response_model=AlertResponse, status_code=status.HTTP_201_CREATED, summary="Create Alert")
def create_alert(payload: AlertCreate, db: Session = Depends(get_sync_db)):
    """
    Manually registers or raises an operational alert.
    Automatically evaluates event correlation against active incidents:
        - If related incident found (score >= 60): adds alert to existing incident
        - If no related incident found: creates a new incident ticket
    """
    new_alert = AlertModel(
        service_id=payload.service_id,
        service=payload.service,
        metric=payload.metric,
        value=payload.value,
        threshold=payload.threshold,
        severity=payload.severity.upper(),
        message=payload.message,
        status=payload.status.upper(),
        source=payload.source,
        timestamp=payload.timestamp or datetime.now(timezone.utc),
    )
    db.add(new_alert)
    db.commit()
    db.refresh(new_alert)

    # Step 14: Broadcast new_alert via WebSocket
    try:
        from backend.core.websocket_manager import ws_manager
        import asyncio
        alert_dict = {
            "id": new_alert.id,
            "service": new_alert.service,
            "metric": new_alert.metric,
            "value": new_alert.value,
            "threshold": new_alert.threshold,
            "severity": new_alert.severity,
            "message": new_alert.message,
            "status": new_alert.status,
            "timestamp": new_alert.created_at.isoformat() if new_alert.created_at else None,
        }
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(ws_manager.broadcast_new_alert(alert_dict))
            loop.create_task(ws_manager.broadcast_alert(alert_dict, "NEW_ALERT"))
        except RuntimeError:
            asyncio.run(ws_manager.broadcast_new_alert(alert_dict))
            asyncio.run(ws_manager.broadcast_alert(alert_dict, "NEW_ALERT"))
    except Exception as exc:
        logger.debug("Failed to broadcast new_alert: %s", exc)

    # Step 5: Automatically correlate alert into incident
    try:
        service = IncidentService(window_seconds=60, threshold_score=60.0)
        service.correlate_alert(db, new_alert)
    except Exception as exc:
        logger.warning("Automatic alert correlation failed: %s", exc)

    return new_alert


@router.post("/{alert_id}/resolve", response_model=AlertResponse, summary="Resolve Alert")
def resolve_alert(alert_id: int, db: Session = Depends(get_sync_db)):
    """Marks an active alert as resolved with timestamp."""
    alert = db.query(AlertModel).filter(AlertModel.id == alert_id).first()
    if not alert:
        raise ResourceNotFoundError("Alert", str(alert_id))
    alert.status = "RESOLVED"
    alert.resolved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(alert)

    try:
        from backend.core.websocket_manager import ws_manager
        import asyncio
        resolved_dict = {
            "id": alert.id,
            "service": alert.service,
            "metric": alert.metric,
            "value": alert.value,
            "threshold": alert.threshold,
            "severity": alert.severity,
            "message": alert.message,
            "status": "RESOLVED",
            "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None,
        }
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(ws_manager.broadcast_alert(resolved_dict, "ALERT_RESOLVED"))
        except RuntimeError:
            asyncio.run(ws_manager.broadcast_alert(resolved_dict, "ALERT_RESOLVED"))
    except Exception as exc:
        logger.debug("Failed to broadcast alert resolution: %s", exc)

    return alert
