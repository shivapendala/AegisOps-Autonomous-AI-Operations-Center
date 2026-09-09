"""
Real LLM Provider for AegisOps with automatic graceful fallback to MockAIProvider.
Supports:
- OpenAI (GPT-4o, GPT-4o-mini, etc.)
- Anthropic Claude
- OpenAI-compatible endpoints (Ollama, vLLM, Azure OpenAI)

If no API key is provided or the LLM request fails (e.g. network outage, quota limit),
it seamlessly falls back to MockAIProvider, guaranteeing zero downtime.
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional
import httpx

from backend.ai.base import AIProvider, IncidentInvestigation, RootCauseAnalysisResult
from backend.ai.mock_provider import MockAIProvider

logger = logging.getLogger("aegisops.ai.llm_provider")


class LLMProvider(AIProvider):
    """
    Production AI Provider integrating external LLM APIs.
    Designed with a built-in MockAIProvider fallback to ensure continuous
    operation when offline, without API keys, or during provider downtime.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        base_url: Optional[str] = None,
        provider_name: str = "LLMProvider",
    ):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY") or ""
        self.model_name = model_name or os.getenv("LLM_MODEL") or "gpt-4o-mini"
        self.base_url = (base_url or os.getenv("LLM_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
        self.provider_name = provider_name
        self.mock_fallback = MockAIProvider(provider_name="MockAIProvider (Fallback)")

        if not self.api_key:
            logger.info("No LLM API key configured. LLMProvider will route directly to MockAIProvider.")

    async def analyze_incident(self, investigation: IncidentInvestigation) -> RootCauseAnalysisResult:
        # If no API key configured, use mock provider immediately
        if not self.api_key:
            logger.info("No API key available; routing to MockAIProvider fallback")
            res = await self.mock_fallback.analyze_incident(investigation)
            res.provider = f"{self.provider_name} (Mock Fallback)"
            return res

        prompt = self._build_investigation_prompt(investigation)

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model_name,
                        "messages": [
                            {
                                "role": "system",
                                "content": (
                                    "You are AegisOps AI Root Cause Investigator, an expert site reliability engineer. "
                                    "Analyze the provided incident context and output STRICT JSON format with keys: "
                                    "probable_root_cause (str), confidence_score (float between 0 and 1), "
                                    "reasoning_summary (str), evidence (list of strings), "
                                    "recommended_actions (list of strings), impact_summary (str)."
                                ),
                            },
                            {"role": "user", "content": prompt},
                        ],
                        "temperature": 0.2,
                        "response_format": {"type": "json_object"},
                    },
                )
                response.raise_for_status()
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                parsed = json.loads(content)

                return RootCauseAnalysisResult(
                    probable_root_cause=parsed.get("probable_root_cause", "Anomaly identified by LLM"),
                    confidence_score=float(parsed.get("confidence_score", 0.88)),
                    reasoning_summary=parsed.get("reasoning_summary", content),
                    evidence=list(parsed.get("evidence", [])),
                    recommended_actions=list(parsed.get("recommended_actions", ["Review LLM suggestions in incident log"])),
                    impact_summary=parsed.get("impact_summary", "Operational impact under LLM analysis"),
                    provider=f"{self.provider_name} ({self.model_name})",
                    raw_response=content,
                )
        except Exception as exc:
            logger.warning("LLM call failed (%s); falling back seamlessly to MockAIProvider", exc)
            fallback_res = await self.mock_fallback.analyze_incident(investigation)
            fallback_res.provider = f"{self.provider_name} (Mock Fallback)"
            return fallback_res

    def analyze_incident_sync(self, investigation: IncidentInvestigation) -> RootCauseAnalysisResult:
        if not self.api_key:
            res = self.mock_fallback.analyze_incident_sync(investigation)
            res.provider = f"{self.provider_name} (Mock Fallback)"
            return res
        import asyncio
        return asyncio.run(self.analyze_incident(investigation))

    def _build_investigation_prompt(self, investigation: IncidentInvestigation) -> str:
        return (
            f"Incident ID: {investigation.incident_id}\n"
            f"Details: {json.dumps(investigation.incident_info, default=str)}\n"
            f"Correlated Alerts: {json.dumps(investigation.correlated_alerts, default=str)}\n"
            f"Recent Metrics: {json.dumps(investigation.recent_metrics, default=str)}\n"
            f"Relevant Logs: {json.dumps(investigation.relevant_logs, default=str)}\n"
        )
