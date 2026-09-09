"""
Pydantic schemas for Incident Management and Event Correlation.
Re-exports core incident schemas and adds event correlation data models.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from backend.schemas.incident import (
    IncidentBase,
    IncidentCreate,
    IncidentResponse,
    IncidentDetailResponse,
    IncidentEventResponse,
    IncidentInvestigateRequest,
    IncidentResolveRequest,
    IncidentCloseRequest,
)
from backend.schemas.recommendation import (
    RecommendationBase,
    RecommendationCreate,
    RecommendationResponse,
)


class CorrelationScoreBreakdown(BaseModel):
    """Point breakdown for 4-factor deterministic correlation rules."""
    same_service: float = Field(0.0, description="Points for matching service (+30)")
    time_window: float = Field(0.0, description="Points for alerts within 60s window (+25)")
    related_metrics: float = Field(0.0, description="Points for cascading metric relationship (+30)")
    severity_relationship: float = Field(0.0, description="Points for operational severity correlation (+15)")
    total_score: float = Field(0.0, description="Sum of points (0 to 100)")
    is_correlated: bool = Field(False, description="True if total_score >= 60")


class CorrelatedAlertItem(BaseModel):
    """Represents an alert that was correlated into an incident."""
    alert_id: int
    service: str
    metric: str
    value: float
    severity: str
    timestamp: datetime
    correlation_score: float
    score_breakdown: CorrelationScoreBreakdown


class CorrelationGroupResult(BaseModel):
    """Represents a grouped cluster of correlated alerts."""
    incident_id: Optional[str] = None
    title: str
    service: str
    severity: str
    status: str = "OPEN"
    correlation_score: float
    probable_cause: str
    affected_metrics: List[str] = []
    alerts: List[Dict[str, Any]] = []
    is_new_incident: bool = False


__all__ = [
    "IncidentBase",
    "IncidentCreate",
    "IncidentResponse",
    "IncidentDetailResponse",
    "IncidentEventResponse",
    "IncidentInvestigateRequest",
    "IncidentResolveRequest",
    "IncidentCloseRequest",
    "RecommendationBase",
    "RecommendationCreate",
    "RecommendationResponse",
    "CorrelationScoreBreakdown",
    "CorrelatedAlertItem",
    "CorrelationGroupResult",
]
