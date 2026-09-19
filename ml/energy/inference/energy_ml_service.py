"""
Unified Energy ML Service for Polarix Microgrid (SIH26060).

Orchestrates:
1. Multi-horizon energy demand & battery SoC forecasting via PyTorch EnergyLSTM baseline.
2. 1-hour ahead binary energy deficit-risk early warning via HistGradientBoosting risk classifier.
3. Unified, backend-consumable operational prediction contract with strict provenance disclaimers.
"""

from __future__ import annotations

import json
import math
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import numpy as np
import pandas as pd

from ml.energy.inference.energy_forecaster import EnergyForecaster, EnergyPrediction
from ml.energy.risk.features import validate_risk_telemetry
from ml.energy.risk.inference import DeficitRiskForecaster, DeficitRiskPrediction


@dataclass
class EnergyForecasts:
    """Multi-horizon electrical and battery forecast outputs from EnergyLSTM."""

    power_demand_1h_kw: float
    battery_soc_1h_percent: float
    energy_demand_6h_kwh: float
    energy_demand_24h_kwh: float


@dataclass
class DeficitRiskOutput:
    """1-hour ahead binary deficit-risk probability and decision."""

    probability: float
    decision: bool
    threshold: float


@dataclass
class ProvenanceMetadata:
    """Provenance, status, and empirical calibration references."""

    source: str = "SYNTHETIC_POLARIX_OPERATIONAL_DATA"
    model_status: str = "CANDIDATE"
    calibration_reference: str = (
        "Australian Antarctic Data Centre (AADC CC BY 4.0) & NCPOR Meteorological Archives"
    )
    disclaimer: str = (
        "Validated on synthetic Polarix operational microgrid telemetry. "
        "Not validated on real classified station SCADA telemetry."
    )


@dataclass
class UnifiedEnergyPrediction:
    """Canonical unified prediction container for Person A backend consumption."""

    station_id: str
    timestamp: str
    contract_version: str
    model_version: str
    forecast_model_version: str
    risk_model_version: str
    forecasts: EnergyForecasts
    deficit_risk: DeficitRiskOutput
    provenance: ProvenanceMetadata = field(default_factory=ProvenanceMetadata)

    def to_dict(self) -> Dict[str, Any]:
        """Convert dataclass to standard nested Python dictionary."""
        return asdict(self)

    def to_json(self, indent: Optional[int] = None) -> str:
        """Serialize prediction directly to standard JSON string."""
        return json.dumps(self.to_dict(), indent=indent)


class EnergyMLService:
    """
    Unified Orchestrator Service for Polarix Energy Forecasting & Deficit-Risk Prediction.

    Acts as an adapter over EnergyForecaster and DeficitRiskForecaster without altering
    their internal feature logic, weights, or thresholds.
    """

    CONTRACT_VERSION: str = "energy-ml-contract-v1"
    UNIFIED_MODEL_VERSION: str = "energy-ml-v1-candidate"
    REQUIRED_LOOKBACK_HOURS: int = 24

    def __init__(
        self,
        model_dir: Union[str, Path] = Path("ml/energy/models"),
        forecaster: Optional[EnergyForecaster] = None,
        risk_forecaster: Optional[DeficitRiskForecaster] = None,
    ):
        self.model_dir = Path(model_dir)
        self.forecaster = forecaster or EnergyForecaster(model_dir=self.model_dir)
        self.risk_forecaster = risk_forecaster or DeficitRiskForecaster(model_dir=self.model_dir)

    def predict(self, window_df: pd.DataFrame, validate: bool = True) -> UnifiedEnergyPrediction:
        """
        Generate unified multi-horizon energy forecasts and deficit-risk classification
        for the latest observation timestamp t given >= 24 hours of causal telemetry.

        Parameters:
            window_df: Historical telemetry window (must contain at least 24 contiguous hourly records).
            validate: Whether to execute physical bounds and schema validation.

        Returns:
            UnifiedEnergyPrediction containing disaggregated forecasts, deficit risk, and provenance metadata.
        """
        if len(window_df) < self.REQUIRED_LOOKBACK_HOURS:
            raise ValueError(
                f"Insufficient historical telemetry: provided {len(window_df)} records, "
                f"but EnergyMLService requires at least {self.REQUIRED_LOOKBACK_HOURS} hours "
                "for multi-horizon neural forecasting and causal rolling risk assessment."
            )

        if validate:
            validate_risk_telemetry(window_df)

        # 1. Execute Energy LSTM Forecasting
        forecast_res: EnergyPrediction = self.forecaster.predict_window(window_df)

        # 2. Execute Deficit-Risk Classification
        risk_res: DeficitRiskPrediction = self.risk_forecaster.predict_window(window_df, validate=False)

        # 3. Output Validation & Consistency Checks
        station_id = str(forecast_res.station_id)
        if station_id not in {"MTR", "BRT"}:
            raise ValueError(f"Invalid station_id in model output: {station_id}")

        timestamp = str(forecast_res.prediction_timestamp)

        # Validate numerical finiteness
        for val_name, val in [
            ("power_demand_1h_kw", forecast_res.target_power_demand_1h_kw),
            ("battery_soc_1h_percent", forecast_res.target_battery_soc_1h_percent),
            ("energy_demand_6h_kwh", forecast_res.target_energy_demand_6h_kwh),
            ("energy_demand_24h_kwh", forecast_res.target_energy_demand_24h_kwh),
            ("deficit_risk_probability", risk_res.deficit_risk_probability),
        ]:
            if not math.isfinite(val):
                raise ValueError(f"Model generated non-finite value for '{val_name}': {val}")

        if not (0.0 <= risk_res.deficit_risk_probability <= 1.0):
            raise ValueError(
                f"Deficit risk probability out of bounds [0, 1]: {risk_res.deficit_risk_probability}"
            )

        forecasts_obj = EnergyForecasts(
            power_demand_1h_kw=float(forecast_res.target_power_demand_1h_kw),
            battery_soc_1h_percent=float(forecast_res.target_battery_soc_1h_percent),
            energy_demand_6h_kwh=float(forecast_res.target_energy_demand_6h_kwh),
            energy_demand_24h_kwh=float(forecast_res.target_energy_demand_24h_kwh),
        )

        deficit_risk_obj = DeficitRiskOutput(
            probability=float(risk_res.deficit_risk_probability),
            decision=bool(risk_res.deficit_risk),
            threshold=float(risk_res.threshold),
        )

        return UnifiedEnergyPrediction(
            station_id=station_id,
            timestamp=timestamp,
            contract_version=self.CONTRACT_VERSION,
            model_version=self.UNIFIED_MODEL_VERSION,
            forecast_model_version=forecast_res.model_version,
            risk_model_version=risk_res.model_version,
            forecasts=forecasts_obj,
            deficit_risk=deficit_risk_obj,
            provenance=ProvenanceMetadata(),
        )

    def predict_records(self, records: List[Dict[str, Any]], validate: bool = True) -> UnifiedEnergyPrediction:
        """
        Generate unified prediction from a list of telemetry record dictionaries.
        """
        df = pd.DataFrame(records)
        return self.predict(df, validate=validate)

    def predict_dataframe(self, df: pd.DataFrame, validate: bool = True) -> pd.DataFrame:
        """
        Generate continuous sliding-window predictions over an entire station timeline.
        Merges both LSTM regression forecasts and Deficit Risk predictions.
        """
        if len(df) < self.REQUIRED_LOOKBACK_HOURS:
            raise ValueError(
                f"Dataframe length {len(df)} is less than required lookback {self.REQUIRED_LOOKBACK_HOURS}"
            )

        if validate:
            validate_risk_telemetry(df)

        forecast_df = self.forecaster.predict_dataframe(df)
        risk_df = self.risk_forecaster.predict_dataframe(df, validate=False)

        # Align on valid forecast indices (from lookback-1 to end)
        common_indices = forecast_df.index
        aligned_risk = risk_df.loc[common_indices]

        out_df = pd.DataFrame(index=common_indices)
        out_df["timestamp"] = forecast_df["timestamp"]
        out_df["station_id"] = forecast_df["station_id"]
        out_df["contract_version"] = self.CONTRACT_VERSION
        out_df["model_version"] = self.UNIFIED_MODEL_VERSION
        out_df["forecast_model_version"] = self.forecaster.config.model_name
        out_df["risk_model_version"] = self.risk_forecaster.model_version

        # Forecast columns
        out_df["power_demand_1h_kw"] = forecast_df["pred_power_demand_1h_kw"]
        out_df["battery_soc_1h_percent"] = forecast_df["pred_battery_soc_1h_percent"]
        out_df["energy_demand_6h_kwh"] = forecast_df["pred_energy_demand_6h_kwh"]
        out_df["energy_demand_24h_kwh"] = forecast_df["pred_energy_demand_24h_kwh"]

        # Risk columns
        out_df["deficit_risk_probability"] = aligned_risk["deficit_risk_probability"]
        out_df["deficit_risk"] = aligned_risk["deficit_risk"]
        out_df["deficit_risk_threshold"] = aligned_risk["threshold"]

        # Provenance columns
        out_df["provenance_source"] = "SYNTHETIC_POLARIX_OPERATIONAL_DATA"
        out_df["model_status"] = "CANDIDATE"

        return out_df
