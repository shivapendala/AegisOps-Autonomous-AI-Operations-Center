"""Pydantic schemas for Health check endpoints."""
from datetime import datetime
from typing import Dict
from pydantic import BaseModel, Field


class AIEngineInfo(BaseModel):
    provider: str
    anomaly_detector: str


class HealthResponse(BaseModel):
    status: str = Field(..., description="Overall operational health: healthy or degraded")
    app_name: str
    version: str
    environment: str
    uptime_seconds: float
    database: str
    tables_ready: bool = True
    ai_engine: AIEngineInfo
    timestamp: datetime
