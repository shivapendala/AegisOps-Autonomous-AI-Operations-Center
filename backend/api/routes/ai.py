"""
AI Operational Intelligence Endpoints.
Exposes scikit-learn anomaly detection scoring and pluggable LLM root-cause analysis.
"""

from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from aegisops.ai.anomaly_detector import AnomalyDetector
from aegisops.ai.llm_service import get_llm_service
from aegisops.models.events import AnomalyScore, LLMAnalysisResult, SystemTelemetry
from backend.config import settings
from database.session import get_sync_db
from monitoring.collector import SystemCollector

router = APIRouter(prefix="/ai", tags=["AI Intelligence"])

# Shared singleton instances
detector = AnomalyDetector(contamination=settings.ANOMALY_DETECTION_CONTAMINATION)
llm_service = get_llm_service(
    provider=settings.LLM_PROVIDER,
    api_key=settings.OPENAI_API_KEY,
    model_name=settings.LLM_MODEL_NAME,
)
collector = SystemCollector()


class EvaluateTelemetryRequest(BaseModel):
    telemetry: Optional[SystemTelemetry] = None


class IncidentAnalysisRequest(BaseModel):
    title: str
    cpu_percent: float = 85.0
    memory_percent: float = 90.0
    disk_percent: float = 75.0
    process_count: int = 150
    notes: Optional[str] = None


@router.get("/info", summary="AI Engine Information")
def get_ai_info() -> Dict[str, Any]:
    """Returns AI model architectures, contamination thresholds, and active LLM provider."""
    return {
        "anomaly_detector": {
            "algorithm": "scikit-learn IsolationForest",
            "contamination": settings.ANOMALY_DETECTION_CONTAMINATION,
            "is_trained": detector.is_trained,
            "feature_space": ["cpu_percent", "memory_percent", "disk_percent", "process_count"],
        },
        "llm_service": {
            "provider": settings.LLM_PROVIDER,
            "model_name": settings.LLM_MODEL_NAME,
            "interface": "BaseLLMService (Pluggable)",
        },
    }


@router.post("/evaluate", response_model=AnomalyScore, summary="Evaluate Telemetry for Anomalies")
def evaluate_telemetry(payload: Optional[EvaluateTelemetryRequest] = None) -> AnomalyScore:
    """Evaluates telemetry with scikit-learn. Uses current host metrics if none provided."""
    target_telemetry = (
        payload.telemetry if payload and payload.telemetry else collector.collect()
    )
    return detector.evaluate_telemetry(target_telemetry)


@router.post("/analyze", response_model=LLMAnalysisResult, summary="Perform AI Root Cause Analysis")
async def analyze_incident(payload: IncidentAnalysisRequest) -> LLMAnalysisResult:
    """Invokes the active LLM service to analyze incident signals and provide remediation."""
    data = payload.model_dump()
    return await llm_service.analyze_incident(data)
