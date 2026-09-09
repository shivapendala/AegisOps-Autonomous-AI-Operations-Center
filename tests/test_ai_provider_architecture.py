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
    assert any("db connection" in e.lower() or "database connection" in e.lower() for e in result.evidence)
    assert any("latency" in e.lower() for e in result.evidence)
    assert len(result.recommended_actions) >= 2
    assert any("database connection pool" in a.lower() for a in result.recommended_actions)
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


def test_step8_ai_root_cause_analysis_exact_example():
    """
    STEP 8 Verification:
    AI receives:
      Incident + Alerts + Metrics + Service information
    Input:
      Service: Payment API
      CPU: 94%
      Memory: 81%
      DB connections: 96%
      API latency: 2.8 sec
      HTTP 500: 18%
    AI produces:
      Probable Root Cause: Database connection pool exhaustion
      Confidence: 91%
      Evidence:
      - DB connections reached 96%
      - API latency increased to 2.8 seconds
      - HTTP 500 errors increased
      - Payment requests timed out
    """
    provider = MockAIProvider()

    investigation = IncidentInvestigation(
        incident_id="INC-STEP8-PAYMENT",
        incident_info={
            "id": "INC-STEP8-PAYMENT",
            "title": "Payment API degradation",
            "service": "Payment API",
            "severity": "CRITICAL",
        },
        service_info={
            "name": "Payment API",
            "type": "REST API",
            "status": "DEGRADED",
        },
        correlated_alerts=[
            {"metric": "CPU", "value": 94.0, "severity": "HIGH", "message": "High CPU utilization"},
            {"metric": "DB connections", "value": 96.0, "severity": "HIGH", "message": "Database pool saturation"},
            {"metric": "API latency", "value": 2.8, "severity": "HIGH", "message": "High API response time"},
            {"metric": "HTTP 500", "value": 18.0, "severity": "CRITICAL", "message": "High HTTP 500 error rate"},
        ],
        recent_metrics={
            "CPU": 94.0,
            "Memory": 81.0,
            "DB connections": 96.0,
            "API latency": 2.8,
            "HTTP 500": 18.0,
        },
    )

    rca = provider.analyze_incident_sync(investigation)

    # 1. Probable Root Cause: Database connection pool exhaustion
    assert rca.probable_root_cause == "Database connection pool exhaustion"

    # 2. Confidence: 91%
    assert round(rca.confidence_score, 2) == 0.91 or rca.confidence_score == 91.0 or int(rca.confidence_score) == 91

    # 3. Evidence
    expected_evidence = [
        "DB connections reached 96%",
        "API latency increased to 2.8 seconds",
        "HTTP 500 errors increased",
        "Payment requests timed out",
    ]
    for exp in expected_evidence:
        assert exp in rca.evidence, f"Missing expected evidence: {exp}"


def test_step9_store_ai_investigation_in_incidents_table(db_session):
    """
    STEP 9 Verification:
    Save AI output into:
      incidents table
    Stores:
      probable_cause: Database connection pool exhaustion
      confidence_score: 91
      impact_summary: Payment API requests are experiencing failures because database connections are saturated.
    Ensures persistent database storage across queries.
    """
    now = datetime.now(timezone.utc)

    # 1. Create open incident for Payment API
    inc = IncidentModel(
        id="INC-STEP9-STORE",
        service_name="Payment API",
        title="Payment API Degradation",
        severity="CRITICAL",
        status="OPEN",
        correlation_score=94.0,
        affected_metrics=["CPU", "DB connections", "API latency", "HTTP 500"],
        created_at=now,
        updated_at=now,
    )
    db_session.add(inc)

    # 2. Attach alerts
    alert = AlertModel(
        id=901,
        service="Payment API",
        metric="DB connections",
        value=96.0,
        threshold=80.0,
        severity="HIGH",
        status="ACTIVE",
        message="Database connections saturated at 96%",
        timestamp=now,
    )
    db_session.add(alert)
    db_session.flush()

    evt = IncidentEventModel(
        incident_id=inc.id,
        alert_id=901,
        event_type="ALERT_ATTACHED",
        description="Alert #901 attached",
        created_at=now,
    )
    db_session.add(evt)
    db_session.commit()

    # 3. Run Investigator with persist=True
    investigator = IncidentInvestigator(provider=MockAIProvider())
    rca = investigator.investigate_sync(inc.id, db_session, persist=True)

    # 4. Refresh and query from incidents table
    db_session.expire_all()
    persisted = db_session.query(IncidentModel).filter(IncidentModel.id == "INC-STEP9-STORE").first()
    assert persisted is not None

    # Verify probable_cause
    assert persisted.probable_cause == "Database connection pool exhaustion"
    assert persisted.root_cause == "Database connection pool exhaustion"

    # Verify confidence_score: 91
    assert persisted.confidence_score == 91.0 or int(persisted.confidence_score) == 91

    # Verify impact_summary:
    # "Payment API requests are experiencing failures because database connections are saturated."
    assert "Payment API requests are experiencing failures because database connections are saturated." in persisted.impact_summary

    # Verify recommendations and timeline event are also stored
    recs = db_session.query(IncidentRecommendationModel).filter(IncidentRecommendationModel.incident_id == inc.id).all()
    assert len(recs) >= 1
    assert any("database connection pool" in r.action.lower() for r in recs)

    # Verify JSON metadata also holds full analysis record
    assert persisted.metadata_json is not None
    assert "ai_root_cause_analysis" in persisted.metadata_json
    ai_meta = persisted.metadata_json["ai_root_cause_analysis"]
    assert ai_meta["probable_root_cause"] == "Database connection pool exhaustion"


def test_step10_generate_recommended_actions_exact_items_and_priorities():
    """
    STEP 10 Verification - Recommended Actions Generation:
    AI should recommend actions:
      1. Check database connection pool (Priority: HIGH)
      2. Inspect long-running queries (Priority: HIGH)
      3. Check database CPU and memory (Priority: MEDIUM)
      4. Review recent Payment API deployments (Priority: MEDIUM)
    """
    provider = MockAIProvider()

    investigation = IncidentInvestigation(
        incident_id="INC-STEP10-REC",
        incident_info={
            "id": "INC-STEP10-REC",
            "title": "Payment API degradation",
            "service": "Payment API",
            "severity": "CRITICAL",
        },
        service_info={
            "name": "Payment API",
            "status": "DEGRADED",
        },
        correlated_alerts=[
            {"metric": "CPU", "value": 94.0, "severity": "HIGH"},
            {"metric": "DB connections", "value": 96.0, "severity": "HIGH"},
            {"metric": "API latency", "value": 2.8, "severity": "HIGH"},
            {"metric": "HTTP 500", "value": 18.0, "severity": "CRITICAL"},
        ],
        recent_metrics={
            "CPU": 94.0,
            "DB connections": 96.0,
            "API latency": 2.8,
            "HTTP 500": 18.0,
        },
    )

    rca = provider.analyze_incident_sync(investigation)

    # Verify recommended actions list contains exact items
    expected_actions = [
        ("Check database connection pool", "HIGH"),
        ("Inspect long-running queries", "HIGH"),
        ("Check database CPU and memory", "MEDIUM"),
        ("Review recent Payment API deployments", "MEDIUM"),
    ]

    action_map = {item["action"]: item["priority"] for item in rca.recommended_action_items}
    for expected_action, expected_priority in expected_actions:
        assert expected_action in rca.recommended_actions, f"Missing action in recommended_actions: {expected_action}"
        assert expected_action in action_map, f"Missing action in recommended_action_items: {expected_action}"
        assert action_map[expected_action] == expected_priority, (
            f"Action '{expected_action}' expected priority {expected_priority}, got {action_map[expected_action]}"
        )


def test_step10_safety_rule_ai_does_not_auto_execute_and_human_in_the_loop_workflow(client, db_session):
    """
    STEP 10 Verification - Important Safety Rule & Human-in-the-Loop:
    1. AI generates recommendations in PENDING status.
    2. AI should NOT automatically execute commands (status remains PENDING).
    3. Flow: AI -> Recommendation -> Human Operator -> Approval -> Action.
    4. Attempting to execute unapproved action MUST be blocked (HTTP 400).
    5. After Human Operator approves, execution succeeds (HTTP 200).
    """
    now = datetime.now(timezone.utc)

    # 1. Create Incident
    inc = IncidentModel(
        id="INC-STEP10-HITL",
        service_name="Payment API",
        title="Payment API Degradation",
        severity="CRITICAL",
        status="OPEN",
        correlation_score=95.0,
        affected_metrics=["DB connections", "API latency"],
        created_at=now,
        updated_at=now,
    )
    db_session.add(inc)

    alert = AlertModel(
        id=1001,
        service="Payment API",
        metric="DB connections",
        value=96.0,
        threshold=80.0,
        severity="HIGH",
        status="ACTIVE",
        message="Database connections saturated at 96%",
        timestamp=now,
    )
    db_session.add(alert)
    db_session.flush()

    evt = IncidentEventModel(
        incident_id=inc.id,
        alert_id=1001,
        event_type="ALERT_ATTACHED",
        description="Alert #1001 attached",
        created_at=now,
    )
    db_session.add(evt)
    db_session.commit()

    # 2. Trigger AI Investigation
    investigator = IncidentInvestigator(provider=MockAIProvider())
    investigator.investigate_sync(inc.id, db_session, persist=True)

    # 3. SAFETY CHECK: Verify all recommendations are PENDING (AI did NOT auto-execute)
    recs = (
        db_session.query(IncidentRecommendationModel)
        .filter(IncidentRecommendationModel.incident_id == inc.id)
        .order_by(IncidentRecommendationModel.id.asc())
        .all()
    )
    assert len(recs) == 4
    for r in recs:
        assert r.status == "PENDING", f"Safety violation: recommendation {r.id} is {r.status}, expected PENDING!"

    rec1 = recs[0]  # "Check database connection pool"
    rec2 = recs[1]  # "Inspect long-running queries"

    # 4. SAFETY VIOLATION CHECK: Try to execute unapproved recommendation directly
    exec_resp = client.post(
        f"/api/incidents/{inc.id}/recommendations/{rec1.id}/execute",
        json={"operator": "Rogue-Process", "execution_notes": "Attempting auto-execution without approval"},
    )
    assert exec_resp.status_code == 400
    assert "Safety Violation" in exec_resp.json()["detail"]

    # Verify rec1 is still PENDING
    db_session.refresh(rec1)
    assert rec1.status == "PENDING"

    # 5. HUMAN OPERATOR APPROVAL: Operator reviews and approves
    approve_resp = client.post(
        f"/api/incidents/{inc.id}/recommendations/{rec1.id}/approve",
        json={"operator": "Operations-Engineer-Alice", "notes": "Approved: expanding connection pool to 200"},
    )
    assert approve_resp.status_code == 200
    approved_data = approve_resp.json()
    assert approved_data["status"] == "APPROVED"

    db_session.refresh(rec1)
    assert rec1.status == "APPROVED"

    # Verify approval audit event logged in timeline
    approval_event = (
        db_session.query(IncidentEventModel)
        .filter(
            IncidentEventModel.incident_id == inc.id,
            IncidentEventModel.event_type == "RECOMMENDATION_APPROVED",
        )
        .first()
    )
    assert approval_event is not None
    assert approval_event.actor == "Operations-Engineer-Alice"

    # 6. ACTION EXECUTION: Now that it is APPROVED, operator triggers action
    exec_approved_resp = client.post(
        f"/api/incidents/{inc.id}/recommendations/{rec1.id}/execute",
        json={"operator": "Operations-Engineer-Alice", "execution_notes": "Executed pool resize playbook"},
    )
    assert exec_approved_resp.status_code == 200
    exec_data = exec_approved_resp.json()
    assert exec_data["status"] == "EXECUTED"

    db_session.refresh(rec1)
    assert rec1.status == "EXECUTED"

    # 7. REJECTION FLOW: Operator rejects rec2
    reject_resp = client.post(
        f"/api/incidents/{inc.id}/recommendations/{rec2.id}/reject",
        json={"operator": "Operations-Engineer-Alice", "reason": "Query optimization scheduled for next sprint"},
    )
    assert reject_resp.status_code == 200
    assert reject_resp.json()["status"] == "REJECTED"

    db_session.refresh(rec2)
    assert rec2.status == "REJECTED"

    # Try to execute rejected recommendation -> Must fail
    exec_rejected = client.post(
        f"/api/incidents/{inc.id}/recommendations/{rec2.id}/execute",
        json={"operator": "Operations-Engineer-Alice"},
    )
    assert exec_rejected.status_code == 400
    assert "Safety Violation" in exec_rejected.json()["detail"]



