"""
tests/test_ai.py
Validates AI Provider Architecture and Root Cause Analysis as specified in Step 16:
- Test 5: Mock AI
  -> Investigation works
  -> No API key required
  -> Validates deterministic RCA output and recommendations
"""

import pytest
from backend.ai.base import (
    IncidentInvestigation,
    RootCauseAnalysisResult,
)
from backend.ai.mock_provider import MockAIProvider


def test_test5_mock_ai_investigation_works_no_api_key_required():
    """
    Test 5:
    Mock AI
    -> Investigation works
    -> No API key required
    """
    # 1. Initialize MockAIProvider directly without any API key or environment variable
    provider = MockAIProvider()

    # 2. Prepare incident investigation input
    investigation = IncidentInvestigation(
        incident_id="INC-SIM-AI-01",
        incident_info={
            "id": "INC-SIM-AI-01",
            "title": "Payment API Degradation",
            "service": "payment-api",
            "severity": "CRITICAL",
            "affected_metrics": ["CPU", "DB connections", "API latency", "HTTP 500"],
        },
        correlated_alerts=[
            {"metric": "cpu_usage", "value": 94.0, "severity": "CRITICAL"},
            {"metric": "database_connections", "value": 96.0, "severity": "CRITICAL"},
            {"metric": "api_latency", "value": 2.8, "severity": "HIGH"},
            {"metric": "http_500_errors", "value": 18.0, "severity": "HIGH"},
        ],
        recent_metrics=[
            {"name": "cpu_usage", "value": 94.0},
            {"name": "database_connections", "value": 96.0},
            {"name": "api_latency", "value": 2.8},
            {"name": "http_500_errors", "value": 18.0},
        ],
        service_info={
            "name": "payment-api",
            "type": "rest_api",
            "environment": "production",
        },
    )

    # 3. Execute analysis synchronously / without external network or LLM API keys
    result = provider.analyze_incident_sync(investigation)

    # 4. Verify investigation completed successfully
    assert isinstance(result, RootCauseAnalysisResult)
    assert result.probable_root_cause == "Database connection pool exhaustion"
    assert result.confidence_score >= 0.90
    assert len(result.evidence) >= 3
    assert any("96%" in ev or "database" in ev.lower() or "connections" in ev.lower() for ev in result.evidence)
    assert len(result.recommended_actions) >= 3
    assert result.provider == "MockAIProvider"
