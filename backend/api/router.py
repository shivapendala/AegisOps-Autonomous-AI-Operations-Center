"""
Main API Router Configuration.
Exposes REST endpoints under the /api namespace (and /api/v1 alias).
Provides:
- GET /api/health
- GET /api/services
- GET /api/metrics
- GET /api/alerts
- GET /api/incidents
"""

from fastapi import APIRouter

from backend.api.routes.health import router as health_router
from backend.api.routes.services import router as services_router
from backend.api.routes.metrics import router as metrics_router
from backend.api.routes.alerts import router as alerts_router
from backend.api.routes.incidents import router as incidents_router
from backend.api.routes.ai import router as ai_router
from backend.api.routes.simulation import router as simulation_router

# Primary router mounted at /api
api_router = APIRouter(prefix="/api")
api_router.include_router(health_router)
api_router.include_router(services_router)
api_router.include_router(metrics_router)
api_router.include_router(alerts_router)
api_router.include_router(incidents_router)
api_router.include_router(ai_router)
api_router.include_router(simulation_router)

# Compatibility alias router mounted at /api/v1
api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(health_router)
api_v1_router.include_router(services_router)
api_v1_router.include_router(metrics_router)
api_v1_router.include_router(alerts_router)
api_v1_router.include_router(incidents_router)
api_v1_router.include_router(ai_router)
api_v1_router.include_router(simulation_router)
