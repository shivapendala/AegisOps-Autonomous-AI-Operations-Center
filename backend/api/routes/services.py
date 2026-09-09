"""
Services Management API Endpoints.
Provides registry, status tracking, and telemetry associations for monitored services.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from backend.core.exceptions import ResourceNotFoundError
from backend.schemas.service import ServiceCreate, ServiceResponse, ServiceUpdate
from database.models.service import ServiceModel
from database.session import get_sync_db

router = APIRouter(prefix="/services", tags=["Services"])


@router.get("", response_model=List[ServiceResponse], summary="List Monitored Services")
def list_services(
    status_filter: Optional[str] = Query(default=None, alias="status", description="Filter by service status (e.g. HEALTHY, DEGRADED, UNHEALTHY)"),
    tier_filter: Optional[str] = Query(default=None, alias="tier", description="Filter by service tier (e.g. CRITICAL, STANDARD)"),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_sync_db),
):
    """Retrieves all registered infrastructure services with optional status/tier filtering."""
    query = db.query(ServiceModel)
    if status_filter:
        query = query.filter(ServiceModel.status == status_filter.upper())
    if tier_filter:
        query = query.filter(ServiceModel.tier == tier_filter.upper())
    services = query.order_by(ServiceModel.name.asc()).limit(limit).all()
    return services


@router.get("/{service_id}", response_model=ServiceResponse, summary="Get Service Details")
def get_service(service_id: int, db: Session = Depends(get_sync_db)):
    """Retrieves detailed information for a specific service by ID."""
    svc = db.query(ServiceModel).filter(ServiceModel.id == service_id).first()
    if not svc:
        raise ResourceNotFoundError("Service", str(service_id))
    return svc


@router.post("", response_model=ServiceResponse, status_code=status.HTTP_201_CREATED, summary="Register Service")
async def create_service(payload: ServiceCreate, db: Session = Depends(get_sync_db)):
    """Registers a new service in the AegisOps monitoring catalog."""
    new_svc = ServiceModel(
        name=payload.name,
        description=payload.description,
        status=payload.status.upper(),
        tier=payload.tier.upper(),
        endpoint_url=payload.endpoint_url,
    )
    db.add(new_svc)
    db.commit()
    db.refresh(new_svc)

    try:
        from backend.core.websocket_manager import ws_manager
        await ws_manager.broadcast_service_status(
            service_name=new_svc.name,
            status=new_svc.status,
            service_id=new_svc.id,
            details=f"Service {new_svc.name} registered as {new_svc.status}",
        )
    except Exception as exc:
        pass

    return new_svc


@router.patch("/{service_id}/status", response_model=ServiceResponse, summary="Update Service Status")
async def update_service_status(
    service_id: int,
    status_val: str = Query(..., alias="status", description="New status (HEALTHY, DEGRADED, UNHEALTHY)"),
    db: Session = Depends(get_sync_db),
):
    """Updates the operational status of a service and broadcasts the change."""
    svc = db.query(ServiceModel).filter(ServiceModel.id == service_id).first()
    if not svc:
        raise ResourceNotFoundError("Service", str(service_id))

    svc.status = status_val.upper()
    db.commit()
    db.refresh(svc)

    try:
        from backend.core.websocket_manager import ws_manager
        await ws_manager.broadcast_service_status(
            service_name=svc.name,
            status=svc.status,
            service_id=svc.id,
            details=f"Service {svc.name} status transitioned to {svc.status}",
        )
    except Exception as exc:
        pass

    return svc
