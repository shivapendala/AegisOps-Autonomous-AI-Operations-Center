"""
Unit tests for the AegisOps AI Root Cause Analysis (RCA) module.
Validates:
- Structured IncidentInvestigation context collection
- MockAIProvider deterministic reasoning and evidence extraction
- Database connection pool exhaustion scenario (exact prompt example)
- LLMProvider graceful fallback when no API key is provided
- PostgreSQL persistence of root causes and recommendations
- REST API endpoint: POST /api/incidents/{incident_id}/analyze
"""

import asyncio
from datetime import datetime, timezone
import pytest

from aegisops.ai.rca import (
    AIProvider,
    IncidentInvestigation,
    IncidentInvestigator,
    LLMProvider,
    MockAIProvider,
    RootCauseAnalysisResult,
    get_ai_provider,
)
from database.models.alert import AlertModel
from database.models.incident import IncidentModel
from database.models.incident_event import IncidentEventModel
from database.models.recommendation import RecommendationModel
from database.models.service import ServiceModel


@pytest.fixture
def mock_provider():
    return MockAIProvider()


# ---------------------------------------------------------------------------
# 1. Provider Abstraction & Prompt Example Verification
# ---------------------------------------------------------------------------

def test_mock_ai_provider_database_connection_pool_exhaustion(mock_provider):
    """
    Verify exact prompt example:
    Probable Cause: Database connection pool exhaustion
    Confidence: 91%
    Evidence:
    * Database connections increased to 96%
    * API latency increased from 200ms to 2.8s
    * HTTP 500 errors increased
    * CPU increased after database saturation
    Recommended Action:
    Increase database connection pool and investigate long-running queries.
    """
    now = datetime.now(timezone.utc)
    investigation = IncidentInvestigation(
        incident_id="INC-PAY01",
        incident_info={
            "id": "INC-PAY01",
            "title": "Payment API degradation",
            "service": "payment-api",
            "severity": "CRITICAL",
        },
        correlated_alerts=[
            {"metric": "database_connections", "value": 96.0, "threshold": 80.0, "severity": "CRITICAL"},
            {"metric": "api_latency", "value": 2.8, "threshold": 1.0, "severity": "HIGH"},
            {"metric": "http_500_errors", "value": 150.0, "threshold": 10.0, "severity": "CRITICAL"},
            {"metric": "cpu_usage", "value": 88.0, "threshold": 70.0, "severity": "CRITICAL"},
        ],
        recent_metrics=[
            {"metric_name": "database_connections", "value": 96.0},
            {"metric_name": "cpu_usage", "value": 88.0},
        ],
        service_info={"name": "payment-api", "tier": "Tier-1"},
        relevant_logs=[{"description": "500 Internal Server Error rate spike"}],
        timestamp=now,
    )

    result = asyncio.run(mock_provider.analyze_incident(investigation))

    # 1. Required return attributes
    assert isinstance(result, RootCauseAnalysisResult)
    assert result.probable_root_cause == "Database connection pool exhaustion"
    assert result.confidence_score == 0.91 or result.confidence_score == 91.0
    assert len(result.reasoning_summary) > 0
    assert len(result.impact_summary) > 0

    # 2. Evidence list matches specification
    assert any("Database connections increased to 96%" in ev for ev in result.evidence)
    assert any("API latency increased from 200ms to 2.8s" in ev for ev in result.evidence)
    assert any("HTTP 500 errors increased" in ev for ev in result.evidence)
    assert any("CPU increased after database saturation" in ev for ev in result.evidence)

    # 3. Recommended actions
    assert any(
        "Increase database connection pool and investigate long-running queries." in act
        for act in result.recommended_actions
    )


def test_mock_ai_provider_cpu_exhaustion(mock_provider):
    """Verify CPU saturation reasoning."""
    investigation = IncidentInvestigation(
        incident_id="INC-COMP01",
        incident_info={"id": "INC-COMP01", "service": "order-processor"},
        correlated_alerts=[
            {"metric": "cpu_usage", "value": 94.0, "threshold": 70.0, "severity": "CRITICAL"}
        ],
        recent_metrics=[{"metric_name": "cpu_usage", "value": 94.0}],
    )

    result = asyncio.run(mock_provider.analyze_incident(investigation))
    assert "Compute resource exhaustion" in result.probable_root_cause
    assert result.confidence_score > 0.8
    assert len(result.evidence) > 0
    assert len(result.recommended_actions) > 0


def test_llm_provider_fallback_without_api_key(monkeypatch):
    """
    Verify that if no API key is available, LLMProvider safely falls back
    to MockAIProvider so the entire project continues to function.
    """
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)

    provider = LLMProvider(api_key="")
    investigation = IncidentInvestigation(
        incident_id="INC-FALLBACK-01",
        incident_info={"id": "INC-FALLBACK-01", "service": "auth-service"},
        correlated_alerts=[{"metric": "disk_usage", "value": 92.0, "severity": "CRITICAL"}],
    )

    result = asyncio.run(provider.analyze_incident(investigation))
    assert result is not None
    assert "Storage volume" in result.probable_root_cause
    assert result.confidence_score > 0.85


def test_get_ai_provider_factory(monkeypatch):
    """Verify factory chooses MockAIProvider when no key is set."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("AI_PROVIDER", raising=False)

    provider = get_ai_provider()
    assert isinstance(provider, MockAIProvider)


# ---------------------------------------------------------------------------
# 2. Context Aggregator & Database Persistence Tests
# ---------------------------------------------------------------------------

def test_incident_investigator_end_to_end(db_session):
    """
    Verify IncidentInvestigator collects context from database,
    calls provider, and persists root cause analysis, evidence, and recommendations.
    """
    # 1. Seed service, alerts, and incident
    svc = ServiceModel(
        name="payment-api",
        description="Payment Processing Gateway",
        status="DEGRADED",
        tier="Tier-1",
    )
    db_session.add(svc)
    db_session.commit()
    db_session.refresh(svc)

    inc = IncidentModel(
        id="INC-TEST-DB01",
        service_id=svc.id,
        service_name=svc.name,
        title="Payment API Latency Degradation",
        description="High latency and 500 error alerts",
        severity="CRITICAL",
        status="OPEN",
        affected_events=[
            {"metric": "database_connections", "value": 96.0, "threshold": 80.0, "severity": "CRITICAL"},
            {"metric": "api_latency", "value": 2.8, "threshold": 1.0, "severity": "HIGH"},
            {"metric": "http_500_errors", "value": 120.0, "threshold": 10.0, "severity": "CRITICAL"},
            {"metric": "cpu_usage", "value": 85.0, "threshold": 70.0, "severity": "CRITICAL"},
        ],
    )
    db_session.add(inc)
    db_session.commit()

    # 2. Run investigation
    investigator = IncidentInvestigator(provider=MockAIProvider())
    result = asyncio.run(investigator.investigate(incident_id="INC-TEST-DB01", db=db_session, persist=True))

    assert result is not None
    assert result.probable_root_cause == "Database connection pool exhaustion"

    # 3. Verify PostgreSQL / SQLite database persistence against the incident
    db_session.refresh(inc)
    assert inc.probable_cause == "Database connection pool exhaustion"
    assert inc.root_cause == "Database connection pool exhaustion"
    assert "Increase database connection pool" in inc.ai_remediation
    assert inc.metadata_json is not None
    assert "ai_root_cause_analysis" in inc.metadata_json

    meta = inc.metadata_json["ai_root_cause_analysis"]
    assert meta["confidence_score"] == 0.91
    assert len(meta["evidence"]) >= 3

    # 4. Verify recommendations persisted
    recs = db_session.query(RecommendationModel).filter(RecommendationModel.incident_id == inc.id).all()
    assert len(recs) >= 2
    assert any("Increase database connection pool" in r.description for r in recs)

    # 5. Verify incident events audit trail
    events = db_session.query(IncidentEventModel).filter(IncidentEventModel.incident_id == inc.id).all()
    assert any(e.event_type == "AI_RCA_COMPLETED" for e in events)


# ---------------------------------------------------------------------------
# 3. API Endpoint Tests
# ---------------------------------------------------------------------------

def test_trigger_incident_rca_api_endpoint(client, db_session):
    """
    Test POST /api/incidents/{incident_id}/analyze REST endpoint.
    """
    inc = IncidentModel(
        id="INC-API-RCA",
        service_name="auth-service",
        title="Auth Latency Spike",
        severity="HIGH",
        status="OPEN",
        affected_events=[
            {"metric": "cpu_usage", "value": 91.0, "severity": "CRITICAL"},
        ],
    )
    db_session.add(inc)
    db_session.commit()

    response = client.post("/api/incidents/INC-API-RCA/analyze")
    assert response.status_code == 200
    data = response.json()

    assert data["incident_id"] == "INC-API-RCA"
    assert "analysis" in data
    assert "probable_root_cause" in data["analysis"]
    assert "confidence_score" in data["analysis"]
    assert "evidence" in data["analysis"]
    assert "recommended_actions" in data["analysis"]
    assert "impact_summary" in data["analysis"]
