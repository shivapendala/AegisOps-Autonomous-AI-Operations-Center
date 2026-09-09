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
from database.models.recommendation import RecommendationModel

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
        title="Payment Gateway P99 Latency SLA Violation",
        description="P99 response duration reached 845ms exceeding 300ms threshold",
        severity="HIGH",
        status="ACTIVE",
        source="scikit-learn-detector",
        trigger_value=845.0,
        threshold_value=300.0,
    )
    alert_2 = AlertModel(
        service_id=svc_payment.id,
        title="Payment Processor 5xx Error Spike",
        description="Elevated error rate at 4.8% on payments-k8s-01",
        severity="MEDIUM",
        status="ACTIVE",
        source="anomaly-detection-engine",
        trigger_value=4.8,
        threshold_value=1.0,
    )
    alert_3 = AlertModel(
        service_id=svc_gateway.id,
        title="Ingress Traffic Surpassed Baseline",
        description="Traffic volume is 18% higher than typical diurnal cycle",
        severity="INFO",
        status="RESOLVED",
        source="baseline-model",
        trigger_value=2450.0,
        threshold_value=2000.0,
        resolved_at=datetime.now(timezone.utc),
    )
    db.add_all([alert_1, alert_2, alert_3])
    db.flush()

    # 5. Seed Incidents with Events & Recommendations
    incident_id = "INC-PAY-8821"
    incident_1 = IncidentModel(
        id=incident_id,
        service_id=svc_payment.id,
        title="Payment Gateway Connection Degradation",
        description="Sustained P99 latency elevation and sporadic downstream connection timeouts.",
        severity="HIGH",
        status="INVESTIGATING",
        root_cause="Downstream bank gateway handshake latency and connection pool bottleneck.",
        impact_summary="Up to 4.8% of checkout authorizations experiencing high latency.",
        ai_remediation="Activate secondary failover gateway route and scale connection pool buffer.",
        anomaly_score=-0.285,
        metadata_json={"impacted_users_estimate": 140, "region": "us-east"},
    )
    db.add(incident_1)
    db.flush()

    # Incident Events Timeline
    events = [
        IncidentEventModel(
            incident_id=incident_id,
            event_type="ANOMALY_DETECTED",
            description="scikit-learn IsolationForest scored payment-processor latency at -0.285 (outlier).",
            actor="AegisOps-AI-Engine",
            event_data={"metric": "latency_p99", "observed": 845.0},
        ),
        IncidentEventModel(
            incident_id=incident_id,
            event_type="INCIDENT_OPENED",
            description="Autonomous incident ticket generated and triage sequence initiated.",
            actor="AegisOps-Autopilot",
            event_data={"severity": "HIGH"},
        ),
        IncidentEventModel(
            incident_id=incident_id,
            event_type="ROOT_CAUSE_ANALYSIS",
            description="LLM reasoning engine identified downstream connection saturation.",
            actor="BaseLLMService[mock]",
            event_data={"confidence": 0.92},
        ),
    ]
    db.add_all(events)

    # AI Recommendations
    recs = [
        RecommendationModel(
            incident_id=incident_id,
            title="Reroute Transactions to Standby Payment Provider",
            description="Shift 50% of card checkout traffic to secondary payment processor endpoint to relieve pool queue.",
            action_type="TRAFFIC_REROUTE",
            confidence=0.94,
            priority="P1",
            status="PENDING",
            generated_by="AegisOps-AI-LLM",
        ),
        RecommendationModel(
            incident_id=incident_id,
            title="Expand Connection Pool Capacity",
            description="Dynamically increase max_connections from 50 to 120 on payments worker pods.",
            action_type="CONFIG_SCALE",
            confidence=0.88,
            priority="P2",
            status="PENDING",
            generated_by="AegisOps-AI-LLM",
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
