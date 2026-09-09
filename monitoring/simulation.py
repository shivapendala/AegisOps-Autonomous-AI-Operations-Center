"""
AegisOps Realistic Monitoring Simulation Engine.
Models 5 production microservices:
1. Payment API
2. Authentication API
3. Order Service
4. PostgreSQL Database
5. Notification Service

Each service models:
- latency (ms)
- request_rate (req/s)
- error_rate (%)
- cpu (%)
- memory (%)
- database_connections (count or %)

Supports 6 operational failure scenarios:
1. NORMAL
2. HIGH_CPU
3. DATABASE_OVERLOAD
4. API_LATENCY_SPIKE
5. ERROR_RATE_SPIKE
6. COMBINED_PAYMENT_FAILURE

Under COMBINED_PAYMENT_FAILURE, multiple cascading events are emitted within a short period:
- CPU: 92%
- Database connections: 95%
- API latency: 2.8s (2800ms)
- HTTP 500 errors: 14.5%
The correlation engine deterministically combines them into ONE incident.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import logging
import random
from typing import Any, Callable, Dict, List, Optional, Tuple
import uuid

from sqlalchemy.orm import Session
from database.session import SessionLocal
from database.models.service import ServiceModel
from database.models.alert import AlertModel
from database.models.metric import MetricModel
from database.models.incident import IncidentModel
from database.models.incident_event import IncidentEventModel
from monitoring.correlation_engine import CorrelatedIncident, EventCorrelationEngine

logger = logging.getLogger("aegisops.monitoring.simulation")


class FailureScenario(str, Enum):
    NORMAL = "NORMAL"
    HIGH_CPU = "HIGH_CPU"
    HIGH_MEMORY = "HIGH_MEMORY"
    HIGH_DISK = "HIGH_DISK"
    DATABASE_OVERLOAD = "DATABASE_OVERLOAD"
    API_LATENCY_SPIKE = "API_LATENCY_SPIKE"
    ERROR_RATE_SPIKE = "ERROR_RATE_SPIKE"
    COMBINED_PAYMENT_FAILURE = "COMBINED_PAYMENT_FAILURE"


@dataclass
class ServiceMetricsSnapshot:
    service_name: str
    service_id: Optional[int]
    latency: float  # in ms
    request_rate: float  # req/s
    error_rate: float  # %
    cpu: float  # %
    memory: float  # %
    database_connections: float  # count or %
    status: str = "HEALTHY"
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "service_name": self.service_name,
            "service_id": self.service_id,
            "latency": round(self.latency, 2),
            "request_rate": round(self.request_rate, 2),
            "error_rate": round(self.error_rate, 2),
            "cpu": round(self.cpu, 2),
            "memory": round(self.memory, 2),
            "database_connections": round(self.database_connections, 2),
            "status": self.status,
            "is_simulation": True,
            "label": "DEMO/SIMULATION",
            "timestamp": self.timestamp.isoformat(),
        }


# Canonical service specifications
SIMULATED_SERVICES_SPEC = [
    {
        "name": "Payment API",
        "description": "Credit card processing, billing settlement, and tokenized payments",
        "tier": "CRITICAL",
        "endpoint_url": "https://payments.aegisops.internal/v1",
        "base_latency": 42.0,
        "base_request_rate": 850.0,
        "base_error_rate": 0.08,
        "base_cpu": 28.0,
        "base_memory": 45.0,
        "base_db_conn": 32.0,
    },
    {
        "name": "Authentication API",
        "description": "OAuth2, JWT authentication, user sessions, and IAM permissions",
        "tier": "CRITICAL",
        "endpoint_url": "https://auth.aegisops.internal/v1",
        "base_latency": 18.0,
        "base_request_rate": 1400.0,
        "base_error_rate": 0.02,
        "base_cpu": 22.0,
        "base_memory": 38.0,
        "base_db_conn": 24.0,
    },
    {
        "name": "Order Service",
        "description": "Order placement, inventory reservation, and cart fulfillment",
        "tier": "HIGH",
        "endpoint_url": "https://orders.aegisops.internal/v1",
        "base_latency": 35.0,
        "base_request_rate": 620.0,
        "base_error_rate": 0.05,
        "base_cpu": 30.0,
        "base_memory": 42.0,
        "base_db_conn": 35.0,
    },
    {
        "name": "PostgreSQL Database",
        "description": "Primary transactional relational datastore with connection pooling",
        "tier": "CRITICAL",
        "endpoint_url": "postgresql://db.aegisops.internal:5432/production",
        "base_latency": 8.0,
        "base_request_rate": 3200.0,
        "base_error_rate": 0.01,
        "base_cpu": 35.0,
        "base_memory": 58.0,
        "base_db_conn": 38.0,
    },
    {
        "name": "Notification Service",
        "description": "Push notifications, email delivery, and SMS transaction receipts",
        "tier": "STANDARD",
        "endpoint_url": "https://notifications.aegisops.internal/v1",
        "base_latency": 25.0,
        "base_request_rate": 340.0,
        "base_error_rate": 0.12,
        "base_cpu": 19.0,
        "base_memory": 32.0,
        "base_db_conn": 15.0,
    },
]


class SimulationEngine:
    """
    Autonomous multi-service simulation engine for demonstrations and drills.
    Generates realistic telemetry fluctuations and models cascading failure scenarios.
    """

    def __init__(
        self,
        db_factory: Optional[Callable[[], Session]] = None,
        correlation_engine: Optional[EventCorrelationEngine] = None,
    ):
        self.db_factory = db_factory or SessionLocal
        self.correlation_engine = correlation_engine or EventCorrelationEngine(
            window_seconds=60, threshold_score=60.0
        )
        self.active_scenario: FailureScenario = FailureScenario.NORMAL
        self.scenario_start_time: datetime = datetime.now(timezone.utc)
        self._service_id_map: Dict[str, int] = {}
        self._active_simulated_alerts: Dict[str, dict] = {}
        self._last_snapshots: Dict[str, ServiceMetricsSnapshot] = {}
        self._step_counter: int = 0
        self._running: bool = False
        self._task: Optional[asyncio.Task] = None

    def ensure_services_seeded(self) -> None:
        """Ensures all 5 simulated services exist in the database with IDs mapped."""
        db = self.db_factory()
        try:
            for spec in SIMULATED_SERVICES_SPEC:
                svc = db.query(ServiceModel).filter(ServiceModel.name == spec["name"]).first()
                if not svc:
                    svc = ServiceModel(
                        name=spec["name"],
                        description=spec["description"],
                        tier=spec["tier"],
                        status="HEALTHY",
                        endpoint_url=spec["endpoint_url"],
                    )
                    db.add(svc)
                    db.commit()
                    db.refresh(svc)
                self._service_id_map[spec["name"]] = svc.id
        except Exception as err:
            logger.error("Error seeding simulated services: %s", err)
            db.rollback()
        finally:
            db.close()

    def set_scenario(self, scenario: str) -> Dict[str, Any]:
        """Activates a failure scenario or returns to normal."""
        try:
            scen_enum = FailureScenario(scenario.upper())
        except ValueError:
            # Match common alias names
            aliases = {
                "NORMAL": FailureScenario.NORMAL,
                "RECOVER": FailureScenario.NORMAL,
                "RECOVER_SYSTEM": FailureScenario.NORMAL,
                "CPU": FailureScenario.HIGH_CPU,
                "CPU_SPIKE": FailureScenario.HIGH_CPU,
                "HIGH_CPU": FailureScenario.HIGH_CPU,
                "HIGH_MEMORY": FailureScenario.HIGH_MEMORY,
                "MEMORY": FailureScenario.HIGH_MEMORY,
                "MEMORY_SPIKE": FailureScenario.HIGH_MEMORY,
                "HIGH_DISK": FailureScenario.HIGH_DISK,
                "DISK": FailureScenario.HIGH_DISK,
                "DISK_SPIKE": FailureScenario.HIGH_DISK,
                "DB": FailureScenario.DATABASE_OVERLOAD,
                "DATABASE_OVERLOAD": FailureScenario.DATABASE_OVERLOAD,
                "DATABASE": FailureScenario.DATABASE_OVERLOAD,
                "API_LATENCY": FailureScenario.API_LATENCY_SPIKE,
                "LATENCY_SPIKE": FailureScenario.API_LATENCY_SPIKE,
                "API_LATENCY_SPIKE": FailureScenario.API_LATENCY_SPIKE,
                "ERROR_RATE": FailureScenario.ERROR_RATE_SPIKE,
                "ERROR_RATE_SPIKE": FailureScenario.ERROR_RATE_SPIKE,
                "PAYMENT": FailureScenario.COMBINED_PAYMENT_FAILURE,
                "PAYMENT_FAILURE": FailureScenario.COMBINED_PAYMENT_FAILURE,
                "COMBINED_PAYMENT_FAILURE": FailureScenario.COMBINED_PAYMENT_FAILURE,
            }
            scen_enum = aliases.get(scenario.upper(), FailureScenario.NORMAL)

        self.active_scenario = scen_enum
        self.scenario_start_time = datetime.now(timezone.utc)
        logger.info("Simulation scenario transitioned to: %s", self.active_scenario.value)

        # If recovering to normal, resolve active alerts
        if self.active_scenario == FailureScenario.NORMAL:
            self._resolve_all_simulated_alerts()

        # Step immediately to propagate changes
        self.step()
        return self.get_status()

    def _resolve_all_simulated_alerts(self) -> None:
        """Resolves all active simulation alerts and resets service statuses to HEALTHY."""
        db = self.db_factory()
        now = datetime.now(timezone.utc)
        try:
            # Mark active simulation alerts as resolved in DB
            db.query(AlertModel).filter(
                AlertModel.source == "simulation-engine",
                AlertModel.status == "ACTIVE"
            ).update({"status": "RESOLVED", "resolved_at": now})

            # Mark all simulated services as HEALTHY
            for svc_name in self._service_id_map.keys():
                db.query(ServiceModel).filter(ServiceModel.name == svc_name).update({"status": "HEALTHY"})

            db.commit()
            self._active_simulated_alerts.clear()
        except Exception as err:
            logger.error("Error resolving simulated alerts: %s", err)
            db.rollback()
        finally:
            db.close()

    def generate_service_metrics(
        self, spec: Dict[str, Any], now: datetime
    ) -> Tuple[ServiceMetricsSnapshot, List[dict]]:
        """
        Calculates realistic metrics for a specific service based on current failure scenario.
        Returns the snapshot and any newly generated alerts.
        """
        svc_name = spec["name"]
        svc_id = self._service_id_map.get(svc_name)
        noise = lambda base, variance: max(0.0, base + (random.random() * 2 - 1) * variance)

        latency = noise(spec["base_latency"], 3.0)
        req_rate = noise(spec["base_request_rate"], 30.0)
        err_rate = noise(spec["base_error_rate"], 0.02)
        cpu = noise(spec["base_cpu"], 2.5)
        memory = noise(spec["base_memory"], 1.5)
        db_conn = noise(spec["base_db_conn"], 2.0)
        status = "HEALTHY"
        alerts: List[dict] = []

        # -------------------------------------------------------------
        # 1. SCENARIO: HIGH_CPU (Spike on Order Service & Host)
        # -------------------------------------------------------------
        if self.active_scenario == FailureScenario.HIGH_CPU:
            if svc_name == "Order Service":
                cpu = 94.5 + random.uniform(-1.5, 2.5)
                latency = 210.0 + random.uniform(-10.0, 30.0)
                status = "CRITICAL"
                alerts.append({
                    "id": f"ALT-SIM-CPU-{uuid.uuid4().hex[:6].upper()}",
                    "service": svc_name,
                    "service_id": svc_id,
                    "metric": "cpu_usage",
                    "value": round(cpu, 2),
                    "threshold": 90.0,
                    "severity": "CRITICAL",
                    "message": f"[DEMO/SIMULATION] CPU critical overload on {svc_name}: {cpu:.1f}% (threshold: 90.0%)",
                    "timestamp": now,
                    "status": "ACTIVE",
                })
            elif svc_name in ["Payment API", "PostgreSQL Database"]:
                cpu = min(cpu + 15.0, 75.0)

        # -------------------------------------------------------------
        # SCENARIO: HIGH_MEMORY (Severe RAM exhaustion)
        # -------------------------------------------------------------
        elif self.active_scenario == FailureScenario.HIGH_MEMORY:
            if svc_name in ["Payment API", "Order Service"]:
                memory = 94.2 + random.uniform(-1.0, 2.5)
                cpu = min(cpu + 20.0, 85.0)
                status = "CRITICAL"
                alerts.append({
                    "id": f"ALT-SIM-MEM-{uuid.uuid4().hex[:6].upper()}",
                    "service": svc_name,
                    "service_id": svc_id,
                    "metric": "memory_usage",
                    "value": round(memory, 2),
                    "threshold": 90.0,
                    "severity": "CRITICAL",
                    "message": f"[DEMO/SIMULATION] Memory exhaustion breach on {svc_name}: {memory:.1f}% (threshold: 90.0%)",
                    "timestamp": now,
                    "status": "ACTIVE",
                })
            else:
                memory = min(memory + 25.0, 82.0)

        # -------------------------------------------------------------
        # SCENARIO: HIGH_DISK (Storage volume saturation)
        # -------------------------------------------------------------
        elif self.active_scenario == FailureScenario.HIGH_DISK:
            if svc_name in ["PostgreSQL Database", "Order Service"]:
                db_conn = min(db_conn + 25.0, 88.0)
                status = "CRITICAL"
                alerts.append({
                    "id": f"ALT-SIM-DISK-{uuid.uuid4().hex[:6].upper()}",
                    "service": svc_name,
                    "service_id": svc_id,
                    "metric": "disk_usage",
                    "value": 93.8,
                    "threshold": 90.0,
                    "severity": "CRITICAL",
                    "message": f"[DEMO/SIMULATION] Disk storage critical volume saturation on {svc_name}: 93.8% (threshold: 90.0%)",
                    "timestamp": now,
                    "status": "ACTIVE",
                })

        # -------------------------------------------------------------
        # 2. SCENARIO: DATABASE_OVERLOAD (PostgreSQL Database saturation)
        # -------------------------------------------------------------
        elif self.active_scenario == FailureScenario.DATABASE_OVERLOAD:
            if svc_name == "PostgreSQL Database":
                db_conn = 96.8 + random.uniform(-1.0, 2.0)
                latency = 480.0 + random.uniform(-20.0, 50.0)
                cpu = 88.0 + random.uniform(-2.0, 4.0)
                memory = 89.5 + random.uniform(-1.0, 2.0)
                status = "CRITICAL"
                alerts.append({
                    "id": f"ALT-SIM-DB-{uuid.uuid4().hex[:6].upper()}",
                    "service": svc_name,
                    "service_id": svc_id,
                    "metric": "database_connections",
                    "value": round(db_conn, 2),
                    "threshold": 90.0,
                    "severity": "CRITICAL",
                    "message": f"[DEMO/SIMULATION] Connection pool exhaustion on {svc_name}: {db_conn:.1f}% (threshold: 90.0%)",
                    "timestamp": now,
                    "status": "ACTIVE",
                })
                alerts.append({
                    "id": f"ALT-SIM-DBLAT-{uuid.uuid4().hex[:6].upper()}",
                    "service": svc_name,
                    "service_id": svc_id,
                    "metric": "db_latency",
                    "value": round(latency, 2),
                    "threshold": 200.0,
                    "severity": "HIGH",
                    "message": f"[DEMO/SIMULATION] Query latency critical: {latency:.1f}ms on {svc_name}",
                    "timestamp": now,
                    "status": "ACTIVE",
                })
            elif svc_name in ["Payment API", "Order Service"]:
                db_conn = min(db_conn + 45.0, 92.0)
                latency = min(latency + 120.0, 400.0)
                status = "DEGRADED"

        # -------------------------------------------------------------
        # 3. SCENARIO: API_LATENCY_SPIKE (Authentication API)
        # -------------------------------------------------------------
        elif self.active_scenario == FailureScenario.API_LATENCY_SPIKE:
            if svc_name == "Authentication API":
                latency = 1450.0 + random.uniform(-50.0, 100.0)
                cpu = 68.0 + random.uniform(-2.0, 4.0)
                status = "DEGRADED"
                alerts.append({
                    "id": f"ALT-SIM-LAT-{uuid.uuid4().hex[:6].upper()}",
                    "service": svc_name,
                    "service_id": svc_id,
                    "metric": "api_latency",
                    "value": round(latency, 2),
                    "threshold": 500.0,
                    "severity": "HIGH",
                    "message": f"[DEMO/SIMULATION] Auth API latency spike: {latency:.1f}ms (threshold: 500.0ms)",
                    "timestamp": now,
                    "status": "ACTIVE",
                })

        # -------------------------------------------------------------
        # 4. SCENARIO: ERROR_RATE_SPIKE (Notification Service)
        # -------------------------------------------------------------
        elif self.active_scenario == FailureScenario.ERROR_RATE_SPIKE:
            if svc_name == "Notification Service":
                err_rate = 22.4 + random.uniform(-2.0, 4.0)
                latency = 320.0 + random.uniform(-10.0, 20.0)
                status = "DEGRADED"
                alerts.append({
                    "id": f"ALT-SIM-ERR-{uuid.uuid4().hex[:6].upper()}",
                    "service": svc_name,
                    "service_id": svc_id,
                    "metric": "error_rate",
                    "value": round(err_rate, 2),
                    "threshold": 5.0,
                    "severity": "HIGH",
                    "message": f"[DEMO/SIMULATION] High HTTP error rate on {svc_name}: {err_rate:.1f}% (threshold: 5.0%)",
                    "timestamp": now,
                    "status": "ACTIVE",
                })

        # -------------------------------------------------------------
        # 5. SCENARIO: COMBINED_PAYMENT_FAILURE
        # Required values:
        # - CPU = 92%
        # - Database connections = 95%
        # - API latency = 2.8 seconds (2800ms)
        # - HTTP 500 errors = high (14.5%)
        # Must generate multiple related events within a short period.
        # The correlation engine must combine them into ONE incident.
        # -------------------------------------------------------------
        elif self.active_scenario == FailureScenario.COMBINED_PAYMENT_FAILURE:
            if svc_name == "Payment API":
                cpu = 92.4 + random.uniform(-0.5, 0.8)
                db_conn = 95.6 + random.uniform(-0.6, 0.9)
                latency = 2800.0 + random.uniform(-50.0, 75.0)
                err_rate = 14.8 + random.uniform(-0.5, 1.2)
                status = "CRITICAL"

                # Emit 4 cascading related alerts for Payment API
                alerts = [
                    {
                        "id": f"ALT-PAY-CPU-{uuid.uuid4().hex[:6].upper()}",
                        "service": "Payment API",
                        "service_id": svc_id,
                        "metric": "cpu_usage",
                        "value": round(cpu, 2),
                        "threshold": 90.0,
                        "severity": "CRITICAL",
                        "message": f"[DEMO/SIMULATION] Payment API worker CPU reached critical capacity: {cpu:.1f}%",
                        "timestamp": now,
                        "status": "ACTIVE",
                    },
                    {
                        "id": f"ALT-PAY-DBCONN-{uuid.uuid4().hex[:6].upper()}",
                        "service": "Payment API",
                        "service_id": svc_id,
                        "metric": "database_connections",
                        "value": round(db_conn, 2),
                        "threshold": 90.0,
                        "severity": "CRITICAL",
                        "message": f"[DEMO/SIMULATION] Payment API connection pool exhausted at {db_conn:.1f}%",
                        "timestamp": now,
                        "status": "ACTIVE",
                    },
                    {
                        "id": f"ALT-PAY-LAT-{uuid.uuid4().hex[:6].upper()}",
                        "service": "Payment API",
                        "service_id": svc_id,
                        "metric": "api_latency",
                        "value": round(latency / 1000.0, 2),  # 2.8s
                        "threshold": 1.0,
                        "severity": "CRITICAL",
                        "message": f"[DEMO/SIMULATION] Payment API response latency degraded to {latency / 1000.0:.1f}s",
                        "timestamp": now,
                        "status": "ACTIVE",
                    },
                    {
                        "id": f"ALT-PAY-500-{uuid.uuid4().hex[:6].upper()}",
                        "service": "Payment API",
                        "service_id": svc_id,
                        "metric": "http_500_errors",
                        "value": round(err_rate, 2),
                        "threshold": 5.0,
                        "severity": "CRITICAL",
                        "message": f"[DEMO/SIMULATION] Payment API HTTP 500 transaction error surge: {err_rate:.1f}%",
                        "timestamp": now,
                        "status": "ACTIVE",
                    },
                ]
            elif svc_name == "PostgreSQL Database":
                db_conn = 92.0 + random.uniform(-1.0, 2.0)
                status = "DEGRADED"

        snapshot = ServiceMetricsSnapshot(
            service_name=svc_name,
            service_id=svc_id,
            latency=latency,
            request_rate=req_rate,
            error_rate=err_rate,
            cpu=cpu,
            memory=memory,
            database_connections=db_conn,
            status=status,
            timestamp=now,
        )
        return snapshot, alerts

    def step(self) -> Dict[str, Any]:
        """
        Executes a single simulation cycle:
        1. Emits metrics for all 5 services.
        2. Generates failure scenario alerts.
        3. Feeds alerts into EventCorrelationEngine.
        4. Persists state to DB and broadcasts via WebSocket.
        """
        self._step_counter += 1
        now = datetime.now(timezone.utc)
        snapshots: List[ServiceMetricsSnapshot] = []
        all_new_alerts: List[dict] = []

        if not self._service_id_map:
            self.ensure_services_seeded()

        for spec in SIMULATED_SERVICES_SPEC:
            snap, alerts = self.generate_service_metrics(spec, now)
            snapshots.append(snap)
            self._last_snapshots[spec["name"]] = snap
            for a in alerts:
                # Deduplicate by metric and service in simulation cache
                key = f"{a['service']}:{a['metric']}"
                if key not in self._active_simulated_alerts:
                    self._active_simulated_alerts[key] = a
                    all_new_alerts.append(a)

        # Process through correlation engine
        updated_incidents: List[CorrelatedIncident] = []
        for alert_dict in all_new_alerts:
            inc, is_new = self.correlation_engine.process_alert(alert_dict)
            if inc and inc not in updated_incidents:
                updated_incidents.append(inc)

        # Persist and broadcast
        self._persist_simulation_step(snapshots, all_new_alerts, updated_incidents)
        self._broadcast_simulation_step(snapshots, all_new_alerts, updated_incidents)

        return {
            "scenario": self.active_scenario.value,
            "snapshots": [s.to_dict() for s in snapshots],
            "new_alerts_count": len(all_new_alerts),
            "incidents_count": len(updated_incidents),
            "timestamp": now.isoformat(),
        }

    def _persist_simulation_step(
        self,
        snapshots: List[ServiceMetricsSnapshot],
        alerts: List[dict],
        incidents: List[CorrelatedIncident],
    ) -> None:
        """Persists simulated service statuses, metrics, alerts, and incidents to PostgreSQL."""
        db = self.db_factory()
        try:
            # 1. Update service statuses
            for snap in snapshots:
                db.query(ServiceModel).filter(ServiceModel.name == snap.service_name).update(
                    {"status": snap.status}
                )

                # Persist sample metrics
                if snap.service_id:
                    db.add(MetricModel(
                        service_id=snap.service_id,
                        metric_name="latency",
                        value=round(snap.latency, 2),
                        unit="ms",
                        dimensions={"simulation": True},
                        timestamp=snap.timestamp,
                    ))
                    db.add(MetricModel(
                        service_id=snap.service_id,
                        metric_name="cpu_usage",
                        value=round(snap.cpu, 2),
                        unit="%",
                        dimensions={"simulation": True},
                        timestamp=snap.timestamp,
                    ))

            # 2. Persist new alerts
            for a in alerts:
                alert_model = AlertModel(
                    service_id=a.get("service_id"),
                    service=a["service"],
                    metric=a["metric"],
                    value=a["value"],
                    threshold=a["threshold"],
                    severity=a["severity"],
                    message=a["message"],
                    status="ACTIVE",
                    source="simulation-engine",
                    timestamp=a["timestamp"],
                )
                db.add(alert_model)

            # 3. Persist correlated incidents
            for c_inc in incidents:
                existing = db.query(IncidentModel).filter(IncidentModel.id == c_inc.id).first()
                if existing:
                    existing.title = c_inc.title
                    existing.severity = c_inc.severity
                    existing.status = c_inc.status
                    existing.probable_cause = c_inc.probable_cause
                    existing.root_cause = c_inc.probable_cause
                    existing.correlation_score = c_inc.correlation_score
                    existing.affected_metrics = c_inc.affected_metrics
                    existing.affected_events = c_inc.affected_events
                    existing.updated_at = c_inc.updated_at
                else:
                    new_db_inc = IncidentModel(
                        id=c_inc.id,
                        service_name=c_inc.service,
                        title=c_inc.title,
                        description=f"[DEMO/SIMULATION] Correlated incident across {len(c_inc.affected_metrics)} metrics.",
                        severity=c_inc.severity,
                        status=c_inc.status,
                        probable_cause=c_inc.probable_cause,
                        root_cause=c_inc.probable_cause,
                        correlation_score=c_inc.correlation_score,
                        affected_metrics=c_inc.affected_metrics,
                        affected_events=c_inc.affected_events,
                        created_at=c_inc.created_at,
                        updated_at=c_inc.updated_at,
                    )
                    db.add(new_db_inc)
                    initial_evt = IncidentEventModel(
                        incident_id=c_inc.id,
                        event_type="CORRELATED_INCIDENT_OPENED",
                        description=f"[DEMO/SIMULATION] Correlation Engine merged {len(c_inc.affected_events)} alerts into {c_inc.id}.",
                        actor="EventCorrelationEngine",
                        event_data={"score": c_inc.correlation_score, "metrics": c_inc.affected_metrics},
                        created_at=c_inc.created_at,
                    )
                    db.add(initial_evt)
                    db.commit()

                    # Trigger RCA on new incident
                    try:
                        from aegisops.ai.rca import IncidentInvestigator
                        investigator = IncidentInvestigator()
                        rca_res = investigator.investigate_sync(c_inc.id, db, persist=True)
                        if rca_res:
                            c_inc.probable_cause = rca_res.probable_root_cause
                    except Exception as rca_err:
                        logger.debug("Simulation RCA failed: %s", rca_err)

            db.commit()
        except Exception as err:
            logger.error("Error persisting simulation step: %s", err)
            db.rollback()
        finally:
            db.close()

    def _broadcast_simulation_step(
        self,
        snapshots: List[ServiceMetricsSnapshot],
        alerts: List[dict],
        incidents: List[CorrelatedIncident],
    ) -> None:
        """Broadcasts simulation data over WebSocket."""
        try:
            from backend.core.websocket_manager import ws_manager
            if ws_manager.client_count == 0:
                return

            loop = None
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                pass

            if loop and loop.is_running():
                # Broadcast simulation service statuses
                sim_payload = {
                    "scenario": self.active_scenario.value,
                    "snapshots": [s.to_dict() for s in snapshots],
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                loop.create_task(ws_manager.broadcast_event("SIMULATION_UPDATE", sim_payload))

                for snap in snapshots:
                    loop.create_task(ws_manager.broadcast_service_status(
                        service_name=snap.service_name,
                        status=snap.status,
                        service_id=snap.service_id,
                        details=f"Latency: {snap.latency:.1f}ms, Error Rate: {snap.error_rate:.1f}%",
                    ))

                for a in alerts:
                    loop.create_task(ws_manager.broadcast_alert(a, "NEW_ALERT"))

                for inc in incidents:
                    loop.create_task(ws_manager.broadcast_incident(inc.to_dict(), "INCIDENT_UPDATE"))
        except Exception as err:
            logger.debug("Failed to broadcast simulation update: %s", err)

    async def start(self, interval_seconds: float = 2.0) -> None:
        """Starts asynchronous simulation background loop."""
        if self._running:
            return
        self._running = True
        logger.info("Starting SimulationEngine background runner (interval: %.1fs)...", interval_seconds)

        async def _loop():
            while self._running:
                try:
                    self.step()
                except Exception as err:
                    logger.error("Error during simulation tick: %s", err, exc_info=True)
                await asyncio.sleep(interval_seconds)

        self._task = asyncio.create_task(_loop())

    async def stop(self) -> None:
        """Stops asynchronous simulation background loop."""
        if not self._running:
            return
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("SimulationEngine background loop stopped.")

    def get_status(self) -> Dict[str, Any]:
        """Returns the current simulation status, active scenario, and service snapshots."""
        return {
            "active_scenario": self.active_scenario.value,
            "scenario_start_time": self.scenario_start_time.isoformat(),
            "active_simulated_alerts": len(self._active_simulated_alerts),
            "services": [s.to_dict() for s in self._last_snapshots.values()],
            "is_simulation": True,
            "label": "DEMO/SIMULATION",
        }


# Global singleton instance
simulation_engine = SimulationEngine()
