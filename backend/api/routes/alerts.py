"""
Alerts Management API Endpoints.
Provides listing, filtering, threshold breach evaluation, and lifecycle tracking for operational alerts.
"""

from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from backend.core.exceptions import ResourceNotFoundError
from backend.schemas.alert import AlertCreate, AlertResponse, AlertUpdate
from database.models.alert import AlertModel
from database.session import get_sync_db

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


@router.get("/{alert_id}", response_model=AlertResponse, summary="Get Alert Details")
def get_alert(alert_id: int, db: Session = Depends(get_sync_db)):
    """Retrieves specific alert information."""
    alert = db.query(AlertModel).filter(AlertModel.id == alert_id).first()
    if not alert:
        raise ResourceNotFoundError("Alert", str(alert_id))
    return alert


@router.post("", response_model=AlertResponse, status_code=status.HTTP_201_CREATED, summary="Create Alert")
def create_alert(payload: AlertCreate, db: Session = Depends(get_sync_db)):
    """Manually registers or raises an operational alert."""
    new_alert = AlertModel(
        service_id=payload.service_id,
        title=payload.title,
        description=payload.description,
        severity=payload.severity.upper(),
        status=payload.status.upper(),
        source=payload.source,
        trigger_value=payload.trigger_value,
        threshold_value=payload.threshold_value,
    )
    db.add(new_alert)
    db.commit()
    db.refresh(new_alert)
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
    return alert
