"""
AegisOps - Autonomous AI Operations Center Backend.
FastAPI main application entrypoint configuring CORS, logging, database initialization,
centralized error handling, and REST/WebSocket operational endpoints.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.router import api_router, api_v1_router
from backend.api.routes.ws import router as ws_router
from backend.config import settings
from backend.core.exceptions import register_exception_handlers
from backend.core.logger import setup_logging
from database.init_db import setup_and_seed

from monitoring.service import MonitoringService
from monitoring.simulation import simulation_engine

logger = setup_logging(settings.LOG_LEVEL)

# Global monitoring service singleton
monitoring_service = MonitoringService(interval_seconds=2.0)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown routines."""
    logger.info("Starting AegisOps - Autonomous AI Operations Center...")
    try:
        setup_and_seed()
        logger.info("Database schema synchronized and seed records verified.")
    except Exception as exc:
        logger.error("Database initialization encountered an error: %s", exc, exc_info=True)

    # Launch real-time monitoring background service
    try:
        await monitoring_service.start()
        logger.info("AegisOps Real-time Monitoring Engine started (2.0s interval).")
    except Exception as exc:
        logger.error("Failed to start monitoring background engine: %s", exc)

    # Launch simulation engine background runner
    try:
        await simulation_engine.start(interval_seconds=2.0)
        logger.info("AegisOps Realistic Simulation Engine started (2.0s interval).")
    except Exception as exc:
        logger.error("Failed to start simulation engine: %s", exc)

    logger.info("AegisOps Backend is ready on http://%s:%s", settings.HOST, settings.PORT)
    yield
    logger.info("Shutting down AegisOps Backend gracefully...")
    await simulation_engine.stop()
    await monitoring_service.stop()


def create_app() -> FastAPI:
    """FastAPI application factory."""
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Autonomous AI Operations Center: Real-time telemetry, scikit-learn anomaly detection, and pluggable LLM root cause analysis.",
        lifespan=lifespan,
    )

    # CORS Configuration
    cors_origins = (
        settings.CORS_ORIGINS
        if isinstance(settings.CORS_ORIGINS, list)
        else [settings.CORS_ORIGINS]
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register Centralized Domain Exception Handlers
    register_exception_handlers(app)

    # Mount REST API Routers
    app.include_router(api_router)
    app.include_router(api_v1_router)

    # Mount WebSocket Router
    app.include_router(ws_router)

    @app.get("/", tags=["Root"])
    def root():
        return {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "status": "operational",
            "docs": "/docs",
            "endpoints": {
                "health": "/api/health",
                "services": "/api/services",
                "metrics": "/api/metrics",
                "alerts": "/api/alerts",
                "incidents": "/api/incidents",
                "telemetry_ws": "/ws/telemetry",
            },
        }

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
