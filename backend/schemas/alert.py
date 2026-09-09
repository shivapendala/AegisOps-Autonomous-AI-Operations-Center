"""Pydantic schemas for Alerts conforming to AegisOps operations standards."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class AlertBase(BaseModel):
    service: str = Field(default="system-host", description="Associated service or host")
    metric: str = Field(default="cpu_usage", description="Metric triggering the alert")
    value: float = Field(..., description="Current observed metric value")
    threshold: float = Field(..., description="Threshold breached")
    severity: str = Field(default="WARNING", description="Severity level: WARNING or CRITICAL")
    message: str = Field(..., description="Human-readable condition message")
    status: str = Field(default="ACTIVE", description="Alert status: ACTIVE, RESOLVED, ACKNOWLEDGED")


class AlertCreate(AlertBase):
    timestamp: Optional[datetime] = None
    source: str = "manual"
    service_id: Optional[int] = None


class AlertUpdate(BaseModel):
    status: Optional[str] = None
    severity: Optional[str] = None
    message: Optional[str] = None
    resolved_at: Optional[datetime] = None


class AlertResponse(AlertBase):
    id: int
    timestamp: datetime
    source: Optional[str] = None
    service_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None

    # Compatibility fields
    title: Optional[str] = None
    description: Optional[str] = None
    trigger_value: Optional[float] = None
    threshold_value: Optional[float] = None

    model_config = {"from_attributes": True}
