"""ML Integration Adapter.

This module provides a clean, isolated boundary for connecting Person C's future
Machine Learning API into the POLARIS backend.

Boundary Flow:
    Existing Telemetry
            ↓
    ML Integration Adapter  <-- [This File]
            ↓
    [ PERSON C ML API — NOT CONNECTED YET ]
            ↓
    ML Result
            ↓
    Existing Backend
            ├── Alerts
            ├── Events
            ├── Readiness
            └── Digital Twin state

CRITICAL OPERATIONAL RULES:
- Person C's ML API is NOT available yet.
- Do NOT implement ML models.
- Do NOT invent fake anomaly scores or predictions.
- The system returns "ML INTEGRATION: NOT CONNECTED" when the API is unconfigured or unreachable.
- Network, HTTP, or timeout errors NEVER crash the application or break existing services.
- When Person C provides their API, integration requires ONLY:
    1. Setting ML_API_URL (and optional ML_API_KEY).
    2. Updating `map_telemetry_to_request()` to format features for Person C's schema.
    3. Updating `map_response_to_result()` to parse Person C's inference response.
"""

import logging
from typing import Any
import httpx
from sqlalchemy.orm import Session

from maitri.config import settings
from maitri.schemas.ml import (
    MLAdapterResult,
    MLInferenceRequestPlaceholder,
    MLInferenceResponsePlaceholder,
    MLStatusResponse,
)

logger = logging.getLogger(__name__)

# Official status constant required for unconnected / unavailable states
ML_STATUS_NOT_CONNECTED = "ML INTEGRATION: NOT CONNECTED"
ML_STATUS_CONNECTED = "ML INTEGRATION: CONNECTED"
ML_STATUS_ERROR = "ML INTEGRATION: ERROR"


class MLAdapter:
    """Isolated adapter managing communication with Person C's ML API."""

    def __init__(
        self,
        api_url: str | None = None,
        api_key: str | None = None,
        timeout_seconds: float | None = None,
    ):
        self._api_url = (
            api_url
            if api_url is not None
            else settings.ml_api_url
        )
        self._api_key = (
            api_key
            if api_key is not None
            else settings.ml_api_key
        )
        self._timeout_seconds = (
            timeout_seconds
            if timeout_seconds is not None
            else settings.ml_api_timeout_seconds
        )

    @property
    def api_url(self) -> str:
        return self._api_url or ""

    @property
    def is_configured(self) -> bool:
        """Checks whether an external ML API endpoint has been provided."""
        return bool(self._api_url and self._api_url.strip())

    def get_status(self) -> MLStatusResponse:
        """Returns the current connection state of the ML adapter.

        When Person C's API is unconfigured or offline, explicitly returns
        'ML INTEGRATION: NOT CONNECTED' without generating fake results.
        """
        if not self.is_configured:
            return MLStatusResponse(
                status=ML_STATUS_NOT_CONNECTED,
                connected=False,
                ml_api_url=None,
                message="Person C ML API slot ready for connection (no ML_API_URL configured)",
            )

        # If configured, perform a lightweight check without throwing
        try:
            headers = {}
            if self._api_key:
                headers["Authorization"] = f"Bearer {self._api_key}"
                headers["X-API-Key"] = self._api_key

            with httpx.Client(timeout=self._timeout_seconds) as client:
                resp = client.get(f"{self.api_url.rstrip('/')}/health", headers=headers)
                if resp.status_code == 200:
                    return MLStatusResponse(
                        status=ML_STATUS_CONNECTED,
                        connected=True,
                        ml_api_url=self.api_url,
                        message="Connected to external ML API",
                    )
        except Exception as exc:
            logger.debug("ML API health check failed: %s", exc)

        return MLStatusResponse(
            status=ML_STATUS_NOT_CONNECTED,
            connected=False,
            ml_api_url=self.api_url,
            message=f"ML API configured at {self.api_url} but unreachable ({ML_STATUS_NOT_CONNECTED})",
        )

    # =========================================================================
    # PERSON C CONTRACT MAPPING FUNCTIONS
    # =========================================================================

    def map_telemetry_to_request(
        self,
        station_id: int,
        timestamp: str,
        features: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """FUTURE CONNECTION POINT 1: Request Mapping for Person C.

        Translates raw telemetry and station features into the payload structure
        expected by Person C's external inference service.

        Currently returns the documented placeholder contract.
        """
        placeholder_payload = MLInferenceRequestPlaceholder(
            station_id=station_id,
            timestamp=timestamp,
            features=features,
            metadata=metadata,
        )
        return placeholder_payload.model_dump()

    def map_response_to_result(
        self,
        raw_response: dict[str, Any],
    ) -> MLAdapterResult:
        """FUTURE CONNECTION POINT 2: Response Mapping for Person C.

        Translates the external inference output from Person C into the
        backend's standard MLAdapterResult.

        Currently maps fields from the placeholder contract.
        """
        try:
            placeholder_parsed = MLInferenceResponsePlaceholder(**raw_response)
            return MLAdapterResult(
                status=ML_STATUS_CONNECTED,
                connected=True,
                inference=placeholder_parsed.model_dump(),
                error=None,
            )
        except Exception as exc:
            logger.warning("Failed to parse ML response from Person C: %s", exc)
            return MLAdapterResult(
                status=ML_STATUS_ERROR,
                connected=False,
                inference=None,
                error=f"Invalid response schema: {exc}",
            )

    # =========================================================================
    # INFERENCE DISPATCH INTERFACE
    # =========================================================================

    def send_inference(
        self,
        station_id: int,
        timestamp: str,
        features: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> MLAdapterResult:
        """Dispatches telemetry features to Person C's ML API and returns the result.

        If the ML API is unconfigured or unreachable:
        - NEVER throws an exception.
        - NEVER fabricates fake anomaly scores or predictions.
        - Returns MLAdapterResult with status="ML INTEGRATION: NOT CONNECTED".
        """
        if not self.is_configured:
            return MLAdapterResult(
                status=ML_STATUS_NOT_CONNECTED,
                connected=False,
                inference=None,
                error="ML_API_URL not configured",
            )

        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
            headers["X-API-Key"] = self._api_key

        payload = self.map_telemetry_to_request(
            station_id=station_id,
            timestamp=timestamp,
            features=features,
            metadata=metadata,
        )

        try:
            inference_url = f"{self.api_url.rstrip('/')}/predict"
            with httpx.Client(timeout=self._timeout_seconds) as client:
                response = client.post(inference_url, json=payload, headers=headers)
                if response.status_code == 200:
                    return self.map_response_to_result(response.json())
                else:
                    return MLAdapterResult(
                        status=ML_STATUS_NOT_CONNECTED,
                        connected=False,
                        inference=None,
                        error=f"ML API HTTP {response.status_code}: {response.text[:200]}",
                    )
        except httpx.TimeoutException:
            logger.warning("ML API call timed out after %ss", self._timeout_seconds)
            return MLAdapterResult(
                status=ML_STATUS_NOT_CONNECTED,
                connected=False,
                inference=None,
                error="ML API request timed out",
            )
        except Exception as exc:
            logger.warning("ML API request failed: %s", exc)
            return MLAdapterResult(
                status=ML_STATUS_NOT_CONNECTED,
                connected=False,
                inference=None,
                error=f"Connection failure: {exc}",
            )

    # =========================================================================
    # BACKEND ROUTING BOUNDARY (Alerts, Events, Readiness, Digital Twin)
    # =========================================================================

    def dispatch_ml_result(
        self,
        db: Session,
        result: MLAdapterResult,
    ) -> None:
        """FUTURE CONNECTION POINT 3: Backend Result Ingestion.

        When Person C's API is connected and returns real predictions, this method
        serves as the isolated boundary to forward genuine ML findings to:
        - Alerts (e.g. triggering predictive failure alerts)
        - Events (e.g. logging ML anomaly detection events)
        - Readiness (e.g. updating mission readiness confidence)
        - Digital Twin (e.g. coloring stressed twin components)

        SAFETY GUARANTEE:
        If result is not connected or contains no inference, this method safely
        no-ops, guaranteeing that lack of ML never impairs existing backend operations.
        """
        if not result.connected or not result.inference:
            # Safely no-op: zero interference with existing telemetry or simulator
            return

        # When Person C connects, real distribution logic will be placed here:
        # e.g.:
        # if result.inference.get("anomaly_detected") and result.inference.get("anomaly_score", 0) > 0.8:
        #     create_alert(...)


# Global default instance
ml_adapter = MLAdapter()
