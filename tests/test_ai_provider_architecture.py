"""
Automated unit and integration tests for STEP 7: AI Provider Architecture.

Architecture Verified:
Incident
   ↓
Investigator
   ↓
AIProvider
   ├── MockAIProvider
   └── LLMProvider

Verifies:
1. MockAIProvider functions with NO API KEY, NO INTERNET, NO LLM.
2. LLMProvider gracefully falls back to MockAIProvider when unconfigured or on network failure.
3. IncidentInvestigator aggregates operational context from database and orchestrates RCA.
4. Persistence of RCA findings, confidence score, and incident recommendations.
"""

from datetime import datetime, timezone
import pytest
from unittest.mock import patch, MagicMock

from backend.ai.base import (
    AIProvider,
    IncidentInvestigation,
    RootCauseAnalysisResult,
)
from backend.ai.mock_provider import MockAIProvider
from backend.ai.llm_provider import LLMProvider
from backend.ai.investigator import IncidentInvestigator, get_ai_provider
from database.models.alert import AlertModel
from database.models.incident import IncidentModel
from database.models.incident_event import IncidentEventModel
from database.models.recommendation import IncidentRecommendationModel


# ---------------------------------------------------------------------------
# 1. MockAIProvider Tests (Zero Dependencies: No API Key, No Internet, No LLM)
# ---------------------------------------------------------------------------

def test_mock_ai_provider_database_pool_exhaustion():
    """Verify MockAIProvider deterministic reasoning on Payment API degradation."""
    provider = MockAIProvider()
    now = datetime.now(timezone.utc)

    investigation = IncidentInvestigation(
        incident_id="INC-PAY-001",
        incident_info={
            "id": "INC-PAY-001",
            "title": "Payment API degradation",
            "service": "payment-processor",
            "severity": "CRITICAL",
            "affected_metrics": ["CPU", "DB Connections", "API Latency", "HTTP 500"],
        },
        correlated_alerts=[
            {"metric": "CPU", "value": 94.0, "severity": "HIGH"},
            {"metric": "DB Connections", "value": 96.0, "severity": "HIGH"},
            {"metric": "API Latency", "value": 2.8, "severity": "HIGH"},
            {"metric": "HTTP 500", "value": 14.5, "severity": "CRITICAL"},
        ],
        timestamp=now,
    )

    result = provider.analyze_incident_sync(investigation)

    assert isinstance(result, RootCauseAnalysisResult)
    assert result.probable_root_cause == "Database connection pool exhaustion"
    assert result.confidence_score >= 0.90
    assert len(result.evidence) >= 3
    assert any("database connections" in e.lower() for e in result.evidence)
    assert any("latency" in e.lower() for e in result.evidence)
    assert len(result.recommended_actions) >= 2
    assert any("increase database connection pool" in a.lower() for a in result.recommended_actions)
    assert result.provider == "MockAIProvider"


def test_mock_ai_provider_cpu_saturation():
    """Verify MockAIProvider detects CPU saturation."""
    provider = MockAIProvider()
    investigation = IncidentInvestigation(
        incident_id="INC-CPU-001",
        incident_info={
            "id": "INC-CPU-001",
            "title": "High CPU utilization",
            "service": "auth-service",
            "severity": "HIGH",
            "affected_metrics": ["cpu_usage"],
        },
        correlated_alerts=[
            {"metric": "cpu_usage", "value": 95.0, "severity": "HIGH"}
        ],
    )

    result = provider.analyze_incident_sync(investigation)
    assert "cpu" in result.probable_root_cause.lower()
    assert result.confidence_score >= 0.85
    assert len(result.recommended_actions) >= 1


def test_mock_ai_provider_memory_leak():
    """Verify MockAIProvider detects memory exhaustion."""
    provider = MockAIProvider()
    investigation = IncidentInvestigation(
        incident_id="INC-MEM-001",
        incident_info={
            "id": "INC-MEM-001",
            "title": "High Memory utilization",
            "service": "order-service",
            "severity": "HIGH",
            "affected_metrics": ["memory_usage"],
        },
        correlated_alerts=[
            {"metric": "memory_usage", "value": 89.0, "severity": "HIGH"}
        ],
    )

    result = provider.analyze_incident_sync(investigation)
    assert "memory" in result.probable_root_cause.lower()
    assert result.confidence_score >= 0.85


# ---------------------------------------------------------------------------
# 2. LLMProvider Graceful Fallback Tests
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_llm_provider_fallback_when_no_api_key():
    """Verify LLMProvider gracefully falls back to MockAIProvider without an API key."""
    provider = LLMProvider(api_key="")
    investigation = IncidentInvestigation(
        incident_id="INC-FALLBACK-01",
        incident_info={
            "title": "Payment API degradation",
            "service": "Payment API",
            "affected_metrics": ["database_connections", "api_latency"],
        },
    )

    result = await provider.analyze_incident(investigation)
    assert result is not None
    assert result.probable_root_cause == "Database connection pool exhaustion"
    assert "Mock Fallback" in result.provider


@pytest.mark.anyio
async def test_llm_provider_fallback_on_network_failure():
    """Verify LLMProvider catches HTTP exceptions and falls back to MockAIProvider."""
    provider = LLMProvider(api_key="sk-dummy-test-key-12345")
    investigation = IncidentInvestigation(
        incident_id="INC-NETFAIL-01",
        incident_info={
            "title": "Payment API degradation",
            "service": "Payment API",
            "affected_metrics": ["database_connections", "api_latency"],
        },
    )

    # Simulate network outage / connection error
    with patch("httpx.AsyncClient.post", side_effect=Exception("Network unreachable / Timeout")):
        result = await provider.analyze_incident(investigation)
        assert result is not None
        assert result.probable_root_cause == "Database connection pool exhaustion"
        assert "Mock Fallback" in result.provider


# ---------------------------------------------------------------------------
# 3. IncidentInvestigator Orchestration & Persistence Tests
# ---------------------------------------------------------------------------

def test_investigator_end_to_end_persistence(db_session):
    """
    Test Incident -> Investigator -> AIProvider -> Database Persistence flow.
    """
    now = datetime.now(timezone.utc)

    # 1. Create Incident in DB
    inc = IncidentModel(
        id="INC-TEST-RCA-101",
        service_name="payment-processor",
        title="Payment Processor Degradation",
        severity="CRITICAL",
        status="OPEN",
        correlation_score=95.0,
        affected_metrics=["CPU", "DB Connections", "API Latency"],
        created_at=now,
        updated_at=now,
    )
    db_session.add(inc)

    # 2. Add correlated alert & event
    alert = AlertModel(
        id=701,
        service="payment-processor",
        metric="DB Connections",
        value=96.0,
        threshold=85.0,
        severity="HIGH",
        status="ACTIVE",
        message="Payment database connections saturated at 96%",
        timestamp=now,
    )
    db_session.add(alert)
    db_session.flush()

    event = IncidentEventModel(
        incident_id=inc.id,
        alert_id=701,
        event_type="ALERT_ATTACHED",
        description="Alert #701 attached to incident",
        created_at=now,
    )
    db_session.add(event)
    db_session.commit()

    # 3. Run Investigator with MockAIProvider
    investigator = IncidentInvestigator(provider=MockAIProvider())
    rca = investigator.investigate_sync(inc.id, db_session, persist=True)

    assert rca.probable_root_cause == "Database connection pool exhaustion"
    assert rca.confidence_score >= 0.90

    # 4. Verify DB was updated
    db_session.refresh(inc)
    assert inc.probable_cause == "Database connection pool exhaustion"
    assert inc.root_cause == "Database connection pool exhaustion"
    assert inc.confidence_score >= 0.90
    assert inc.metadata_json is not None
    assert "ai_root_cause_analysis" in inc.metadata_json

    # 5. Verify Recommendations were persisted
    recs = (
        db_session.query(IncidentRecommendationModel)
        .filter(IncidentRecommendationModel.incident_id == inc.id)
        .all()
    )
    assert len(recs) >= 1
    assert any("database connection pool" in r.action.lower() for r in recs)

    # 6. Verify Audit Event was logged
    audit_events = (
        db_session.query(IncidentEventModel)
        .filter(
            IncidentEventModel.incident_id == inc.id,
            IncidentEventModel.event_type == "AI_RCA_COMPLETED",
        )
        .all()
    )
    assert len(audit_events) == 1
    assert "MockAIProvider" in audit_events[0].actor


def test_get_ai_provider_factory():
    """Verify factory returns appropriate provider."""
    mock_p = get_ai_provider("mock")
    assert isinstance(mock_p, MockAIProvider)

    llm_p = get_ai_provider("openai")
    assert isinstance(llm_p, LLMProvider)
