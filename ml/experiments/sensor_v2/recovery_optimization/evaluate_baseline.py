"""
Reproducible Step 52 Baseline Evaluation Script (SIH26060 - Person C).

Reproduces the exact Step 52 Multivariate Sensor-Context baseline metrics across Maitri and Bharati:
- Maitri: Accuracy ≈ 71.01%, Precision ≈ 0.4138, Recall ≈ 0.4068, F1 ≈ 0.4103, FPR ≈ 0.1899, AUPRC ≈ 0.3430
- Bharati: Accuracy ≈ 70.59%, Precision ≈ 0.3962, Recall ≈ 0.3559, F1 ≈ 0.3750, FPR ≈ 0.1788, AUPRC ≈ 0.3475
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import numpy as np
import pandas as pd

from ml.experiments.sensor_v2.calibrate_v2_sensors import search_threshold
from ml.experiments.sensor_v2.config import SensorV2ExperimentConfig
from ml.experiments.sensor_v2.evaluate_v2_experiments import (
    calculate_binary_metrics,
    compute_roc_pr_metrics,
)
from ml.experiments.sensor_v2.hybrid_score.evaluate_hybrid_scores import (
    load_reconstructions_for_hybrid,
)
from ml.experiments.sensor_v2.hybrid_score.hybrid_scoring_functions import (
    fit_hybrid_normalization_parameters,
    normalize_and_combine_signals,
)
from ml.experiments.sensor_v2.multivariate_context.multivariate_scoring_functions import (
    align_station_multivariate_windows,
    compute_multivariate_fusion_scores,
)
from ml.experiments.sensor_v2.train_recovery_aware_models import (
    BHARATI_RECOVERY_CONFIG,
    MAITRI_RECOVERY_CONFIG,
)

MAITRI_SENSORS = ["TEMP_001", "PRESS_001", "HUM_001", "VIB_001", "POWER_001"]
BHARATI_SENSORS = ["BRT_TEMP_001", "BRT_PRESS_001", "BRT_HUM_001", "BRT_VIB_001", "BRT_POWER_001"]


def compute_step52_baseline(cfg: SensorV2ExperimentConfig, sensors: List[str]) -> Dict[str, Any]:
    """Compute and return exact Step 52 multivariate baseline metrics."""
    val_x, val_xh, val_meta, test_x, test_xh, test_meta = load_reconstructions_for_hybrid(cfg)

    norm_params = fit_hybrid_normalization_parameters(val_x, val_xh, val_meta)
    val_h3 = normalize_and_combine_signals(val_x, val_xh, val_meta, norm_params, w_curr=0.5, w_delta=0.2, w_drift=0.3)
    test_h3 = normalize_and_combine_signals(test_x, test_xh, test_meta, norm_params, w_curr=0.5, w_delta=0.2, w_drift=0.3)

    # Validation Alignment & Calibration
    df_val = pd.DataFrame(val_meta)
    val_meta_dict = {s_id: [val_meta[i] for i in df_val[df_val["sensor_id"] == s_id].index] for s_id in sensors}
    val_scores_dict = {s_id: val_h3[df_val[df_val["sensor_id"] == s_id].index] for s_id in sensors}
    val_aligned = align_station_multivariate_windows(cfg.station_id, val_meta_dict, val_scores_dict, sensors)
    s_val_mv, y_val_mv, _ = compute_multivariate_fusion_scores(val_aligned, strategy="robust")
    th_mv, _ = search_threshold(s_val_mv, y_val_mv, criterion="max_f1")

    # Test Alignment & Evaluation
    df_test = pd.DataFrame(test_meta)
    test_meta_dict = {s_id: [test_meta[i] for i in df_test[df_test["sensor_id"] == s_id].index] for s_id in sensors}
    test_scores_dict = {s_id: test_h3[df_test[df_test["sensor_id"] == s_id].index] for s_id in sensors}
    test_aligned = align_station_multivariate_windows(cfg.station_id, test_meta_dict, test_scores_dict, sensors)
    s_test_mv, y_test_mv, states_test = compute_multivariate_fusion_scores(test_aligned, strategy="robust")

    m_test = calculate_binary_metrics(y_test_mv, (s_test_mv > th_mv).astype(int))
    auc, pr = compute_roc_pr_metrics(y_test_mv, s_test_mv)
    m_test["auroc"] = auc
    m_test["auprc"] = pr
    m_test["threshold"] = float(th_mv)

    return m_test


def main() -> None:
    print("=== Recomputing Step 52 Baseline Metrics ===")
    mtr_base = compute_step52_baseline(MAITRI_RECOVERY_CONFIG, MAITRI_SENSORS)
    brt_base = compute_step52_baseline(BHARATI_RECOVERY_CONFIG, BHARATI_SENSORS)

    print("\nMaitri Step 52 Baseline:")
    print(json.dumps(mtr_base, indent=2))

    print("\nBharati Step 52 Baseline:")
    print(json.dumps(brt_base, indent=2))


if __name__ == "__main__":
    main()
