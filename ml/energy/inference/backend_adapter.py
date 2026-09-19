"""
Energy ML Backend Integration Adapter (Polarix SIH26060).

Acts as a clean, decoupled boundary adapter between Person A's backend telemetry
ingestion layer and Person C's EnergyMLService:
1. Ingests canonical raw telemetry records (dict or DataFrame).
2. Validates physical bounds, data types, and strictly enforces station IDs (MTR/BRT only).
3. Rejects 'BHR' with an explicit actionable error (no silent aliasing).
4. Maintains an isolated 24-hour contiguous hourly sliding buffer per station.
5. Rejects out-of-order and duplicate timestamps; detects hourly timeline gaps.
6. Returns INSUFFICIENT_HISTORY when < 24 contiguous hours exist.
7. Executes EnergyMLService unified multi-horizon forecasting & deficit-risk prediction when 24 hours exist.
8. Returns the canonical unified output contract without modifying underlying ML models.
"""

from __future__ import annotations

import json
import math
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import numpy as np
import pandas as pd

from ml.energy.inference.energy_ml_service import EnergyMLService, UnifiedEnergyPrediction
from ml.energy.risk.features import (
    PHYSICAL_BOUNDS,
    REQUIRED_RAW_COLUMNS,
    validate_risk_telemetry,
)


def parse_utc_timestamp(ts: Union[str, datetime, pd.Timestamp]) -> datetime:
    """Parse timestamp into timezone-aware UTC datetime."""
    if isinstance(ts, datetime):
        if ts.tzinfo is None:
            return ts.replace(tzinfo=timezone.utc)
        return ts.astimezone(timezone.utc)
    elif isinstance(ts, pd.Timestamp):
        if ts.tzinfo is None:
            return ts.tz_localize("UTC").to_pydatetime()
        return ts.tz_convert("UTC").to_pydatetime()
    elif isinstance(ts, str):
        # Handle ISO-8601 string
        clean_str = ts.strip().replace("Z", "+00:00")
        dt = datetime.fromisoformat(clean_str)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    else:
        raise ValueError(f"Unsupported timestamp type: {type(ts)} for value '{ts}'")


@dataclass
class AdapterResponse:
    """Standardized response container for backend adapter ingestion and prediction."""

    status: str  # "PREDICTION_AVAILABLE" or "INSUFFICIENT_HISTORY"
    station_id: str
    latest_timestamp: Optional[str]
    available_history: int
    required_history: int = 24
    prediction: Optional[Dict[str, Any]] = None
    message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert response to standard nested dictionary."""
        return asdict(self)

    def to_json(self, indent: Optional[int] = None) -> str:
        """Serialize response directly to standard JSON."""
        return json.dumps(self.to_dict(), indent=indent)


class EnergyMLBackendAdapter:
    """
    ML-side boundary adapter for Person A Backend Ingestion.

    Maintains isolated 24-hour sliding ring buffers for MTR and BRT stations,
    validates canonical telemetry, verifies hourly contiguous continuity,
    and invokes EnergyMLService when ready.
    """

    SUPPORTED_STATIONS = {"MTR", "BRT"}
    REQUIRED_LOOKBACK_HOURS = 24
    EXPECTED_CADENCE_SECONDS = 3600  # 1 hour

    def __init__(
        self,
        energy_service: Optional[EnergyMLService] = None,
        model_dir: Union[str, Path] = Path("ml/energy/models"),
    ):
        self.energy_service = energy_service or EnergyMLService(model_dir=model_dir)
        # Separate isolated buffers for each station
        self._buffers: Dict[str, List[Dict[str, Any]]] = {
            "MTR": [],
            "BRT": [],
        }

    def reset(self, station_id: Optional[str] = None) -> None:
        """Reset historical buffer for a specific station or all stations."""
        if station_id:
            if station_id in self._buffers:
                self._buffers[station_id].clear()
        else:
            for s in self._buffers:
                self._buffers[s].clear()

    def get_history(self, station_id: str) -> List[Dict[str, Any]]:
        """Retrieve copy of current sliding buffer for a station."""
        if station_id not in self.SUPPORTED_STATIONS:
            raise ValueError(f"Unsupported station_id '{station_id}'. Expected {self.SUPPORTED_STATIONS}")
        return [dict(r) for r in self._buffers[station_id]]

    def _validate_telemetry_dict(self, telemetry: Dict[str, Any]) -> None:
        """Validate raw telemetry dictionary against schema and physical invariants."""
        if not isinstance(telemetry, dict):
            raise TypeError(f"Telemetry payload must be a dictionary, got {type(telemetry)}")

        station_id = telemetry.get("station_id")
        if station_id == "BHR":
            raise ValueError(
                "Invalid station_id 'BHR'. Person A backend must normalize 'BHR' to canonical 'BRT' "
                "before routing to EnergyMLBackendAdapter."
            )
        if station_id not in self.SUPPORTED_STATIONS:
            raise ValueError(
                f"Invalid station_id '{station_id}'. Expected one of {sorted(self.SUPPORTED_STATIONS)}."
            )

        # Validate required fields
        missing_fields = [f for f in REQUIRED_RAW_COLUMNS if f not in telemetry]
        if missing_fields:
            raise KeyError(f"Telemetry missing required canonical fields: {missing_fields}")

        # Check timestamp
        ts_val = telemetry["timestamp"]
        try:
            parse_utc_timestamp(ts_val)
        except Exception as e:
            raise ValueError(f"Invalid timestamp format '{ts_val}': {e}") from e

        # Validate numeric types, NaN, Inf, and physical bounds
        for col, (low, high) in PHYSICAL_BOUNDS.items():
            if col in telemetry:
                val = telemetry[col]
                if val is None or not isinstance(val, (int, float, np.number)):
                    raise ValueError(f"Field '{col}' must be a valid number, got {val}")
                val_float = float(val)
                if not math.isfinite(val_float):
                    raise ValueError(f"Field '{col}' contains NaN or infinite value: {val}")
                if low is not None and val_float < low:
                    raise ValueError(
                        f"Field '{col}' value {val_float} is below physical lower bound {low}"
                    )
                if high is not None and val_float > high:
                    raise ValueError(
                        f"Field '{col}' value {val_float} is above physical upper bound {high}"
                    )

    def _get_contiguous_hourly_suffix(self, buffer: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Find the longest contiguous hourly sequence ending at the latest record in the buffer.
        If a gap (> 1 hour) occurs, returns only records after the gap.
        """
        if not buffer:
            return []

        suffix = [buffer[-1]]
        for i in range(len(buffer) - 1, 0, -1):
            curr_dt = parse_utc_timestamp(buffer[i]["timestamp"])
            prev_dt = parse_utc_timestamp(buffer[i - 1]["timestamp"])
            delta_sec = (curr_dt - prev_dt).total_seconds()

            if math.isclose(delta_sec, self.EXPECTED_CADENCE_SECONDS, abs_tol=1.0):
                suffix.insert(0, buffer[i - 1])
            else:
                # Timeline gap detected
                break

        return suffix

    def ingest(self, telemetry: Dict[str, Any]) -> AdapterResponse:
        """
        Ingest a single canonical telemetry record into the station's sliding buffer.

        Validates:
        - Physical bounds and required schema.
        - Strict chronological ordering (no out-of-order records).
        - Rejects duplicate timestamps.

        Returns:
            AdapterResponse indicating current buffer status.
        """
        self._validate_telemetry_dict(telemetry)

        station_id = str(telemetry["station_id"])
        record_ts = parse_utc_timestamp(telemetry["timestamp"])
        iso_ts = record_ts.strftime("%Y-%m-%dT%H:%M:%SZ")

        # Copy telemetry record and ensure standardized timestamp string
        clean_record = dict(telemetry)
        clean_record["timestamp"] = iso_ts

        station_buf = self._buffers[station_id]

        # Chronological ordering and duplicate check
        if station_buf:
            last_ts = parse_utc_timestamp(station_buf[-1]["timestamp"])
            if record_ts < last_ts:
                raise ValueError(
                    f"Out-of-order telemetry for station {station_id}: incoming timestamp "
                    f"{iso_ts} is earlier than latest buffered timestamp {station_buf[-1]['timestamp']}."
                )
            if record_ts == last_ts:
                raise ValueError(
                    f"Duplicate telemetry timestamp for station {station_id}: {iso_ts} is already buffered."
                )

        # Append to buffer
        station_buf.append(clean_record)

        # Maintain maximum buffer length of 24
        if len(station_buf) > self.REQUIRED_LOOKBACK_HOURS:
            station_buf.pop(0)

        # Check contiguous history available
        contiguous_suffix = self._get_contiguous_hourly_suffix(station_buf)
        avail_len = len(contiguous_suffix)

        if avail_len < self.REQUIRED_LOOKBACK_HOURS:
            gap_msg = (
                f"Buffer has {len(station_buf)} records, but only {avail_len} contiguous hourly records due to timeline gap."
                if avail_len < len(station_buf)
                else f"Buffering in progress: {avail_len}/{self.REQUIRED_LOOKBACK_HOURS} contiguous hourly records."
            )
            return AdapterResponse(
                status="INSUFFICIENT_HISTORY",
                station_id=station_id,
                latest_timestamp=iso_ts,
                available_history=avail_len,
                required_history=self.REQUIRED_LOOKBACK_HOURS,
                prediction=None,
                message=gap_msg,
            )

        return AdapterResponse(
            status="PREDICTION_AVAILABLE",
            station_id=station_id,
            latest_timestamp=iso_ts,
            available_history=avail_len,
            required_history=self.REQUIRED_LOOKBACK_HOURS,
            prediction=None,
            message="24 contiguous hourly records buffered and ready for prediction.",
        )

    def predict(self, station_id: str) -> AdapterResponse:
        """
        Execute unified multi-horizon energy prediction for the specified station
        using the current 24-hour contiguous historical window.
        """
        if station_id not in self.SUPPORTED_STATIONS:
            if station_id == "BHR":
                raise ValueError(
                    "Invalid station_id 'BHR'. Person A backend must normalize 'BHR' to canonical 'BRT'."
                )
            raise ValueError(f"Invalid station_id '{station_id}'. Expected {sorted(self.SUPPORTED_STATIONS)}.")

        station_buf = self._buffers[station_id]
        if not station_buf:
            return AdapterResponse(
                status="INSUFFICIENT_HISTORY",
                station_id=station_id,
                latest_timestamp=None,
                available_history=0,
                required_history=self.REQUIRED_LOOKBACK_HOURS,
                prediction=None,
                message="No telemetry has been ingested for this station.",
            )

        latest_ts = station_buf[-1]["timestamp"]
        contiguous_suffix = self._get_contiguous_hourly_suffix(station_buf)
        avail_len = len(contiguous_suffix)

        if avail_len < self.REQUIRED_LOOKBACK_HOURS:
            return AdapterResponse(
                status="INSUFFICIENT_HISTORY",
                station_id=station_id,
                latest_timestamp=latest_ts,
                available_history=avail_len,
                required_history=self.REQUIRED_LOOKBACK_HOURS,
                prediction=None,
                message=(
                    f"Insufficient contiguous history: {avail_len}/{self.REQUIRED_LOOKBACK_HOURS} hours available. "
                    "EnergyMLService neural forecasting requires 24 contiguous hourly records."
                ),
            )

        # Convert the 24 contiguous records into a DataFrame
        window_df = pd.DataFrame(contiguous_suffix)

        # Execute unified prediction via EnergyMLService
        unified_pred: UnifiedEnergyPrediction = self.energy_service.predict(window_df, validate=False)

        return AdapterResponse(
            status="PREDICTION_AVAILABLE",
            station_id=station_id,
            latest_timestamp=latest_ts,
            available_history=self.REQUIRED_LOOKBACK_HOURS,
            required_history=self.REQUIRED_LOOKBACK_HOURS,
            prediction=unified_pred.to_dict(),
            message="Unified energy prediction successfully generated.",
        )

    def ingest_and_predict(self, telemetry: Dict[str, Any]) -> AdapterResponse:
        """
        Ingest incoming telemetry record and immediately attempt unified prediction.

        Convenience method for real-time streaming backend pipelines:
        - If < 24 contiguous hours: returns status INSUFFICIENT_HISTORY.
        - If 24 contiguous hours: returns status PREDICTION_AVAILABLE with prediction payload.
        """
        ingest_res = self.ingest(telemetry)
        if ingest_res.status == "INSUFFICIENT_HISTORY":
            return ingest_res

        return self.predict(ingest_res.station_id)
