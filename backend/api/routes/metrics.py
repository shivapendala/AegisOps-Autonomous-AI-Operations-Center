"""
System and Service Metrics Endpoints.
Provides queries against persisted metric streams as well as real-time host telemetry.
"""

from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from backend.schemas.metric import MetricCreate, MetricResponse, SystemMetricsSummary, HostTelemetry
from database.models.metric import MetricModel
from database.session import get_sync_db
from monitoring.collector import SystemCollector

router = APIRouter(prefix="/metrics", tags=["Metrics"])
collector = SystemCollector()


@router.get("", response_model=List[MetricResponse], summary="Get Metrics Stream")
def list_metrics(
    service_id: Optional[int] = Query(default=None, description="Filter metrics by service ID"),
    metric_name: Optional[str] = Query(default=None, description="Filter by metric name"),
    limit: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_sync_db),
):
    """Retrieves timeseries metrics from the datastore."""
    query = db.query(MetricModel)
    if service_id is not None:
        query = query.filter(MetricModel.service_id == service_id)
    if metric_name is not None:
        query = query.filter(MetricModel.metric_name == metric_name)
    metrics = query.order_by(MetricModel.timestamp.desc()).limit(limit).all()
    return metrics


@router.get("/current", response_model=HostTelemetry, summary="Get Instantaneous Host Telemetry")
def get_current_host_metrics():
    """Fetches real-time host CPU, RAM, Disk, and Network telemetry via psutil."""
    raw = collector.collect()
    return HostTelemetry(
        host_name=raw.host_name,
        cpu_percent=raw.cpu_percent,
        memory_percent=raw.memory_percent,
        disk_percent=raw.disk_percent,
        network_sent_mb=raw.network_sent_mb,
        network_recv_mb=raw.network_recv_mb,
        process_count=raw.process_count,
        timestamp=raw.timestamp,
    )


@router.get("/diagnostics", summary="Get Detailed System Diagnostics")
def get_diagnostics():
    """Retrieves deep host diagnostics including per-core CPU and top consuming processes."""
    return collector.get_detailed_report()


@router.get("/summary", response_model=SystemMetricsSummary, summary="System Metrics Summary")
def get_metrics_summary(db: Session = Depends(get_sync_db)):
    """Returns a composite summary of host telemetry and recent service metrics."""
    raw = collector.collect()
    recent_metrics = db.query(MetricModel).order_by(MetricModel.timestamp.desc()).limit(10).all()
    total_count = db.query(MetricModel).count()

    return SystemMetricsSummary(
        host=HostTelemetry(
            host_name=raw.host_name,
            cpu_percent=raw.cpu_percent,
            memory_percent=raw.memory_percent,
            disk_percent=raw.disk_percent,
            network_sent_mb=raw.network_sent_mb,
            network_recv_mb=raw.network_recv_mb,
            process_count=raw.process_count,
            timestamp=raw.timestamp,
        ),
        service_metrics=recent_metrics,
        total_metrics_count=total_count,
        timestamp=datetime.now(timezone.utc),
    )


@router.post("", response_model=MetricResponse, status_code=status.HTTP_201_CREATED, summary="Record Metric")
def record_metric(payload: MetricCreate, db: Session = Depends(get_sync_db)):
    """Ingests a new telemetry metric data point."""
    new_metric = MetricModel(
        service_id=payload.service_id,
        metric_name=payload.metric_name,
        value=payload.value,
        unit=payload.unit,
        dimensions=payload.dimensions,
        timestamp=payload.timestamp or datetime.now(timezone.utc),
    )
    db.add(new_metric)
    db.commit()
    db.refresh(new_metric)
    return new_metric
