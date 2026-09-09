"""
Pluggable LLM Service Interface and Implementations.
Designed behind an abstract base class (BaseLLMService) to allow interchangeable
backends (Mock, OpenAI, Anthropic, or local vLLM / Ollama) without modifying business logic.
"""

from abc import ABC, abstractmethod
import logging
from typing import Any, Dict, List, Optional
import httpx

from aegisops.models.events import LLMAnalysisResult

logger = logging.getLogger("aegisops.ai.llm_service")


class BaseLLMService(ABC):
    """
    Abstract Service Interface for AI Operational Analysis.
    Decouples operational incident handling from specific LLM providers.
    """

    @abstractmethod
    async def analyze_incident(self, incident_data: Dict[str, Any]) -> LLMAnalysisResult:
        """Analyzes incident telemetry and returns root cause assessment."""
        pass

    @abstractmethod
    async def suggest_remediation(self, incident_data: Dict[str, Any]) -> List[str]:
        """Provides actionable mitigation recommendations."""
        pass


class MockLLMService(BaseLLMService):
    """
    Default offline / testing LLM provider.
    Provides deterministic, zero-dependency contextual reasoning based on incident signals.
    """

    def __init__(self, model_name: str = "mock-aegis-engine"):
        self.model_name = model_name
        logger.info("Initialized MockLLMService (model: %s)", model_name)

    async def analyze_incident(self, incident_data: Dict[str, Any]) -> LLMAnalysisResult:
        title = incident_data.get("title", "Unknown Anomaly")
        cpu = incident_data.get("cpu_percent", 0.0)
        memory = incident_data.get("memory_percent", 0.0)
        disk = incident_data.get("disk_percent", 0.0)

        # Contextual reasoning based on telemetry signatures
        if cpu > 80.0:
            root_cause = (
                f"Sustained CPU saturation ({cpu:.1f}%) observed across compute threads. "
                "Likely caused by unbounded worker loop, unindexed queries, or runaway worker process."
            )
            mitigations = [
                "Profile top active PID CPU consumers using psutil probe",
                "Throttle background batch ingestion pipelines",
                "Trigger horizontal pod autoscaling or spin up standby worker replica",
            ]
        elif memory > 85.0:
            root_cause = (
                f"Memory exhaustion alert ({memory:.1f}% utilized). "
                "Potential memory leak in caching layer or large in-memory dataset aggregation."
            )
            mitigations = [
                "Purge expired Redis / in-memory cache partitions",
                "Gracefully restart worker instances exceeding RSS threshold",
                "Inspect memory allocation profiles for memory retention leaks",
            ]
        elif disk > 90.0:
            root_cause = (
                f"Storage volume threshold exceeded ({disk:.1f}% consumed). "
                "Log rotation failure or accumulated Docker scratch layers."
            )
            mitigations = [
                "Execute log pruning for log files older than retention policy",
                "Prune untagged container images and dead volumes",
                "Expand block volume storage partition",
            ]
        else:
            root_cause = f"Multi-metric baseline divergence detected in operational telemetry for: {title}"
            mitigations = [
                "Inspect recent application deployments and config changes",
                "Verify upstream dependency response latency and database connection pool health",
                "Maintain telemetry observation window for persistent degradation",
            ]

        return LLMAnalysisResult(
            summary=f"Automated AI root cause analysis for incident: {title}",
            probable_root_cause=root_cause,
            suggested_mitigation_steps=mitigations,
            confidence=0.91,
            provider="mock-aegis-engine",
            raw_response="Synthesized via AegisOps Operational Rule Engine",
        )

    async def suggest_remediation(self, incident_data: Dict[str, Any]) -> List[str]:
        res = await self.analyze_incident(incident_data)
        return res.suggested_mitigation_steps


class OpenAILLMService(BaseLLMService):
    """
    OpenAI and OpenAI-compatible (Ollama, vLLM, Azure) provider implementation.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = "gpt-4o-mini",
        base_url: str = "https://api.openai.com/v1",
    ):
        self.api_key = api_key or ""
        self.model_name = model_name
        self.base_url = base_url.rstrip("/")
        self._mock_fallback = MockLLMService()

    async def analyze_incident(self, incident_data: Dict[str, Any]) -> LLMAnalysisResult:
        if not self.api_key:
            logger.warning("OpenAI API key missing; falling back to MockLLMService")
            return await self._mock_fallback.analyze_incident(incident_data)

        prompt = (
            "You are AegisOps AI Root Cause Analyzer. Analyze this system incident:\n"
            f"Data: {incident_data}\n"
            "Return JSON with: summary, probable_root_cause, suggested_mitigation_steps (list), confidence."
        )

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model_name,
                        "messages": [
                            {"role": "system", "content": "You are an autonomous SRE operations AI."},
                            {"role": "user", "content": prompt},
                        ],
                        "temperature": 0.2,
                    },
                )
                response.raise_for_status()
                data = response.json()
                content = data["choices"][0]["message"]["content"]

                # Extract and parse content
                return LLMAnalysisResult(
                    summary=f"Analysis completed via {self.model_name}",
                    probable_root_cause=content,
                    suggested_mitigation_steps=["Review LLM recommendations in incident log"],
                    confidence=0.88,
                    provider=f"openai/{self.model_name}",
                    raw_response=content,
                )
        except Exception as exc:
            logger.error("Error communicating with OpenAI provider: %s. Using fallback.", exc)
            return await self._mock_fallback.analyze_incident(incident_data)

    async def suggest_remediation(self, incident_data: Dict[str, Any]) -> List[str]:
        analysis = await self.analyze_incident(incident_data)
        return analysis.suggested_mitigation_steps


def get_llm_service(
    provider: str = "mock",
    api_key: Optional[str] = None,
    model_name: Optional[str] = None,
) -> BaseLLMService:
    """
    Factory method to instantiate the requested LLM service backend.
    """
    normalized = (provider or "mock").lower()
    if normalized == "openai":
        return OpenAILLMService(
            api_key=api_key,
            model_name=model_name or "gpt-4o-mini",
        )
    return MockLLMService(model_name=model_name or "mock-aegis-engine")
