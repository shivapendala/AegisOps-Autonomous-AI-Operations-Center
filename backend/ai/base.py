"""
AegisOps AI Provider Base Classes & Context Models.
Defines the AIProvider interface, IncidentInvestigation input context,
and RootCauseAnalysisResult output model.

Architecture:
Incident -> Investigator -> AIProvider -> (MockAIProvider | LLMProvider)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class IncidentInvestigation:
    """Structured operational context aggregated for AI root cause investigation."""

    incident_id: str
    incident_info: Dict[str, Any]
    correlated_alerts: List[Dict[str, Any]] = field(default_factory=list)
    recent_metrics: List[Dict[str, Any]] = field(default_factory=list)
    service_info: Optional[Dict[str, Any]] = None
    relevant_logs: List[Dict[str, Any]] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "incident_id": self.incident_id,
            "incident_info": self.incident_info,
            "correlated_alerts": self.correlated_alerts,
            "recent_metrics": self.recent_metrics,
            "service_info": self.service_info,
            "relevant_logs": self.relevant_logs,
            "timestamp": self.timestamp.isoformat() if isinstance(self.timestamp, datetime) else str(self.timestamp),
        }


@dataclass
class RootCauseAnalysisResult:
    """Structured assessment output returned by the AI provider."""

    probable_root_cause: str
    confidence_score: float  # e.g. 0.91 or 91%
    reasoning_summary: str
    evidence: List[str] = field(default_factory=list)
    recommended_actions: List[str] = field(default_factory=list)
    impact_summary: str = ""
    provider: str = "MockAIProvider"
    raw_response: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "probable_root_cause": self.probable_root_cause,
            "confidence_score": round(self.confidence_score, 2),
            "reasoning_summary": self.reasoning_summary,
            "evidence": list(self.evidence),
            "recommended_actions": list(self.recommended_actions),
            "impact_summary": self.impact_summary,
            "provider": self.provider,
            "raw_response": self.raw_response,
        }


class AIProvider(ABC):
    """
    Abstract Service Interface for AI Operational Root Cause Analysis.
    Decouples operational incident handling from specific LLM providers.
    Allows zero-dependency offline mocking alongside live LLM APIs.
    """

    @abstractmethod
    async def analyze_incident(self, investigation: IncidentInvestigation) -> RootCauseAnalysisResult:
        """Analyzes an incident investigation asynchronously and returns structured RCA."""
        pass

    def analyze_incident_sync(self, investigation: IncidentInvestigation) -> RootCauseAnalysisResult:
        """Synchronous analysis execution fallback."""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    return pool.submit(asyncio.run, self.analyze_incident(investigation)).result()
            return loop.run_until_complete(self.analyze_incident(investigation))
        except Exception:
            return asyncio.run(self.analyze_incident(investigation))
