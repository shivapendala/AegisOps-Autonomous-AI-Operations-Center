"""Pydantic schemas for AI Recommendations."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class RecommendationBase(BaseModel):
    incident_id: Optional[str] = None
    title: str = Field(..., max_length=255)
    description: str
    action_type: str = "REMEDIATION"
    confidence: float = 0.90
    priority: str = "P2"
    status: str = "PENDING"
    generated_by: str = "AegisOps-AI-LLM"


class RecommendationCreate(RecommendationBase):
    pass


class RecommendationResponse(RecommendationBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
