"""
PyTorch LSTM Autoencoder for Polarix Maitri Telemetry Anomaly Detection (SIH26060).

Architecture:
- Encoder LSTM: Processes time-series window (batch, seq_len, input_size) -> hidden state
- Latent Layer: Projects encoder representation into lower-dimensional bottleneck
- Repeat Vector: Replicates latent bottleneck vector across seq_len steps
- Decoder LSTM: Reconstructs sequence dynamics from latent representation
- Output Projection: Linear layer returning reconstructed sequence (batch, seq_len, input_size)

Reconstruction error:
- Mean Squared Error (MSE) between actual normalized input and reconstructed sequence.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional, Tuple

import torch
import torch.nn as nn

MODEL_VERSION = "lstm-ae-v1"


@dataclass
class LSTMAutoencoderConfig:
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
    def from_dict(cls, data: Dict[str, Any]) -> "LSTMAutoencoderConfig":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class Encoder(nn.Module):
    """Encodes a multi-step sequence into a fixed-size latent bottleneck."""

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


class Decoder(nn.Module):
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
        # Repeat latent vector across seq_len time steps
        repeated_latent = latent.unsqueeze(1).repeat(1, self.seq_len, 1)
        # (batch_size, seq_len, latent_size)
        out, _ = self.lstm(repeated_latent)
        # out: (batch_size, seq_len, hidden_size)
        reconstruction = self.fc_out(out)
        # (batch_size, seq_len, output_size)
        return reconstruction


class LSTMAutoencoder(nn.Module):
    """
    Complete sequence-to-sequence LSTM Autoencoder.
    """

    def __init__(self, config: Optional[LSTMAutoencoderConfig] = None, **kwargs: Any) -> None:
        super().__init__()
        if config is None:
            config = LSTMAutoencoderConfig(**kwargs)
        self.config = config

        self.encoder = Encoder(
            input_size=config.input_size,
            hidden_size=config.encoder_hidden_size,
            latent_size=config.latent_size,
            num_layers=config.num_layers,
            dropout=config.dropout,
        )
        self.decoder = Decoder(
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
        Compute per-sequence or batch MSE reconstruction error.
        x: (batch_size, seq_len, input_size)
        Returns:
            If reduction == 'none': (batch_size,) tensor of per-sample MSEs.
            If reduction == 'mean': scalar scalar tensor.
        """
        reconstructed = self.forward(x)
        # Squared error per element: (batch_size, seq_len, input_size)
        sq_err = (x - reconstructed) ** 2
        # Average across sequence length and feature dimensions: (batch_size,)
        per_sample_mse = torch.mean(sq_err, dim=(1, 2))
        if reduction == "mean":
            return torch.mean(per_sample_mse)
        elif reduction == "none":
            return per_sample_mse
        else:
            raise ValueError(f"Unsupported reduction: {reduction}")
