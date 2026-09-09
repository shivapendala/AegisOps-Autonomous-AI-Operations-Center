"""
Database initialization and seeding script.
Creates all tables for:
users, services, metrics, alerts, incidents, incident_events, recommendations.
Seeds initial sample data if tables are empty.
"""

from datetime import datetime, timezone
import logging
from sqlalchemy.orm import Session
from database.session import SessionLocal, init_database
from database.models.user import UserModel
from database.models.service import ServiceModel
from database.models.metric import MetricModel
from database.models.alert import AlertModel
from database.models.incident import IncidentModel
from database.models.incident_event import IncidentEventModel
from database.models.recommendation import IncidentRecommendationModel, RecommendationModel

logger = logging.getLogger("aegisops.database.init")


def seed_initial_data(db: Session) -> None:
    """Seeds default sample records if the database is newly initialized."""
    # Check if services exist
    if db.query(ServiceModel).count() > 0:
        logger.info("Database already contains records; skipping initial seeding.")
        return

    logger.info("Seeding initial AegisOps operational data...")

    # 1. Seed Users
    admin_user = UserModel(
        username="admin",
        email="admin@aegisops.internal",
        full_name="Operations Administrator",
        role="ADMIN",
        is_active=True,
    )
    sre_user = UserModel(
        username="sre_lead",
        email="sre@aegisops.internal",
        full_name="Lead Site Reliability Engineer",
        role="OPERATOR",
        is_active=True,
    )
    db.add_all([admin_user, sre_user])
    db.flush()

    # 2. Seed Services
    svc_gateway = ServiceModel(
        name="api-gateway",
        description="Public Edge Ingress and Reverse Proxy",
        status="HEALTHY",
        tier="CRITICAL",
        endpoint_url="https://api.aegisops.internal",
    )
    svc_auth = ServiceModel(
        name="auth-service",
        description="Authentication and Identity Provider",
        status="HEALTHY",
        tier="CRITICAL",
        endpoint_url="https://auth.aegisops.internal",
    )
    svc_payment = ServiceModel(
        name="payment-processor",
        description="Transaction and Payment Settlement Pipeline",
        status="DEGRADED",
        tier="CRITICAL",
        endpoint_url="https://payments.aegisops.internal",
    )
    svc_telemetry = ServiceModel(
        name="telemetry-pipeline",
        description="Real-time Stream Ingestion and Metric Aggregation",
        status="HEALTHY",
        tier="STANDARD",
        endpoint_url="https://telemetry.aegisops.internal",
    )
    db.add_all([svc_gateway, svc_auth, svc_payment, svc_telemetry])
    db.flush()

    # 3. Seed Metrics
    metrics_data = [
        MetricModel(
            service_id=svc_gateway.id,
            metric_name="request_rate",
            value=2450.0,
            unit="req/s",
            dimensions={"region": "us-east", "env": "prod"},
        ),
        MetricModel(
            service_id=svc_gateway.id,
            metric_name="latency_p99",
            value=14.2,
            unit="ms",
            dimensions={"region": "us-east", "env": "prod"},
        ),
        MetricModel(
            service_id=svc_payment.id,
            metric_name="error_rate_5xx",
            value=4.8,
            unit="%",
            dimensions={"cluster": "payments-k8s-01"},
        ),
        MetricModel(
            service_id=svc_payment.id,
            metric_name="latency_p99",
            value=845.0,
            unit="ms",
            dimensions={"cluster": "payments-k8s-01"},
        ),
        MetricModel(
            service_id=svc_auth.id,
            metric_name="jwt_verification_latency",
            value=2.4,
            unit="ms",
            dimensions={"cache": "redis-auth"},
        ),
        MetricModel(
            service_id=svc_telemetry.id,
            metric_name="queue_backlog",
            value=120.0,
            unit="messages",
            dimensions={"broker": "kafka-cluster-ops"},
        ),
    ]
    db.add_all(metrics_data)
    db.flush()

    # 4. Seed Alerts
    alert_1 = AlertModel(
        service_id=svc_payment.id,
        service=svc_payment.name,
        metric="latency_p99",
        value=845.0,
        threshold=300.0,
        severity="HIGH",
        status="ACTIVE",
        source="scikit-learn-detector",
        message="P99 response duration reached 845ms exceeding 300ms threshold",
    )
    alert_2 = AlertModel(
        service_id=svc_payment.id,
        service=svc_payment.name,
        metric="error_rate_5xx",
        value=4.8,
        threshold=1.0,
        severity="WARNING",
        status="ACTIVE",
        source="anomaly-detection-engine",
        message="Elevated error rate at 4.8% on payments-k8s-01",
    )
    alert_3 = AlertModel(
        service_id=svc_gateway.id,
        service=svc_gateway.name,
        metric="request_rate",
        value=2450.0,
        threshold=2000.0,
        severity="WARNING",
        status="RESOLVED",
        source="baseline-model",
        message="Traffic volume is 18% higher than typical diurnal cycle",
        resolved_at=datetime.now(timezone.utc),
    )
    db.add_all([alert_1, alert_2, alert_3])
    db.flush()

    # 5. Seed Incidents with Events & Recommendations
    incident_1 = IncidentModel(
        id="INC-101",
        service_id=svc_payment.id,
        title="Payment API Degradation",
        description="Sustained P99 latency elevation, database connection saturation, and HTTP 500 surge.",
        severity="CRITICAL",
        status="OPEN",
        correlation_score=91.0,
        probable_cause="Database connection pool exhaustion",
        confidence_score=91.0,
        root_cause="Database connection pool exhaustion",
        impact_summary="Payment API requests are experiencing failures because database connections are saturated.",
        ai_remediation="Check database connection pool, inspect long-running queries, and review deployments.",
        anomaly_score=-0.285,
        metadata_json={
            "ai_root_cause_analysis": {
                "probable_cause": "Database connection pool exhaustion",
                "confidence_score": 91.0,
                "evidence": [
                    "DB connections reached 96%",
                    "API latency increased to 2.8 seconds",
                    "HTTP 500 errors increased",
                    "Payment requests timed out"
                ],
                "recommended_actions": [
                    "Check database connection pool",
                    "Inspect long-running queries",
                    "Check database CPU and memory",
                    "Review recent Payment API deployments"
                ]
            }
        },
    )

    incident_2 = IncidentModel(
        id="INC-102",
        service_id=svc_auth.id,
        title="Auth API High Latency",
        description="JWT token verification latency spike during cache failover.",
        severity="HIGH",
        status="RESOLVED",
        correlation_score=85.0,
        probable_cause="Redis cache token eviction storm",
        confidence_score=88.0,
        root_cause="Redis cache token eviction storm",
        impact_summary="Token verification latency temporarily elevated prior to Redis replica warm-up.",
        ai_remediation="Flushed cache keyspace buffers and scaled replica nodes.",
        resolved_at=datetime.now(timezone.utc),
        metadata_json={
            "ai_root_cause_analysis": {
                "probable_cause": "Redis cache token eviction storm",
                "confidence_score": 88.0,
                "evidence": [
                    "JWT verification latency spiked to 240ms",
                    "Redis cache hit ratio dropped to 62%"
                ],
                "recommended_actions": [
                    "Scale Redis cache replicas",
                    "Verify JWT cache TTLs"
                ]
            }
        },
    )
    db.add_all([incident_1, incident_2])
    db.flush()

    # Incident Events Timeline (Connecting Alerts to Incidents)
    events = [
        IncidentEventModel(
            incident_id="INC-101",
            alert_id=alert_1.id,
            event_type="ALERT_ATTACHED",
            description=f"Alert #{alert_1.id} ({alert_1.metric}) connected to incident",
            actor="AegisOps-CorrelationEngine",
            event_data={"metric": "latency_p99", "observed": 845.0},
        ),
        IncidentEventModel(
            incident_id="INC-101",
            alert_id=alert_2.id,
            event_type="ALERT_ATTACHED",
            description=f"Alert #{alert_2.id} ({alert_2.metric}) connected to incident",
            actor="AegisOps-CorrelationEngine",
            event_data={"metric": "error_rate_5xx", "observed": 4.8},
        ),
        IncidentEventModel(
            incident_id="INC-101",
            event_type="INCIDENT_OPENED",
            description="Autonomous incident ticket generated and triage sequence initiated.",
            actor="AegisOps-Autopilot",
            event_data={"severity": "CRITICAL"},
        ),
        IncidentEventModel(
            incident_id="INC-101",
            event_type="AI_RCA_COMPLETED",
            description="AI Root Cause Analysis completed: Database connection pool exhaustion (91% confidence).",
            actor="MockAIProvider",
            event_data={"confidence": 91.0},
        ),
        IncidentEventModel(
            incident_id="INC-102",
            event_type="INCIDENT_RESOLVED",
            description="Auth API latency recovered and Redis replica cache normalized.",
            actor="Operations Console",
            event_data={"status": "RESOLVED"},
        ),
    ]
    db.add_all(events)

    # Incident Recommendations
    recs = [
        IncidentRecommendationModel(
            incident_id="INC-101",
            action="Check database connection pool",
            priority="HIGH",
            status="PENDING",
            title="Check database connection pool",
            description="Inspect active connections and increase max pool limit if saturated.",
            action_type="CONFIG_SCALE",
            confidence=0.91,
            generated_by="MockAIProvider",
        ),
        IncidentRecommendationModel(
            incident_id="INC-101",
            action="Inspect long-running queries",
            priority="HIGH",
            status="PENDING",
            title="Inspect long-running queries",
            description="Identify unindexed queries causing connection locks.",
            action_type="QUERY_AUDIT",
            confidence=0.89,
            generated_by="MockAIProvider",
        ),
        IncidentRecommendationModel(
            incident_id="INC-101",
            action="Check database CPU and memory",
            priority="MEDIUM",
            status="PENDING",
            title="Check database CPU and memory",
            description="Verify database host resource headroom.",
            action_type="RESOURCE_AUDIT",
            confidence=0.82,
            generated_by="MockAIProvider",
        ),
        IncidentRecommendationModel(
            incident_id="INC-101",
            action="Review recent Payment API deployments",
            priority="MEDIUM",
            status="PENDING",
            title="Review recent Payment API deployments",
            description="Audit recent service deployments and database migration commits.",
            action_type="DEPLOYMENT_AUDIT",
            confidence=0.78,
            generated_by="MockAIProvider",
        ),
        IncidentRecommendationModel(
            incident_id="INC-102",
            action="Scale Redis cache replicas",
            priority="HIGH",
            status="EXECUTED",
            title="Scale Redis cache replicas",
            description="Scale Redis cache replicas to prevent cache misses on JWT token verification.",
            action_type="CONFIG_SCALE",
            confidence=0.88,
            generated_by="MockAIProvider",
        ),
    ]
    db.add_all(recs)

    db.commit()
    logger.info("Database initialized and sample operational data seeded successfully.")


def setup_and_seed():
    """Initializes schema and runs seeding."""
    init_database()
    db = SessionLocal()
    try:
        seed_initial_data(db)
    finally:
        db.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    setup_and_seed()
