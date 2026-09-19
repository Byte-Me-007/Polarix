"""
Transition-Focused & Observation-Centric Scoring Formulations (Polarix SIH26060 - Person C).

Implements:
1. Last-Step Reconstruction Error:
   score_last = (x[..., -1, :] - x_hat[..., -1, :]) ** 2
2. Recent-Weighted Reconstruction Error:
   score_recent = sum_{k=0}^{L-1} w_k * (x[..., k, :] - x_hat[..., k, :]) ** 2
   where w_k = exp(alpha * k) / sum(exp(alpha * j))
3. Transition / Delta Error:
   delta_x = x[..., -1, :] - x[..., -2, :]
   delta_x_hat = x_hat[..., -1, :] - x_hat[..., -2, :]
   score_delta = (delta_x - delta_x_hat) ** 2
4. Composite Transition-Observation Error:
   score_composite = 0.5 * score_last + 0.5 * score_delta
"""

from __future__ import annotations

import numpy as np
import torch


def compute_last_step_error(x: np.ndarray, x_hat: np.ndarray) -> np.ndarray:
    """
    Compute squared reconstruction error strictly at the final (current) timestep.

    Parameters:
    -----------
    x : np.ndarray, shape (N, seq_len, 1) or (seq_len, 1)
        Input normalized sequence.
    x_hat : np.ndarray, shape (N, seq_len, 1) or (seq_len, 1)
        Reconstructed sequence.

    Returns:
    --------
    np.ndarray, shape (N,) or float: Squared error at final timestep.
    """
    if x.ndim == 2:
        return float((x[-1, 0] - x_hat[-1, 0]) ** 2)
    # Shape: (N, seq_len, 1) -> (N,)
    diff_last = x[:, -1, 0] - x_hat[:, -1, 0]
    return np.array(diff_last ** 2, dtype=float)


def compute_recent_weights(seq_len: int = 30, alpha: float = 0.15) -> np.ndarray:
    """
    Generate normalized exponential weights prioritizing recent observations.
    The final timestep has the highest weight.
    """
    indices = np.arange(seq_len, dtype=float)
    raw_weights = np.exp(alpha * indices)
    return raw_weights / np.sum(raw_weights)


def compute_recent_weighted_error(
    x: np.ndarray, x_hat: np.ndarray, alpha: float = 0.15
) -> np.ndarray:
    """
    Compute time-weighted reconstruction MSE giving higher weight to recent points.
    """
    weights = compute_recent_weights(seq_len=x.shape[-2], alpha=alpha)
    if x.ndim == 2:
        # x: (seq_len, 1)
        sq_err = (x[:, 0] - x_hat[:, 0]) ** 2
        return float(np.sum(weights * sq_err))

    # x: (N, seq_len, 1)
    sq_err = (x[:, :, 0] - x_hat[:, :, 0]) ** 2  # (N, seq_len)
    return np.array(np.sum(sq_err * weights[np.newaxis, :], axis=1), dtype=float)


def compute_delta_transition_error(x: np.ndarray, x_hat: np.ndarray) -> np.ndarray:
    """
    Compute discrepancy between observed delta (x[t] - x[t-1]) and reconstructed delta.
    """
    if x.ndim == 2:
        delta_obs = x[-1, 0] - x[-2, 0]
        delta_rec = x_hat[-1, 0] - x_hat[-2, 0]
        return float((delta_obs - delta_rec) ** 2)

    delta_obs = x[:, -1, 0] - x[:, -2, 0]
    delta_rec = x_hat[:, -1, 0] - x_hat[:, -2, 0]
    return np.array((delta_obs - delta_rec) ** 2, dtype=float)


def compute_composite_transition_error(
    x: np.ndarray, x_hat: np.ndarray, last_weight: float = 0.5, delta_weight: float = 0.5
) -> np.ndarray:
    """
    Compute composite score balancing current observation reconstruction and transition dynamics.
    """
    last_err = compute_last_step_error(x, x_hat)
    delta_err = compute_delta_transition_error(x, x_hat)
    return last_weight * last_err + delta_weight * delta_err
