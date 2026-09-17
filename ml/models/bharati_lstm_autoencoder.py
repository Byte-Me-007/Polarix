"""
PyTorch LSTM Autoencoder for Polarix Bharati Telemetry Anomaly Detection (SIH26060 - Person C).

Architecture:
- Encoder LSTM: (batch, seq_len, 1) -> hidden state -> latent bottleneck (latent_size=16)
- Decoder LSTM: repeats latent bottleneck across seq_len -> LSTM (hidden_size=32) -> output projection (1)
- Reconstruction error: MSE between normalized input sequence and reconstructed output.

Model Version: lstm-ae-bharati-v1
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional

import torch
import torch.nn as nn

MODEL_VERSION = "lstm-ae-bharati-v1"
STATION_ID = "BRT"


@dataclass
class BharatiLSTMConfig:
    station_id: str = STATION_ID
    input_size: int = 1
    seq_len: int = 30
    encoder_hidden_size: int = 32
    latent_size: int = 16
    decoder_hidden_size: int = 32
    num_layers: int = 1
    dropout: float = 0.0
    model_version: str = MODEL_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BharatiLSTMConfig":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class BharatiEncoder(nn.Module):
    """Encodes a time-series sequence into a compact latent bottleneck."""

    def __init__(
        self,
        input_size: int = 1,
        hidden_size: int = 32,
        latent_size: int = 16,
        num_layers: int = 1,
        dropout: float = 0.0,
    ) -> None:
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0,
        )
        self.fc_latent = nn.Linear(hidden_size, latent_size)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (batch_size, seq_len, input_size)
        _, (h_n, _) = self.lstm(x)
        # h_n[-1]: (batch_size, hidden_size)
        latent = self.fc_latent(h_n[-1])
        return latent


class BharatiDecoder(nn.Module):
    """Decodes a latent vector back into a reconstructed time-series sequence."""

    def __init__(
        self,
        latent_size: int = 16,
        hidden_size: int = 32,
        output_size: int = 1,
        seq_len: int = 30,
        num_layers: int = 1,
        dropout: float = 0.0,
    ) -> None:
        super().__init__()
        self.seq_len = seq_len
        self.lstm = nn.LSTM(
            input_size=latent_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0,
        )
        self.fc_out = nn.Linear(hidden_size, output_size)

    def forward(self, latent: torch.Tensor) -> torch.Tensor:
        # latent: (batch_size, latent_size)
        repeated_latent = latent.unsqueeze(1).repeat(1, self.seq_len, 1)
        # out: (batch_size, seq_len, hidden_size)
        out, _ = self.lstm(repeated_latent)
        # reconstruction: (batch_size, seq_len, output_size)
        reconstruction = self.fc_out(out)
        return reconstruction


class BharatiLSTMAutoencoder(nn.Module):
    """
    Sequence-to-sequence LSTM Autoencoder for Bharati station telemetry.
    """

    def __init__(self, config: Optional[BharatiLSTMConfig] = None, **kwargs: Any) -> None:
        super().__init__()
        if config is None:
            config = BharatiLSTMConfig(**kwargs)
        self.config = config

        self.encoder = BharatiEncoder(
            input_size=config.input_size,
            hidden_size=config.encoder_hidden_size,
            latent_size=config.latent_size,
            num_layers=config.num_layers,
            dropout=config.dropout,
        )
        self.decoder = BharatiDecoder(
            latent_size=config.latent_size,
            hidden_size=config.decoder_hidden_size,
            output_size=config.input_size,
            seq_len=config.seq_len,
            num_layers=config.num_layers,
            dropout=config.dropout,
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass.
        Input x: (batch_size, seq_len, input_size)
        Output: (batch_size, seq_len, input_size)
        """
        latent = self.encoder(x)
        reconstruction = self.decoder(latent)
        return reconstruction

    def compute_reconstruction_error(
        self, x: torch.Tensor, reduction: str = "mean"
    ) -> torch.Tensor:
        """
        Compute MSE reconstruction error.
        x: (batch_size, seq_len, input_size)
        """
        reconstructed = self.forward(x)
        sq_err = (x - reconstructed) ** 2
        per_sample_mse = torch.mean(sq_err, dim=(1, 2))
        if reduction == "mean":
            return torch.mean(per_sample_mse)
        elif reduction == "none":
            return per_sample_mse
        else:
            raise ValueError(f"Unsupported reduction: {reduction}")
