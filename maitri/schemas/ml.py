"""ML Integration Schemas.

Placeholder request and response contracts for Person C's future Machine Learning API.
"""

from typing import Any
from pydantic import BaseModel, Field


class MLStatusResponse(BaseModel):
    status: str = Field(
        default="ML INTEGRATION: NOT CONNECTED",
        description="Integration status message",
    )
    connected: bool = Field(
        default=False,
        description="True if external ML API is reachable and active",
    )
    ml_api_url: str | None = Field(
        default=None,
        description="Configured ML API endpoint URL (empty if unconfigured)",
    )
    message: str = Field(
        default="Person C ML API slot ready for connection",
        description="Operational context",
    )


class MLInferenceRequestPlaceholder(BaseModel):
    """Documented contract placeholder for sending telemetry features to Person C."""

    station_id: int = Field(
        ..., description="Target station ID (e.g. 1 for Maitri, 2 for Bharati)"
    )
    timestamp: str = Field(
        ..., description="Observation timestamp in ISO8601 UTC format"
    )
    features: dict[str, float | int | str | None] = Field(
        default_factory=dict,
        description="Normalized telemetry features (e.g. ambient_temp, wind_speed, generator_output_kw, vibration_hz, fuel_level_pct)",
    )
    metadata: dict[str, Any] | None = Field(
        default=None,
        description="Optional operational context such as operational mode or active alerts",
    )


class MLInferenceResponsePlaceholder(BaseModel):
    """Documented contract placeholder for receiving inference results from Person C."""

    model_version: str | None = Field(
        default=None, description="Inference model version tag (e.g. 'v1.0.0')"
    )
    anomaly_detected: bool | None = Field(
        default=None, description="Whether the ML model detected an anomaly"
    )
    anomaly_score: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Confidence score [0.0 - 1.0] indicating anomaly likelihood",
    )
    predicted_component: str | None = Field(
        default=None,
        description="Subsystem or sensor predicted to experience failure",
    )
    confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Model confidence level",
    )
    recommendation: str | None = Field(
        default=None,
        description="Prescriptive action recommended by the ML model",
    )


class MLAdapterResult(BaseModel):
    """Clean result envelope returned by the ML integration adapter."""

    status: str = Field(
        default="ML INTEGRATION: NOT CONNECTED",
        description="Integration status",
    )
    connected: bool = Field(
        default=False,
        description="Whether inference succeeded with the external ML API",
    )
    inference: dict[str, Any] | None = Field(
        default=None,
        description="Raw or structured inference result from Person C (None when not connected)",
    )
    error: str | None = Field(
        default=None,
        description="Error description if an attempt failed gracefully",
    )
