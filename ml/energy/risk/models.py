"""
Classification Models & Evaluation Metrics for Energy Deficit-Risk Prediction (Polarix SIH26060).

Includes:
1. MajorityClassClassifier (Baseline 1)
2. RuleBasedPersistenceRiskClassifier (Baseline 2)
3. LogisticRegressionRiskClassifier (Linear with class-weights)
4. GradientBoostingRiskClassifier (Tree-based model with class-weights)
5. Comprehensive classification metrics with safety-oriented false-negative accounting.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.preprocessing import StandardScaler


class MajorityClassClassifier:
    """Predicts majority class probability based on training set prevalence."""

    def __init__(self):
        self.prevalence_ = 0.0

    def fit(self, X: np.ndarray, y: np.ndarray) -> MajorityClassClassifier:
        clean_y = y[~np.isnan(y)]
        self.prevalence_ = float(np.mean(clean_y == 1.0)) if len(clean_y) > 0 else 0.0
        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        n = len(X)
        p1 = np.full(n, self.prevalence_)
        p0 = 1.0 - p1
        return np.column_stack([p0, p1])

    def predict(self, X: np.ndarray, threshold: float = 0.5) -> np.ndarray:
        probs = self.predict_proba(X)[:, 1]
        return (probs >= threshold).astype(int)


class RuleBasedPersistenceRiskClassifier:
    """
    Heuristic physical rule: deficit risk is active if current power demand
    exceeds 90% of rated capacity or current battery SoC is below 30%.
    """

    def __init__(self, p_rated_mtr: float = 120.0, p_rated_brt: float = 150.0):
        self.p_rated_mtr = p_rated_mtr
        self.p_rated_brt = p_rated_brt

    def fit(self, X: np.ndarray, y: np.ndarray) -> RuleBasedPersistenceRiskClassifier:
        return self

    def predict_proba(self, X: np.ndarray, feature_names: Optional[List[str]] = None) -> np.ndarray:
        # If feature_names provided, locate indices
        p_idx = feature_names.index("power_demand_kw") if feature_names and "power_demand_kw" in feature_names else 0
        soc_idx = feature_names.index("battery_soc_percent") if feature_names and "battery_soc_percent" in feature_names else 2
        brt_idx = feature_names.index("station_is_brt") if feature_names and "station_is_brt" in feature_names else 13

        p_dem = X[:, p_idx]
        soc = X[:, soc_idx]
        is_brt = X[:, brt_idx]

        rated_cap = np.where(is_brt == 1.0, self.p_rated_brt, self.p_rated_mtr)
        rule_active = (p_dem > 0.90 * rated_cap) | (soc < 30.0)

        p1 = np.where(rule_active, 0.85, 0.02)
        p0 = 1.0 - p1
        return np.column_stack([p0, p1])

    def predict(self, X: np.ndarray, threshold: float = 0.5, feature_names: Optional[List[str]] = None) -> np.ndarray:
        probs = self.predict_proba(X, feature_names=feature_names)[:, 1]
        return (probs >= threshold).astype(int)


class LogisticRegressionRiskClassifier:
    """Interpretable linear classifier with class-weight balancing."""

    def __init__(self, random_state: int = 42):
        self.random_state = random_state
        self.scaler = StandardScaler()
        self.model = LogisticRegression(
            class_weight="balanced",
            max_iter=1000,
            random_state=random_state,
        )

    def fit(self, X: np.ndarray, y: np.ndarray) -> LogisticRegressionRiskClassifier:
        mask = ~np.isnan(y)
        X_clean, y_clean = X[mask], y[mask]
        X_scaled = self.scaler.fit_transform(X_clean)
        self.model.fit(X_scaled, y_clean)
        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        X_scaled = self.scaler.transform(X)
        return self.model.predict_proba(X_scaled)

    def predict(self, X: np.ndarray, threshold: float = 0.5) -> np.ndarray:
        probs = self.predict_proba(X)[:, 1]
        return (probs >= threshold).astype(int)


class GradientBoostingRiskClassifier:
    """Tree-based gradient boosting classifier with class balancing."""

    def __init__(self, random_state: int = 42, max_iter: int = 150):
        self.random_state = random_state
        self.model = HistGradientBoostingClassifier(
            class_weight="balanced",
            max_iter=max_iter,
            min_samples_leaf=15,
            random_state=random_state,
        )

    def fit(self, X: np.ndarray, y: np.ndarray) -> GradientBoostingRiskClassifier:
        mask = ~np.isnan(y)
        X_clean, y_clean = X[mask], y[mask]
        self.model.fit(X_clean, y_clean)
        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        return self.model.predict_proba(X)

    def predict(self, X: np.ndarray, threshold: float = 0.5) -> np.ndarray:
        probs = self.predict_proba(X)[:, 1]
        return (probs >= threshold).astype(int)


def compute_classification_metrics(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    threshold: float = 0.5,
) -> Dict[str, Any]:
    """
    Compute comprehensive classification metrics including specificity,
    balanced accuracy, PR-AUC, ROC-AUC, confusion matrix, and false negative analysis.
    """
    mask = ~np.isnan(y_true) & ~np.isnan(y_prob)
    if not np.any(mask):
        return {
            "accuracy": 0.0,
            "precision": 0.0,
            "recall": 0.0,
            "f1": 0.0,
            "specificity": 0.0,
            "balanced_accuracy": 0.0,
            "roc_auc": float("nan"),
            "pr_auc": float("nan"),
            "confusion_matrix": {"tn": 0, "fp": 0, "fn": 0, "tp": 0},
            "positive_prevalence": 0.0,
            "total_samples": 0,
            "false_negatives": 0,
            "false_positives": 0,
            "missed_deficit_rate": 0.0,
        }

    t = y_true[mask].astype(int)
    p_prob = y_prob[mask]
    p_pred = (p_prob >= threshold).astype(int)

    n_samples = len(t)
    n_positives = int(np.sum(t == 1))
    prevalence = float(n_positives / n_samples) if n_samples > 0 else 0.0

    # Confusion matrix
    tn, fp, fn, tp = 0, 0, 0, 0
    if len(np.unique(t)) == 1:
        # Single class present
        if t[0] == 0:
            tn = int(np.sum(p_pred == 0))
            fp = int(np.sum(p_pred == 1))
        else:
            tp = int(np.sum(p_pred == 1))
            fn = int(np.sum(p_pred == 0))
    else:
        cm = confusion_matrix(t, p_pred, labels=[0, 1])
        tn, fp, fn, tp = int(cm[0, 0]), int(cm[0, 1]), int(cm[1, 0]), int(cm[1, 1])

    acc = float((tp + tn) / n_samples)
    prec = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0
    rec = float(tp / (tp + fn)) if (tp + fn) > 0 else (0.0 if n_positives > 0 else 1.0)
    spec = float(tn / (tn + fp)) if (tn + fp) > 0 else 1.0
    f1 = float(2.0 * prec * rec / (prec + rec)) if (prec + rec) > 0 else 0.0
    bal_acc = float((rec + spec) / 2.0)

    # ROC-AUC & PR-AUC
    roc_auc = float("nan")
    pr_auc = float("nan")
    if len(np.unique(t)) > 1:
        try:
            roc_auc = float(roc_auc_score(t, p_prob))
            pr_auc = float(average_precision_score(t, p_prob))
        except Exception:
            pass

    missed_rate = float(fn / n_positives) if n_positives > 0 else 0.0

    return {
        "accuracy": round(acc, 4),
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "f1": round(f1, 4),
        "specificity": round(spec, 4),
        "balanced_accuracy": round(bal_acc, 4),
        "roc_auc": round(roc_auc, 4) if not np.isnan(roc_auc) else None,
        "pr_auc": round(pr_auc, 4) if not np.isnan(pr_auc) else None,
        "confusion_matrix": {"tn": tn, "fp": fp, "fn": fn, "tp": tp},
        "positive_prevalence": round(prevalence, 4),
        "total_samples": n_samples,
        "false_negatives": fn,
        "false_positives": fp,
        "missed_deficit_rate": round(missed_rate, 4),
    }
