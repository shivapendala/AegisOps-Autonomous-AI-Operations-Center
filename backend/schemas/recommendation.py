"""Pydantic schemas for AI Recommendations."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class RecommendationBase(BaseModel):
    incident_id: Optional[str] = None
    action: Optional[str] = None
    priority: str = "HIGH"
    status: str = "PENDING"
    title: Optional[str] = None
    description: Optional[str] = None
    action_type: str = "REMEDIATION"
    confidence: float = 0.90
    generated_by: str = "AegisOps-AI-LLM"


class RecommendationCreate(RecommendationBase):
    pass


class RecommendationResponse(RecommendationBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
