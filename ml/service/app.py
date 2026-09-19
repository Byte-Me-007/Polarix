"""
Polarix ML Microservice Application (SIH26060 - Person C).

Independent FastAPI service exposing production Sensor ML and Energy ML inference boundaries.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ml.service.routes.health import router as health_router
from ml.service.routes.energy import router as energy_router, get_energy_adapter
from ml.service.routes.sensor import router as sensor_router, get_maitri_service, get_bharati_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Warm up and verify ML models on startup."""
    # Pre-initialize singletons to ensure fast first-request response
    get_energy_adapter()
    get_maitri_service()
    get_bharati_service()
    yield


def create_app() -> FastAPI:
    """Create and configure the Polarix ML FastAPI application."""
    app = FastAPI(
        title="Polarix ML Inference Service",
        description="Autonomous Sensor ML Anomaly Detection & Energy Forecasting Microservice (SIH26060).",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routes
    app.include_router(health_router)
    app.include_router(energy_router)
    app.include_router(sensor_router)

    return app


app = create_app()
