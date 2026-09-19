"""
PyTorch Multi-Horizon Temperature Forecasting LSTM Model (Polarix SIH26060 - Person C).

A causal, multi-horizon Recurrent Neural Network for predicting Antarctic ambient
temperatures at horizons t+1h, t+6h, and t+24h.
"""

from __future__ import annotations

from typing import Dict, Any, Optional
import torch
import torch.nn as nn


class TemperatureLSTM(nn.Module):
    """
    Lightweight Multi-Horizon LSTM for station-aware Antarctic temperature forecasting.

    Inputs:
        x: Tensor of shape (batch_size, sequence_length, num_features)
    Outputs:
        Tensor of shape (batch_size, 3) corresponding to:
        [0] -> temperature_1h_c (t + 1h)
        [1] -> temperature_6h_c (t + 6h)
        [2] -> temperature_24h_c (t + 24h)
    """

    def __init__(
        self,
        input_dim: int = 9,
        hidden_dim: int = 64,
        num_layers: int = 2,
        output_dim: int = 3,
        dropout: float = 0.1,
        bidirectional: bool = False,
    ) -> None:
        super().__init__()
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.output_dim = output_dim
        self.dropout_rate = dropout
        self.bidirectional = bidirectional

        self.lstm = nn.LSTM(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0,
            bidirectional=bidirectional,
        )

        effective_hidden = hidden_dim * (2 if bidirectional else 1)
        self.fc_head = nn.Sequential(
            nn.Linear(effective_hidden, 32),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(32, output_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass.
        Args:
            x: Sequence tensor of shape (batch_size, seq_len, input_dim)
        Returns:
            Multi-horizon forecasts tensor of shape (batch_size, 3)
        """
        lstm_out, (hn, cn) = self.lstm(x)
        # Take the output at the final timestep for causal autoregression
        last_step = lstm_out[:, -1, :]
        out = self.fc_head(last_step)
        return out

    def get_parameter_count(self) -> Dict[str, int]:
        """Returns total and trainable parameter counts."""
        total = sum(p.numel() for p in self.parameters())
        trainable = sum(p.numel() for p in self.parameters() if p.requires_grad)
        return {"total_parameters": total, "trainable_parameters": trainable}
