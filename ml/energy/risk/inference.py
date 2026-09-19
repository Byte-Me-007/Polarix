"""
Inference Engine for Energy Deficit-Risk Prediction (Polarix SIH26060).

Provides:
1. Canonical operational prediction interface (dict, window DataFrame, full DataFrame).
2. Authoritative frozen decision threshold loaded directly from model artifact metadata.
3. Strict causal feature verification, range checking, and future-target exclusion.
4. Structured prediction dataclass matching the Polarix operational API contract.
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import joblib
import numpy as np
import pandas as pd

from ml.energy.risk.features import (
    REQUIRED_RAW_COLUMNS,
    RISK_FEATURE_COLUMNS,
    TARGET_COLUMNS_EXCLUDED,
    extract_risk_features,
    validate_risk_telemetry,
)


@dataclass
class DeficitRiskPrediction:
    """Canonical operational container for deficit risk predictions."""

    station_id: str
    timestamp: str
    deficit_risk_probability: float
    deficit_risk: bool
    threshold: float
    model_version: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class DeficitRiskForecaster:
    """Inference engine for Energy Deficit Risk Classification."""

    def __init__(
        self,
        model_dir: Union[str, Path] = Path("ml/energy/models"),
        model_name: str = "energy_deficit_risk_v1",
    ):
        self.model_dir = Path(model_dir)
        self.model_name = model_name

        self.bundle_path = self.model_dir / f"{model_name}.joblib"
        self.config_path = self.model_dir / f"{model_name}_config.json"

        if not self.bundle_path.exists():
            raise FileNotFoundError(f"Model bundle missing: {self.bundle_path}")
        if not self.config_path.exists():
            raise FileNotFoundError(f"Model config missing: {self.config_path}")

        # Load config
        with open(self.config_path, "r", encoding="utf-8") as f:
            self.config = json.load(f)

        # Load bundle
        bundle = joblib.load(self.bundle_path)
        self.model = bundle["model"]
        self.feature_names = bundle["feature_names"]
        self.threshold = float(self.config.get("selected_threshold", bundle.get("threshold", 0.35)))
        self.model_version = bundle.get(
            "model_version", self.config.get("model_version", self.config.get("model_name", "energy-deficit-risk-v1"))
        )

        # Verify feature order and count
        if len(self.feature_names) != 26:
            raise ValueError(f"Expected exactly 26 features in model bundle, found {len(self.feature_names)}")

    def predict_window(self, df_window: pd.DataFrame, validate: bool = True) -> DeficitRiskPrediction:
        """
        Generate deficit risk prediction for the most recent observation in a historical window.

        Parameters:
            df_window: Historical telemetry window containing required causal fields.
            validate: Whether to validate physical ranges and schema bounds.
        """
        if len(df_window) == 0:
            raise ValueError("Input dataframe window is empty.")

        if validate:
            validate_risk_telemetry(df_window)

        # Extract causal features strictly
        X_df, _ = extract_risk_features(df_window, validate=False)

        # Take the feature vector for the latest timestamp in explicit canonical order
        x_vec = X_df[self.feature_names].iloc[-1:].to_numpy(dtype=np.float32)

        probs = self.model.predict_proba(x_vec)
        # Verify binary probability semantics: index 1 is positive class (deficit risk = 1)
        prob = float(probs[0, 1])
        prob = max(0.0, min(1.0, prob))
        is_risk = bool(prob >= self.threshold)

        ts_now = str(df_window["timestamp"].iloc[-1])
        station_id = str(df_window["station_id"].iloc[-1])

        return DeficitRiskPrediction(
            station_id=station_id,
            timestamp=ts_now,
            deficit_risk_probability=round(prob, 4),
            deficit_risk=is_risk,
            threshold=round(self.threshold, 4),
            model_version=self.model_version,
        )

    def predict_dict(self, telemetry: Dict[str, Any], validate: bool = True) -> DeficitRiskPrediction:
        """
        Generate deficit risk prediction for a single telemetry record dictionary.
        """
        df_single = pd.DataFrame([telemetry])
        return self.predict_window(df_single, validate=validate)

    def predict_dataframe(self, df: pd.DataFrame, validate: bool = True) -> pd.DataFrame:
        """
        Generate deficit risk predictions over an entire station telemetry DataFrame.
        """
        if len(df) == 0:
            raise ValueError("Input DataFrame is empty.")

        if validate:
            validate_risk_telemetry(df)

        X_df, _ = extract_risk_features(df, validate=False)
        X_vals = X_df[self.feature_names].to_numpy(dtype=np.float32)

        probs = self.model.predict_proba(X_vals)[:, 1]
        probs = np.clip(probs, 0.0, 1.0)
        preds = (probs >= self.threshold).astype(bool)

        out_df = pd.DataFrame(index=df.index)
        out_df["timestamp"] = df["timestamp"].values
        out_df["station_id"] = df["station_id"].values
        out_df["deficit_risk_probability"] = np.round(probs, 4)
        out_df["deficit_risk"] = preds
        out_df["threshold"] = round(self.threshold, 4)
        out_df["model_version"] = self.model_version

        return out_df
