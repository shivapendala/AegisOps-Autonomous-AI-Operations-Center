"""Pydantic schemas for Incidents and Incident Events."""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from backend.schemas.recommendation import RecommendationResponse


class IncidentEventResponse(BaseModel):
    id: int
    incident_id: str
    event_type: str
    description: str
    actor: str
    event_data: Optional[Dict[str, Any]] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class IncidentBase(BaseModel):
    service_id: Optional[int] = None
    title: str = Field(..., max_length=255)
    description: Optional[str] = None
    severity: str = "MEDIUM"
    status: str = "OPEN"
    root_cause: Optional[str] = None
    impact_summary: Optional[str] = None
    ai_remediation: Optional[str] = None
    anomaly_score: Optional[float] = None
    metadata_json: Optional[Dict[str, Any]] = None


class IncidentCreate(IncidentBase):
    id: Optional[str] = None


class IncidentResolveRequest(BaseModel):
    resolution_notes: str = "Resolved by Operations Engineer"
    actor: str = "Operations-Operator"


class IncidentResponse(IncidentBase):
    id: str
    service_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class IncidentDetailResponse(IncidentResponse):
    events: List[IncidentEventResponse] = []
    recommendations: List[RecommendationResponse] = []

    model_config = {"from_attributes": True}
