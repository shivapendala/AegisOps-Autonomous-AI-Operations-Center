"""
Health Check and System Readiness Endpoint.
Reports operational status, versioning, database connectivity, and AI engine state.
"""

from datetime import datetime, timezone
import time
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from backend.config import settings
from backend.schemas.health import HealthResponse
from database.session import get_sync_db

router = APIRouter(prefix="/health", tags=["Health"])

START_TIME = time.time()


@router.get("", response_model=HealthResponse, summary="System Health & Readiness Probe")
def get_health(db: Session = Depends(get_sync_db)):
    """Validates backend service readiness, database connection, and runtime status."""
    uptime_seconds = round(time.time() - START_TIME, 2)
    db_status = "healthy"
    tables_ready = True
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        db_status = f"unhealthy: {str(exc)}"
        tables_ready = False

    return HealthResponse(
        status="healthy" if db_status == "healthy" else "degraded",
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
        uptime_seconds=uptime_seconds,
        database=db_status,
        tables_ready=tables_ready,
        ai_engine={
            "provider": settings.LLM_PROVIDER,
            "anomaly_detector": "scikit-learn-isolation-forest",
        },
        timestamp=datetime.now(timezone.utc),
    )
