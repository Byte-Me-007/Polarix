"""
Polarix Maitri ML Backend Integration Contract (SIH26060 - Person C).

Defines the canonical JSON schemas, examples, and dependency-free conversion adapters
for Person A's backend to seamlessly stream telemetry into and receive structured anomaly
detection responses from Person C's MaitriMLService.

Architecture:
Backend JSON Ingestion
        ↓
  adapt_backend_input() → TelemetryInput (Validated)
        ↓
  MaitriMLService.process_telemetry()
        ↓
  TelemetryInferenceOutput
        ↓
  adapt_backend_output() → Backend JSON Response
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Union

# Ensure repository root is on sys.path
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from ml.inference.inference_contract import (
    DEFAULT_MODEL_VERSION,
    SUPPORTED_SENSORS,
    SUPPORTED_STATIONS,
    VALID_ANOMALY_TYPES,
    VALID_QUALITIES,
    VALID_STATUSES,
    DuplicateTelemetryError,
    InvalidContractError,
    StaleTelemetryError,
    TelemetryInferenceOutput,
    TelemetryInput,
    UnsupportedSensorError,
    UnsupportedStationError,
    parse_iso_timestamp,
)
from ml.inference.maitri_ml_service import MaitriMLService

# -----------------------------------------------------------------------------
# Canonical Backend-Facing JSON Schema Examples
# -----------------------------------------------------------------------------

EXAMPLE_BACKEND_TELEMETRY_INPUT: Dict[str, Any] = {
    "station_id": "MTR",
    "sensor_id": "TEMP_001",
    "timestamp": "2026-09-17T10:30:00Z",
    "value": -34.5,
    "unit": "C",
    "quality": "GOOD",
    "source": "SIMULATOR",
}

EXAMPLE_BACKEND_INFERENCE_OUTPUT_NORMAL: Dict[str, Any] = {
    "station_id": "MTR",
    "sensor_id": "TEMP_001",
    "timestamp": "2026-09-17T10:30:00Z",
    "value": -34.5,
    "unit": "C",
    "quality": "GOOD",
    "source": "SIMULATOR",
    "anomaly_score": 0.002824,
    "anomaly_status": "NORMAL",
    "anomaly_type": "NORMAL",
    "model_version": "lstm-ae-v1",
}

EXAMPLE_BACKEND_INFERENCE_OUTPUT_ANOMALY: Dict[str, Any] = {
    "station_id": "MTR",
    "sensor_id": "TEMP_001",
    "timestamp": "2026-09-17T10:30:00Z",
    "value": 25.0,
    "unit": "C",
    "quality": "GOOD",
    "source": "SIMULATOR",
    "anomaly_score": 4.945585,
    "anomaly_status": "ANOMALY",
    "anomaly_type": "SPIKE",
    "model_version": "lstm-ae-v1",
}


# -----------------------------------------------------------------------------
# Input & Output Adapters
# -----------------------------------------------------------------------------

def adapt_backend_input(payload: Union[Dict[str, Any], str]) -> TelemetryInput:
    """
    Validate and adapt a backend-provided telemetry JSON string or dictionary into
    a typed TelemetryInput contract instance.

    Parameters:
    -----------
    payload : Union[Dict[str, Any], str]
        Raw backend payload dictionary or JSON string.

    Returns:
    --------
    TelemetryInput:
        Validated typed telemetry input.

    Raises:
    -------
    InvalidContractError: If payload is malformed or violates schema constraints.
    UnsupportedStationError: If station_id is not 'MTR'.
    UnsupportedSensorError: If sensor_id is not among supported Maitri sensors.
    """
    if isinstance(payload, str):
        return TelemetryInput.from_json(payload)
    elif isinstance(payload, dict):
        return TelemetryInput.from_dict(payload)
    else:
        raise InvalidContractError(
            f"Expected backend payload as dict or JSON string, got {type(payload).__name__}"
        )


def adapt_backend_output(output: Union[TelemetryInferenceOutput, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Serialize a TelemetryInferenceOutput into a standardized, JSON-compatible dictionary
    ready for backend response emission or message broadcasting.

    Guarantees:
    - All floating-point fields are strictly finite (no NaN, Infinity).
    - Stable, deterministic dictionary keys.
    - Full telemetry metadata preservation.

    Parameters:
    -----------
    output : Union[TelemetryInferenceOutput, Dict[str, Any]]
        Inference output contract object or dictionary.

    Returns:
    --------
    Dict[str, Any]:
        Standardized, JSON-serializable dictionary.
    """
    if isinstance(output, TelemetryInferenceOutput):
        out_dict = output.to_dict()
    elif isinstance(output, dict):
        # Validate through contract instantiation to ensure integrity
        validated = TelemetryInferenceOutput.from_dict(output)
        out_dict = validated.to_dict()
    else:
        raise InvalidContractError(
            f"Expected TelemetryInferenceOutput or dict, got {type(output).__name__}"
        )

    # Convert any non-finite numeric values (such as NaN/Inf in raw value) to None for clean JSON compliance
    clean_val = out_dict.get("value")
    if clean_val is not None:
        if isinstance(clean_val, (int, float)) and not math.isfinite(clean_val):
            clean_val = None

    score_val = out_dict.get("anomaly_score")
    if score_val is not None:
        if isinstance(score_val, (int, float)) and not math.isfinite(score_val):
            score_val = None
        else:
            score_val = round(float(score_val), 6)

    return {
        "station_id": out_dict["station_id"],
        "sensor_id": out_dict["sensor_id"],
        "timestamp": out_dict["timestamp"],
        "value": clean_val,
        "unit": out_dict["unit"],
        "quality": out_dict["quality"],
        "source": out_dict["source"],
        "anomaly_score": score_val,
        "anomaly_status": out_dict["anomaly_status"],
        "anomaly_type": out_dict["anomaly_type"],
        "model_version": out_dict["model_version"],
    }


def process_backend_payload(
    service: MaitriMLService,
    payload: Union[Dict[str, Any], str],
) -> Dict[str, Any]:
    """
    End-to-end convenience pipeline for backend integration:
    Backend JSON Dict/String → TelemetryInput → MaitriMLService → TelemetryInferenceOutput → Backend JSON Dict.

    Parameters:
    -----------
    service : MaitriMLService
        Initialized Maitri ML service instance.
    payload : Union[Dict[str, Any], str]
        Raw backend telemetry dictionary or JSON string.

    Returns:
    --------
    Dict[str, Any]:
        Standardized inference result dictionary ready for REST/WebSocket/MQTT emission.
    """
    telemetry_input = adapt_backend_input(payload)
    inference_output = service.process_telemetry(telemetry_input)
    return adapt_backend_output(inference_output)
