"""
Sensor ML V2 Experiment Pipeline Runner (Polarix SIH26060 - Person C).

Executes the complete end-to-end V2 candidate workflow:
1. Trains Maitri and Bharati V2 candidate models with enhanced training configuration.
2. Performs validation-only threshold calibration.
3. Evaluates candidates on the exact same held-out test splits.
4. Generates comparison reports (JSON & Markdown) against frozen V1 baseline.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ml.experiments.sensor_v2.config import BHARATI_V2_CONFIG, MAITRI_V2_CONFIG
from ml.experiments.sensor_v2.evaluate_v2_experiments import run_full_v2_evaluation_suite
from ml.experiments.sensor_v2.train_v2_models import train_v2_candidate


def run_all() -> None:
    print("================================================================================")
    print("STARTING POLARIX SENSOR ML V2 RETRAINING & EVALUATION EXPERIMENT")
    print("================================================================================")

    # 1. Train candidates
    train_v2_candidate(MAITRI_V2_CONFIG)
    train_v2_candidate(BHARATI_V2_CONFIG)

    # 2. Evaluate & calibrate thresholds
    run_full_v2_evaluation_suite()

    print("\n================================================================================")
    print("SENSOR ML V2 EXPERIMENT RUN COMPLETE")
    print("================================================================================")


if __name__ == "__main__":
    run_all()
