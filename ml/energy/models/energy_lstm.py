"""
PyTorch Neural Network Baseline for Polarix Energy Microgrid Forecasting (SIH26060).

Implements a multi-horizon, multi-target LSTM neural forecaster:
- Input: 24-hour sequence of 18 causal features.
- Backbone: 2-layer stacked LSTM with recurrent regularization.
- Head: Multi-task regression projection mapping hidden state to 4 forecasting targets:
  1. Task A: target_power_demand_1h_kw
  2. Task B: target_battery_soc_1h_percent
  3. Task C: target_energy_demand_6h_kwh
  4. Task D: target_energy_demand_24h_kwh
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import torch
import torch.nn as nn


@dataclass
class EnergyModelConfig:
    """Configuration parameters for Energy ML neural model."""

    model_name: str = "lstm-energy-baseline-v1"
    model_type: str = "LSTM"
    input_dim: int = 18
    hidden_dim: int = 48
    num_layers: int = 2
    num_targets: int = 4
    dropout: float = 0.15
    lookback: int = 24
    batch_size: int = 64
    learning_rate: float = 0.001
    weight_decay: float = 1e-5
    max_epochs: int = 40
    early_stopping_patience: int = 8
    seed: int = 42

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> EnergyModelConfig:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def save(self, filepath: Path) -> None:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, filepath: Path) -> EnergyModelConfig:
        with open(filepath, "r", encoding="utf-8") as f:
            return cls.from_dict(json.load(f))


class EnergyLSTM(nn.Module):
    """Stacked LSTM with multi-task regression head for Antarctic microgrid forecasting."""

    def __init__(self, config: EnergyModelConfig):
        super().__init__()
        self.config = config

        self.lstm = nn.LSTM(
            input_size=config.input_dim,
            hidden_size=config.hidden_dim,
            num_layers=config.num_layers,
            batch_first=True,
            dropout=config.dropout if config.num_layers > 1 else 0.0,
        )

        self.head = nn.Sequential(
            nn.Linear(config.hidden_dim, config.hidden_dim),
            nn.ReLU(),
            nn.Dropout(p=config.dropout),
            nn.Linear(config.hidden_dim, config.num_targets),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass.
        Args:
            x: Input tensor of shape (batch_size, lookback, input_dim)
        Returns:
            out: Predicted normalized targets of shape (batch_size, num_targets)
        """
        # lstm_out: (batch_size, seq_len, hidden_dim)
        lstm_out, _ = self.lstm(x)
        # Take the representation at the final timestep (causal summary up to timestamp t)
        last_hidden = lstm_out[:, -1, :]
        out = self.head(last_hidden)
        return out
