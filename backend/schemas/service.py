"""Pydantic schemas for Monitored Services."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ServiceBase(BaseModel):
    name: str = Field(..., max_length=128)
    description: Optional[str] = None
    status: str = Field(default="HEALTHY", max_length=32)
    tier: str = Field(default="STANDARD", max_length=32)
    endpoint_url: Optional[str] = None


class ServiceCreate(ServiceBase):
    pass


class ServiceUpdate(BaseModel):
    description: Optional[str] = None
    status: Optional[str] = None
    tier: Optional[str] = None
    endpoint_url: Optional[str] = None


class ServiceResponse(ServiceBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
