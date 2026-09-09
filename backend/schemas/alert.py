"""Pydantic schemas for Alerts."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class AlertBase(BaseModel):
    service_id: Optional[int] = None
    title: str = Field(..., max_length=255)
    description: Optional[str] = None
    severity: str = Field(default="MEDIUM", max_length=32)
    status: str = Field(default="ACTIVE", max_length=32)
    source: str = Field(default="scikit-learn-detector", max_length=64)
    trigger_value: Optional[float] = None
    threshold_value: Optional[float] = None


class AlertCreate(AlertBase):
    pass


class AlertUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    severity: Optional[str] = None
    status: Optional[str] = None
    resolved_at: Optional[datetime] = None


class AlertResponse(AlertBase):
    id: int
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
