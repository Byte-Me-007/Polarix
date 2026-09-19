"""
Authoritative Evaluation & Transfer Diagnostic Suite for Energy Deficit Risk (Polarix SIH26060).

Evaluates:
1. Primary Chronological Test Evaluation for MTR, BRT, and Combined partitions.
2. Benchmark comparison across Majority Class, Rule-Based Persistence, Logistic Regression, and Gradient Boosting.
3. Event-regime disaggregated error rates (NORMAL, HIGH_LOAD, POWER_CONSTRAINT).
4. Exploratory Cross-Station Transfer Generalization (Train MTR -> Test BRT, Train BRT -> Test MTR).
5. Serializes deficit_risk_metrics.json and generates deficit_risk_report.md.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import joblib
import numpy as np
import pandas as pd

from ml.energy.risk.features import RISK_FEATURE_COLUMNS, extract_risk_features
from ml.energy.risk.inference import DeficitRiskForecaster
from ml.energy.risk.models import (
    GradientBoostingRiskClassifier,
    LogisticRegressionRiskClassifier,
    MajorityClassClassifier,
    RuleBasedPersistenceRiskClassifier,
    compute_classification_metrics,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("EnergyRiskEvaluate")


def run_full_risk_evaluation(
    data_dir: Path = Path("ml/energy/data"),
    model_dir: Path = Path("ml/energy/models"),
    results_dir: Path = Path("ml/energy/results"),
    seed: int = 42,
) -> Dict[str, Any]:
    """Execute complete deficit risk benchmark and export Markdown report."""
    results_dir.mkdir(parents=True, exist_ok=True)

    mtr_df = pd.read_csv(data_dir / "maitri_energy_telemetry.csv")
    brt_df = pd.read_csv(data_dir / "bharati_energy_telemetry.csv")

    mtr_train = mtr_df[mtr_df["split"] == "train"].copy()
    mtr_test = mtr_df[mtr_df["split"] == "test"].copy()

    brt_train = brt_df[brt_df["split"] == "train"].copy()
    brt_test = brt_df[brt_df["split"] == "test"].copy()

    comb_train = pd.concat([mtr_train, brt_train], ignore_index=True)
    comb_test = pd.concat([mtr_test, brt_test], ignore_index=True)

    # 1. Load Trained Production Forecaster
    forecaster = DeficitRiskForecaster(model_dir=model_dir)
    frozen_threshold = forecaster.threshold

    # Train baselines on combined training data
    X_tr_df, y_tr_s = extract_risk_features(comb_train)
    X_tr = X_tr_df.to_numpy(dtype=np.float32)
    y_tr = y_tr_s.to_numpy(dtype=np.float32)

    maj_model = MajorityClassClassifier().fit(X_tr, y_tr)
    rule_model = RuleBasedPersistenceRiskClassifier().fit(X_tr, y_tr)
    lr_model = LogisticRegressionRiskClassifier(random_state=seed).fit(X_tr, y_tr)

    # 2. Evaluate a Given Data Partition
    def evaluate_models_on_partition(df: pd.DataFrame) -> Dict[str, Any]:
        X_df, y_s = extract_risk_features(df)
        X_vals = X_df.to_numpy(dtype=np.float32)
        y_vals = y_s.to_numpy(dtype=np.float32)

        # Predictions
        neural_gb_probs = forecaster.model.predict_proba(X_vals)[:, 1]
        maj_probs = maj_model.predict_proba(X_vals)[:, 1]
        rule_probs = rule_model.predict_proba(X_vals, feature_names=RISK_FEATURE_COLUMNS)[:, 1]
        lr_probs = lr_model.predict_proba(X_vals)[:, 1]

        return {
            "gradient_boosting_v1": compute_classification_metrics(y_vals, neural_gb_probs, threshold=frozen_threshold),
            "logistic_regression": compute_classification_metrics(y_vals, lr_probs, threshold=0.50),
            "rule_based_persistence": compute_classification_metrics(y_vals, rule_probs, threshold=0.50),
            "majority_class": compute_classification_metrics(y_vals, maj_probs, threshold=0.50),
        }

    mtr_test_metrics = evaluate_models_on_partition(mtr_test)
    brt_test_metrics = evaluate_models_on_partition(brt_test)
    comb_test_metrics = evaluate_models_on_partition(comb_test)

    # 3. Exploratory Cross-Station Generalization Transfer Experiments
    logger.info("Running exploratory cross-station transfer experiments...")
    # Transfer 1: Train MTR -> Test BRT
    X_mtr_tr_df, y_mtr_tr_s = extract_risk_features(mtr_train)
    gb_mtr_only = GradientBoostingRiskClassifier(random_state=seed).fit(
        X_mtr_tr_df.to_numpy(dtype=np.float32), y_mtr_tr_s.to_numpy(dtype=np.float32)
    )
    X_brt_te_df, y_brt_te_s = extract_risk_features(brt_test)
    transfer_mtr_to_brt_probs = gb_mtr_only.predict_proba(X_brt_te_df.to_numpy(dtype=np.float32))[:, 1]
    transfer_mtr_to_brt_metrics = compute_classification_metrics(
        y_brt_te_s.to_numpy(dtype=np.float32), transfer_mtr_to_brt_probs, threshold=frozen_threshold
    )

    # Transfer 2: Train BRT -> Test MTR
    X_brt_tr_df, y_brt_tr_s = extract_risk_features(brt_train)
    gb_brt_only = GradientBoostingRiskClassifier(random_state=seed).fit(
        X_brt_tr_df.to_numpy(dtype=np.float32), y_brt_tr_s.to_numpy(dtype=np.float32)
    )
    X_mtr_te_df, y_mtr_te_s = extract_risk_features(mtr_test)
    transfer_brt_to_mtr_probs = gb_brt_only.predict_proba(X_mtr_te_df.to_numpy(dtype=np.float32))[:, 1]
    transfer_brt_to_mtr_metrics = compute_classification_metrics(
        y_mtr_te_s.to_numpy(dtype=np.float32), transfer_brt_to_mtr_probs, threshold=frozen_threshold
    )

    # 4. Event Regime Breakdown on Combined Test
    event_metrics = {}
    for ev in ["NORMAL", "HIGH_LOAD", "POWER_CONSTRAINT"]:
        sub_df = comb_test[comb_test["event_type"] == ev].copy()
        if len(sub_df) > 0:
            X_ev_df, y_ev_s = extract_risk_features(sub_df)
            ev_probs = forecaster.model.predict_proba(X_ev_df.to_numpy(dtype=np.float32))[:, 1]
            event_metrics[ev] = compute_classification_metrics(
                y_ev_s.to_numpy(dtype=np.float32), ev_probs, threshold=frozen_threshold
            )

    full_results = {
        "model_version": forecaster.model_version,
        "frozen_decision_threshold": frozen_threshold,
        "evaluation_partition": "Held-Out Test (Nov 7 - Dec 31, 2026)",
        "station_test_metrics": {
            "MTR": mtr_test_metrics,
            "BRT": brt_test_metrics,
            "COMBINED": comb_test_metrics,
        },
        "exploratory_cross_station_transfer": {
            "train_mtr_test_brt": transfer_mtr_to_brt_metrics,
            "train_brt_test_mtr": transfer_brt_to_mtr_metrics,
        },
        "event_regime_metrics": event_metrics,
    }

    # Save JSON Metrics
    metrics_path = results_dir / "deficit_risk_metrics.json"
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(full_results, f, indent=2)
    logger.info(f"Saved deficit risk metrics to {metrics_path}")

    # Generate Markdown Report
    report_md_path = results_dir / "deficit_risk_report.md"
    generate_risk_markdown_report(full_results, report_md_path)
    logger.info(f"Generated deficit risk report: {report_md_path}")

    return full_results


def generate_risk_markdown_report(data: Dict[str, Any], output_path: Path) -> None:
    """Generate comprehensive Markdown diagnostic report for energy deficit risk."""
    comb = data["station_test_metrics"]["COMBINED"]
    mtr = data["station_test_metrics"]["MTR"]
    brt = data["station_test_metrics"]["BRT"]
    trans = data["exploratory_cross_station_transfer"]
    thresh = data["frozen_decision_threshold"]

    gb_comb = comb["gradient_boosting_v1"]
    lr_comb = comb["logistic_regression"]
    rule_comb = comb["rule_based_persistence"]
    maj_comb = comb["majority_class"]

    md = f"""# Polarix Energy Deficit-Risk Prediction Report (SIH26060)

**Model Version:** `{data['model_version']}`
**Operating Decision Threshold:** `tau = {thresh:.4f}` (Frozen from validation tuning)
**Evaluation Partition:** Held-Out Chronological Test Partition (`2026-11-07T06:00:00Z` $\\to$ `2026-12-31T23:00:00Z`, $N=1,314$ hours/station)
**Author:** Person C — Machine Learning Specialist
**Evaluation Date:** 2026-09-19

---

## 1. Executive Summary & Problem Formulation

Energy Deficit-Risk prediction models the probability that an Antarctic research station microgrid will enter a critical deficit condition in the next hour ($t \\to t+1\\,\\text{{h}}$):
$$\\text{{Deficit Condition}} \\iff (\\text{{SoC}}(t+1) < 25.0\\%) \\lor (P_{{\\text{{demand}}}}(t+1) > 0.95 \\cdot P_{{\\text{{generator, rated}}}})$$

### Class Distribution Across Chronological Splits:
- **Maitri (`MTR`):** Train $156$ positives ($2.54\\%$) | Val $49$ positives ($3.73\\%$) | Test $27$ positives ($2.05\\%$)
- **Bharati (`BRT`):** Train $76$ positives ($1.24\\%$) | Val $18$ positives ($1.37\\%$) | Test $23$ positives ($1.75\\%$)
- **Combined:** Train $232$ positives ($1.89\\%$) | Val $67$ positives ($2.55\\%$) | Test $50$ positives ($1.90\\%$)

---

## 2. Comparative Model Benchmark (Combined Test Partition, N={gb_comb['total_samples']})

| Model Architecture | Accuracy | Precision | Recall | F1 Score | Specificity | Balanced Acc | ROC-AUC | PR-AUC | Missed Deficits |
|:---|:---|:---|:---|:---|:---|:---|:---|:---|:---|
| **Gradient Boosting V1 (Selected)** | **${gb_comb['accuracy']*100:.2f}\\%$** | **${gb_comb['precision']*100:.2f}\\%$** | **${gb_comb['recall']*100:.2f}\\%$** | **${gb_comb['f1']:.4f}$** | **${gb_comb['specificity']:.4f}$** | **${gb_comb['balanced_accuracy']:.4f}$** | **${gb_comb['roc_auc']:.4f}$** | **${gb_comb['pr_auc']:.4f}$** | **${gb_comb['false_negatives']} ({gb_comb['missed_deficit_rate']*100:.1f}\\%)$** |
| **Logistic Regression (Balanced)** | ${lr_comb['accuracy']*100:.2f}\\%$ | ${lr_comb['precision']*100:.2f}\\%$ | ${lr_comb['recall']*100:.2f}\\%$ | ${lr_comb['f1']:.4f}$ | ${lr_comb['specificity']:.4f}$ | ${lr_comb['balanced_accuracy']:.4f}$ | ${lr_comb['roc_auc']:.4f}$ | ${lr_comb['pr_auc']:.4f}$ | ${lr_comb['false_negatives']} (${lr_comb['missed_deficit_rate']*100:.1f}\\%)$ |
| **Rule-Based Persistence** | ${rule_comb['accuracy']*100:.2f}\\%$ | ${rule_comb['precision']*100:.2f}\\%$ | ${rule_comb['recall']*100:.2f}\\%$ | ${rule_comb['f1']:.4f}$ | ${rule_comb['specificity']:.4f}$ | ${rule_comb['balanced_accuracy']:.4f}$ | ${rule_comb['roc_auc']:.4f}$ | ${rule_comb['pr_auc']:.4f}$ | ${rule_comb['false_negatives']} (${rule_comb['missed_deficit_rate']*100:.1f}\\%)$ |
| **Majority Class Baseline** | ${maj_comb['accuracy']*100:.2f}\\%$ | ${maj_comb['precision']*100:.2f}\\%$ | ${maj_comb['recall']*100:.2f}\\%$ | ${maj_comb['f1']:.4f}$ | ${maj_comb['specificity']:.4f}$ | ${maj_comb['balanced_accuracy']:.4f}$ | ${maj_comb['roc_auc']:.4f}$ | ${maj_comb['pr_auc']:.4f}$ | ${maj_comb['false_negatives']} (${maj_comb['missed_deficit_rate']*100:.1f}\\%)$ |

---

## 3. Station-Specific Performance

### 3.1 Maitri (`MTR`) — Inland Microgrid (N={mtr['gradient_boosting_v1']['total_samples']}, Positives={mtr['gradient_boosting_v1']['confusion_matrix']['tp'] + mtr['gradient_boosting_v1']['confusion_matrix']['fn']})
- **Gradient Boosting:** Accuracy: ${mtr['gradient_boosting_v1']['accuracy']*100:.2f}\\%$, Precision: ${mtr['gradient_boosting_v1']['precision']*100:.2f}\\%$, Recall: ${mtr['gradient_boosting_v1']['recall']*100:.2f}\\%$, F1: ${mtr['gradient_boosting_v1']['f1']:.4f}$, Specificity: ${mtr['gradient_boosting_v1']['specificity']:.4f}$
- **Confusion Matrix:** TN={mtr['gradient_boosting_v1']['confusion_matrix']['tn']}, FP={mtr['gradient_boosting_v1']['confusion_matrix']['fp']}, FN={mtr['gradient_boosting_v1']['confusion_matrix']['fn']}, TP={mtr['gradient_boosting_v1']['confusion_matrix']['tp']}
- **False Negatives:** {mtr['gradient_boosting_v1']['false_negatives']} (Missed Deficit Rate: {mtr['gradient_boosting_v1']['missed_deficit_rate']*100:.2f}%)

### 3.2 Bharati (`BRT`) — Coastal Microgrid (N={brt['gradient_boosting_v1']['total_samples']}, Positives={brt['gradient_boosting_v1']['confusion_matrix']['tp'] + brt['gradient_boosting_v1']['confusion_matrix']['fn']})
- **Gradient Boosting:** Accuracy: ${brt['gradient_boosting_v1']['accuracy']*100:.2f}\\%$, Precision: ${brt['gradient_boosting_v1']['precision']*100:.2f}\\%$, Recall: ${brt['gradient_boosting_v1']['recall']*100:.2f}\\%$, F1: ${brt['gradient_boosting_v1']['f1']:.4f}$, Specificity: ${brt['gradient_boosting_v1']['specificity']:.4f}$
- **Confusion Matrix:** TN={brt['gradient_boosting_v1']['confusion_matrix']['tn']}, FP={brt['gradient_boosting_v1']['confusion_matrix']['fp']}, FN={brt['gradient_boosting_v1']['confusion_matrix']['fn']}, TP={brt['gradient_boosting_v1']['confusion_matrix']['tp']}
- **False Negatives:** {brt['gradient_boosting_v1']['false_negatives']} (Missed Deficit Rate: {brt['gradient_boosting_v1']['missed_deficit_rate']*100:.2f}%)

---

## 4. Exploratory Cross-Station Transfer Generalization

Transfer experiments evaluate model portability when trained strictly on one station and tested on the other:

| Transfer Direction | Training Station | Evaluation Station | Test Accuracy | Precision | Recall | F1 Score | Specificity | ROC-AUC | PR-AUC |
|:---|:---|:---|:---|:---|:---|:---|:---|:---|:---|
| **MTR $\\to$ BRT Transfer** | Maitri (Inland, $120\\,\\text{{kW}}$) | Bharati (Coastal, $150\\,\\text{{kW}}$) | ${trans['train_mtr_test_brt']['accuracy']*100:.2f}\\%$ | ${trans['train_mtr_test_brt']['precision']*100:.2f}\\%$ | ${trans['train_mtr_test_brt']['recall']*100:.2f}\\%$ | ${trans['train_mtr_test_brt']['f1']:.4f}$ | ${trans['train_mtr_test_brt']['specificity']:.4f}$ | ${trans['train_mtr_test_brt']['roc_auc']:.4f}$ | ${trans['train_mtr_test_brt']['pr_auc']:.4f}$ |
| **BRT $\\to$ MTR Transfer** | Bharati (Coastal, $150\\,\\text{{kW}}$) | Maitri (Inland, $120\\,\\text{{kW}}$) | ${trans['train_brt_test_mtr']['accuracy']*100:.2f}\\%$ | ${trans['train_brt_test_mtr']['precision']*100:.2f}\\%$ | ${trans['train_brt_test_mtr']['recall']*100:.2f}\\%$ | ${trans['train_brt_test_mtr']['f1']:.4f}$ | ${trans['train_brt_test_mtr']['specificity']:.4f}$ | ${trans['train_brt_test_mtr']['roc_auc']:.4f}$ | ${trans['train_brt_test_mtr']['pr_auc']:.4f}$ |

---

## 5. Limitations & Governance Disclaimer

> [!CAUTION]
> **Safety Disclaimer:**
> This model provides an advisory machine learning probability signal and **must not** be used as an autonomous control cutoff without supervisory microgrid engineering rules. Telemetry is calibrated from synthetic Polarix operational data.
"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(md)


if __name__ == "__main__":
    run_full_risk_evaluation()
