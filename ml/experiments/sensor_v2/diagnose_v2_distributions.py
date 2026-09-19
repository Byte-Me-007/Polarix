"""
Reconstruction Error Distribution Diagnostics for Sensor ML V2 (Polarix SIH26060 - Person C).

Computes comprehensive statistical distributions (mean, median, std, percentiles)
per sensor and per anomaly type on validation and held-out test splits for both
Maitri and Bharati stations.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import numpy as np
import pandas as pd


def compute_normal_stats(values: np.ndarray) -> Dict[str, Any]:
    """Calculate statistical distribution for normal reconstruction errors."""
    if len(values) == 0:
        return {
            "count": 0,
            "mean": 0.0,
            "median": 0.0,
            "std": 0.0,
            "p90": 0.0,
            "p95": 0.0,
            "p99": 0.0,
            "max": 0.0,
        }
    return {
        "count": int(len(values)),
        "mean": float(np.mean(values)),
        "median": float(np.median(values)),
        "std": float(np.std(values)),
        "p90": float(np.percentile(values, 90)),
        "p95": float(np.percentile(values, 95)),
        "p99": float(np.percentile(values, 99)),
        "max": float(np.max(values)),
    }


def compute_anomaly_stats(values: np.ndarray) -> Dict[str, Any]:
    """Calculate statistical distribution for anomalous reconstruction errors."""
    if len(values) == 0:
        return {
            "count": 0,
            "mean": 0.0,
            "median": 0.0,
            "std": 0.0,
            "p10": 0.0,
            "p25": 0.0,
            "p50": 0.0,
            "p75": 0.0,
            "p90": 0.0,
        }
    return {
        "count": int(len(values)),
        "mean": float(np.mean(values)),
        "median": float(np.median(values)),
        "std": float(np.std(values)),
        "p10": float(np.percentile(values, 10)),
        "p25": float(np.percentile(values, 25)),
        "p50": float(np.percentile(values, 50)),
        "p75": float(np.percentile(values, 75)),
        "p90": float(np.percentile(values, 90)),
    }


def analyze_station_distributions(errors_csv: Path, station_id: str) -> Dict[str, Any]:
    """Compute complete error distributions for a given station's V2 reconstruction errors."""
    df = pd.read_csv(errors_csv)

    station_results: Dict[str, Any] = {
        "station_id": station_id,
        "splits": {},
    }

    for split_name in ["val", "test"]:
        split_df = df[df["split"] == split_name].copy()
        if len(split_df) == 0:
            continue

        per_sensor_stats: Dict[str, Any] = {}
        for sensor_id, s_df in split_df.groupby("sensor_id"):
            norm_mask = s_df["is_anomaly"] == 0
            anom_mask = s_df["is_anomaly"] == 1

            norm_errors = s_df.loc[norm_mask, "reconstruction_error"].to_numpy(dtype=float)
            anom_errors = s_df.loc[anom_mask, "reconstruction_error"].to_numpy(dtype=float)

            # Per Anomaly Type stats
            type_stats: Dict[str, Any] = {}
            for a_type in ["SPIKE", "DRIFT", "STUCK_VALUE", "DROPOUT"]:
                type_mask = (s_df["anomaly_type"] == a_type) | (
                    (a_type == "DROPOUT") & (s_df["anomaly_type"].isin(["DROPOUT", "MISSING_DATA"]))
                )
                t_errors = s_df.loc[type_mask, "reconstruction_error"].to_numpy(dtype=float)
                type_stats[a_type] = compute_anomaly_stats(t_errors)

            per_sensor_stats[sensor_id] = {
                "sensor_id": sensor_id,
                "normal": compute_normal_stats(norm_errors),
                "anomalous": compute_anomaly_stats(anom_errors),
                "by_anomaly_type": type_stats,
            }

        # Global station-wide stats across all sensors in split
        global_norm = split_df.loc[split_df["is_anomaly"] == 0, "reconstruction_error"].to_numpy(dtype=float)
        global_anom = split_df.loc[split_df["is_anomaly"] == 1, "reconstruction_error"].to_numpy(dtype=float)

        station_results["splits"][split_name] = {
            "global_normal": compute_normal_stats(global_norm),
            "global_anomalous": compute_anomaly_stats(global_anom),
            "sensors": per_sensor_stats,
        }

    return station_results


def run_diagnostics() -> Dict[str, Any]:
    """Run full diagnostic analysis and generate reports."""
    results_dir = REPO_ROOT / "ml" / "experiments" / "sensor_v2" / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    mtr_csv = results_dir / "mtr_v2_reconstruction_errors.csv"
    brt_csv = results_dir / "brt_v2_reconstruction_errors.csv"

    mtr_diag = analyze_station_distributions(mtr_csv, "MTR")
    brt_diag = analyze_station_distributions(brt_csv, "BRT")

    diagnostics = {
        "timestamp_utc": pd.Timestamp.now("UTC").isoformat(),
        "description": "Reconstruction Error Distribution Diagnostics for Sensor ML V2",
        "stations": {
            "MTR": mtr_diag,
            "BRT": brt_diag,
        },
    }

    # Save JSON artifact
    json_path = results_dir / "reconstruction_error_diagnostics.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(diagnostics, f, indent=2)
    print(f"[Diagnostics] Saved JSON artifact: {json_path.relative_to(REPO_ROOT)}")

    # Save Markdown report
    md_path = results_dir / "reconstruction_error_diagnostics.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# Sensor ML V2 Reconstruction Error Distribution Diagnostics\n\n")
        f.write("**Project:** Polarix SIH26060 — Person C (ML Specialist)  \n")
        f.write("**Status:** `DIAGNOSTIC_EVIDENCE_CAPTURED`  \n\n")
        f.write("---\n\n")

        for s_key in ["MTR", "BRT"]:
            st = diagnostics["stations"][s_key]
            f.write(f"## Station: `{st['station_id']}`\n\n")

            for split_name in ["val", "test"]:
                split_data = st["splits"].get(split_name, {})
                f.write(f"### Split: `{split_name.upper()}`\n\n")

                # Global summary
                gn = split_data.get("global_normal", {})
                ga = split_data.get("global_anomalous", {})
                f.write(f"- **Overall Normal (N={gn.get('count', 0)}):** Mean={gn.get('mean', 0):.6f}, Median={gn.get('median', 0):.6f}, P95={gn.get('p95', 0):.6f}, Max={gn.get('max', 0):.6f}\n")
                f.write(f"- **Overall Anomalous (N={ga.get('count', 0)}):** Mean={ga.get('mean', 0):.6f}, Median={ga.get('median', 0):.6f}, P10={ga.get('p10', 0):.6f}, P90={ga.get('p90', 0):.6f}\n\n")

                f.write("#### Per-Sensor Breakdown:\n\n")
                f.write("| Sensor ID | Normal Count | Normal Median | Normal P95 | Anomaly Count | Anomaly Median | Anomaly P10 | Overlap / Separation |\n")
                f.write("| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |\n")

                for sensor_id, s_info in split_data.get("sensors", {}).items():
                    n_stat = s_info["normal"]
                    a_stat = s_info["anomalous"]
                    n_med = n_stat["median"]
                    n_p95 = n_stat["p95"]
                    a_med = a_stat["median"]
                    a_p10 = a_stat["p10"]

                    if a_stat["count"] == 0:
                        sep = "No Anomaly Samples"
                    elif a_p10 > n_p95:
                        sep = "✅ Clean Separation"
                    elif a_med > n_med:
                        sep = "⚠️ Moderate Overlap"
                    else:
                        sep = "❌ Heavy Overlap / Inverted"

                    f.write(
                        f"| `{sensor_id}` | {n_stat['count']} | {n_med:.6f} | {n_p95:.6f} | {a_stat['count']} | {a_med:.6f} | {a_p10:.6f} | {sep} |\n"
                    )
                f.write("\n")

        f.write("---\n\n")
        f.write("## Key Diagnostic Takeaways\n\n")
        f.write("1. **Sensor Disparity:** Sensors exhibit widely varying baseline normal reconstruction errors (e.g. Vibration vs Humidity vs Pressure), demonstrating why a single global threshold causes severe false alarms on noisy channels while missing anomalies on low-variance channels.\n")
        f.write("2. **Distribution Overlap:** Diurnal sensor variations naturally produce elevated normal MSE, causing significant overlap between normal tails and subtle anomaly distributions (like Drift and Stuck Value).\n")

    print(f"[Diagnostics] Saved Markdown report: {md_path.relative_to(REPO_ROOT)}")
    return diagnostics


if __name__ == "__main__":
    run_diagnostics()
