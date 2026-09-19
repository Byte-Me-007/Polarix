"""
Strictly Causal Persistence Filter (SIH26060 - Person C).

Guarantees:
1. Purely Causal: Prediction at time t depends strictly on observations up to time t (t <= current).
2. Zero Lookahead: Never inspects future values (t+1, t+2, etc.).
3. K-Consecutive Invariant: Emits an anomaly alarm at step t if and only if the anomaly threshold
   has been breached for at least K consecutive causal observations (t-K+1 ... t).

Semantics:
- K = 1: Standard causal thresholding (emits alarm on first breach).
- K = 2: Requires 2 consecutive breaches (emits alarm on second consecutive breach).
- K = 3: Requires 3 consecutive breaches (emits alarm on third consecutive breach).
- K = 4: Requires 4 consecutive breaches (emits alarm on fourth consecutive breach).
"""

from __future__ import annotations

from typing import Union

import numpy as np


def apply_causal_persistence(
    scores: Union[np.ndarray, list],
    threshold: float,
    k: int = 1,
) -> np.ndarray:
    """
    Apply strictly causal K-consecutive persistence filter to a sequence of scores.

    Parameters:
    -----------
    scores : np.ndarray or list of float
        Chronological anomaly scores S(0), S(1), ..., S(N-1).
    threshold : float
        Decision threshold for triggering an anomaly breach.
    k : int, default=1
        Number of consecutive breaches required to emit an anomaly prediction.

    Returns:
    --------
    predictions : np.ndarray of int (0 or 1), shape (N,)
    """
    if k < 1:
        raise ValueError(f"Persistence parameter K must be >= 1, got {k}")

    arr = np.asarray(scores, dtype=float)
    n = len(arr)
    if n == 0:
        return np.empty(0, dtype=int)

    preds = np.zeros(n, dtype=int)
    consecutive_breaches = 0

    for t in range(n):
        s_t = arr[t]
        if s_t >= threshold:
            consecutive_breaches += 1
            if consecutive_breaches >= k:
                preds[t] = 1
            else:
                preds[t] = 0
        else:
            consecutive_breaches = 0
            preds[t] = 0

    return preds
