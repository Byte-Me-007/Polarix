"""
Sensor ML V2 Retraining Experiment Configuration (Polarix SIH26060 - Person C).

Defines reproducible hyperparameter configurations, scheduler policies,
and experiment paths for both Maitri ('MTR') and Bharati ('BRT') V2 candidates.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class SensorV2ExperimentConfig:
    """Configuration for Sensor ML V2 retraining and calibration experiments."""

    station_id: str
    station_name: str
    model_version: str
    dataset_csv: str
    seq_len: int = 30
    input_size: int = 1
    hidden_size: int = 32
    latent_size: int = 16
    num_layers: int = 1
    dropout: float = 0.0
    epochs: int = 60  # Increased epoch budget beyond V1 (was 30)
    batch_size: int = 64
    initial_lr: float = 0.001
    lr_scheduler: str = "ReduceLROnPlateau"  # Dynamic LR scheduling
    lr_scheduler_factor: float = 0.5
    lr_scheduler_patience: int = 4
    min_lr: float = 1e-5
    early_stopping_patience: int = 12  # Increased from 7 in V1
    seed: int = 42
    train_ratio: float = 0.70
    val_ratio: float = 0.15
    test_ratio: float = 0.15
    models_dir: str = "ml/experiments/sensor_v2/models"
    results_dir: str = "ml/experiments/sensor_v2/results"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


MAITRI_V2_CONFIG = SensorV2ExperimentConfig(
    station_id="MTR",
    station_name="Maitri",
    model_version="lstm-ae-v2-candidate",
    dataset_csv="ml/data/maitri_synthetic_telemetry.csv",
    seq_len=30,
    hidden_size=32,
    latent_size=16,
    epochs=60,
    batch_size=64,
    initial_lr=0.001,
    lr_scheduler="ReduceLROnPlateau",
    lr_scheduler_factor=0.5,
    lr_scheduler_patience=4,
    min_lr=1e-5,
    early_stopping_patience=12,
    seed=42,
)

BHARATI_V2_CONFIG = SensorV2ExperimentConfig(
    station_id="BRT",
    station_name="Bharati",
    model_version="lstm-ae-bharati-v2-candidate",
    dataset_csv="ml/data/bharati_synthetic_telemetry.csv",
    seq_len=30,
    hidden_size=32,
    latent_size=16,
    epochs=60,
    batch_size=64,
    initial_lr=0.001,
    lr_scheduler="ReduceLROnPlateau",
    lr_scheduler_factor=0.5,
    lr_scheduler_patience=4,
    min_lr=1e-5,
    early_stopping_patience=12,
    seed=42,
)
