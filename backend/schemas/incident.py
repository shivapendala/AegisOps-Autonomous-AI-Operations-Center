"""Pydantic schemas for Incidents and Incident Events."""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, computed_field
from backend.schemas.recommendation import RecommendationResponse


class IncidentEventResponse(BaseModel):
    id: int
    incident_id: str
    alert_id: Optional[int] = None
    event_type: Optional[str] = "ALERT_ATTACHED"
    description: Optional[str] = ""
    actor: Optional[str] = "AegisOps-Autopilot"
    event_data: Optional[Dict[str, Any]] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class IncidentBase(BaseModel):
    service_id: Optional[int] = None
    service: Optional[str] = None
    service_name: Optional[str] = None
    title: str = Field(..., max_length=255)
    description: Optional[str] = None
    severity: str = "MEDIUM"
    status: str = "OPEN"
    root_cause: Optional[str] = None
    probable_cause: Optional[str] = None
    confidence_score: Optional[float] = 0.0
    impact_summary: Optional[str] = None
    ai_remediation: Optional[str] = None
    anomaly_score: Optional[float] = None
    correlation_score: Optional[float] = 100.0
    affected_metrics: Optional[List[str]] = []
    affected_events: Optional[List[Dict[str, Any]]] = []
    metadata_json: Optional[Dict[str, Any]] = None


class IncidentCreate(IncidentBase):
    id: Optional[str] = None


class IncidentInvestigateRequest(BaseModel):
    investigation_notes: str = "Investigation initiated by Operations Engineer"
    actor: str = "Operations-Operator"


class IncidentResolveRequest(BaseModel):
    resolution_notes: str = "Resolved by Operations Engineer"
    actor: str = "Operations-Operator"


class IncidentCloseRequest(BaseModel):
    closure_notes: str = "Incident reviewed and closed by Operations Engineer"
    actor: str = "Operations-Operator"


class IncidentResponse(IncidentBase):
    id: str
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class IncidentDetailResponse(IncidentResponse):
    confidence: Optional[float] = None
    evidence: Optional[List[str]] = []
    recommended_actions: Optional[List[str]] = []
    events: List[IncidentEventResponse] = []
    recommendations: List[RecommendationResponse] = []

    @computed_field
    @property
    def timeline(self) -> List[IncidentEventResponse]:
        return self.events

    model_config = {"from_attributes": True}

