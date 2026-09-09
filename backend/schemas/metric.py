"""Pydantic schemas for Metrics."""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class MetricBase(BaseModel):
    service_id: Optional[int] = None
    metric_name: str = Field(..., max_length=128)
    value: float
    unit: str = Field(default="", max_length=32)
    dimensions: Optional[Dict[str, Any]] = None


class MetricCreate(MetricBase):
    timestamp: Optional[datetime] = None


class MetricResponse(MetricBase):
    id: int
    timestamp: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class HostTelemetry(BaseModel):
    host_name: str
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    network_sent_mb: float
    network_recv_mb: float
    process_count: int
    timestamp: datetime


class SystemMetricsSummary(BaseModel):
    host: HostTelemetry
    service_metrics: List[MetricResponse]
    total_metrics_count: int
    timestamp: datetime
