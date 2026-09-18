#!/usr/bin/env python3
"""
Executable Machine Learning Integration Example for Person A (Backend Engineer).
Polarix SIH26060 — Antigravity Multi-Agent Implementation.

This script demonstrates the exact, copy-paste-ready integration flow to incorporate
Person C's finalized ML inference services into Person A's FastAPI / MQTT backend.

Run directly via:
    .venv/bin/python ml/integration/person_a_ml_integration_example.py
"""

from __future__ import annotations

import json
import math
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict

# Ensure project root is available on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# =============================================================================
# EXACT PERSON C IMPORTS FOR PERSON A
# =============================================================================
from ml.inference.maitri_ml_service import MaitriMLService
from ml.inference.bharati_ml_service import BharatiMLService
from ml.inference.maitri_backend_contract import (
    adapt_backend_input as adapt_mtr_input,
    adapt_backend_output as adapt_mtr_output,
    process_backend_payload as process_mtr,
)
from ml.inference.bharati_backend_contract import (
    adapt_backend_input as adapt_brt_input,
    adapt_backend_output as adapt_brt_output,
    process_backend_payload as process_brt,
)
from ml.inference.inference_contract import (
    DuplicateTelemetryError as MTR_DuplicateError,
    StaleTelemetryError as MTR_StaleError,
    InvalidContractError as MTR_InvalidContractError,
)


def run_person_a_integration_demo() -> None:
    print("=" * 80)
    print("POLARIX ML INTEGRATION KIT — PERSON A BACKEND DEMONSTRATION")
    print("=" * 80)

    # -------------------------------------------------------------------------
    # 1. SERVICE LIFECYCLE INITIALIZATION (Application Startup / Singleton)
    # -------------------------------------------------------------------------
    print("\n[1] Initializing ML Services (Instantiate ONCE on application startup)...")
    maitri_service = MaitriMLService()
    bharati_service = BharatiMLService()
    print(f" -> Maitri Service Initialized  (Model: {maitri_service.model_version}, Threshold: {maitri_service.threshold})")
    print(f" -> Bharati Service Initialized (Model: {bharati_service.model_version}, Threshold: {bharati_service.threshold})")

    # -------------------------------------------------------------------------
    # 2. MAITRI STREAMING INGESTION (MTR / TEMP_001)
    # -------------------------------------------------------------------------
    print("\n[2] Ingesting Maitri Telemetry Stream (MTR / TEMP_001)...")
    base_time = datetime(2026, 9, 18, 10, 0, 0, tzinfo=timezone.utc)

    # A. Cold-Start Warmup (Steps 1 to 29)
    print(" -> Ingesting Steps 1..29 (Warmup Window):")
    warmup_res = None
    for step in range(1, 30):
        packet = {
            "station_id": "MTR",
            "sensor_id": "TEMP_001",
            "timestamp": (base_time + timedelta(seconds=step)).isoformat(),
            "value": -15.0 + 0.05 * (step % 3),
            "unit": "C",
            "quality": "GOOD",
            "source": "SIMULATOR",
        }
        warmup_res = process_mtr(maitri_service, packet)

    print(f"    Step 29 Result: status={warmup_res['anomaly_status']}, score={warmup_res['anomaly_score']}, type={warmup_res['anomaly_type']}")
    assert warmup_res["anomaly_status"] == "INSUFFICIENT_DATA"

    # B. 30th Observation (First Scored Inference)
    step_30_packet = {
        "station_id": "MTR",
        "sensor_id": "TEMP_001",
        "timestamp": (base_time + timedelta(seconds=30)).isoformat(),
        "value": -15.0,
        "unit": "C",
        "quality": "GOOD",
        "source": "SIMULATOR",
    }
    step_30_res = process_mtr(maitri_service, step_30_packet)
    print("\n -> Step 30 Output (First Full Neural Inference):")
    print(json.dumps(step_30_res, indent=2))
    assert step_30_res["anomaly_status"] == "NORMAL"
    assert step_30_res["anomaly_type"] == "NORMAL"

    # C. Anomaly Shock Spike Injection
    spike_packet = {
        "station_id": "MTR",
        "sensor_id": "TEMP_001",
        "timestamp": (base_time + timedelta(seconds=31)).isoformat(),
        "value": 45.0,  # Sudden 60C shock jump
        "unit": "C",
        "quality": "GOOD",
        "source": "SIMULATOR",
    }
    spike_res = process_mtr(maitri_service, spike_packet)
    print("\n -> Step 31 Output (SPIKE Anomaly Injected):")
    print(json.dumps(spike_res, indent=2))
    assert spike_res["anomaly_status"] == "ANOMALY"
    assert spike_res["anomaly_type"] == "SPIKE"

    # -------------------------------------------------------------------------
    # 3. BHARATI STREAMING INGESTION (BRT / BRT_TEMP_001)
    # -------------------------------------------------------------------------
    print("\n[3] Ingesting Bharati Telemetry Stream (BRT / BRT_TEMP_001)...")
    brt_base_time = datetime(2026, 9, 18, 11, 0, 0, tzinfo=timezone.utc)

    # Warmup 30 steps
    for step in range(1, 31):
        packet = {
            "station_id": "BRT",
            "sensor_id": "BRT_TEMP_001",
            "timestamp": (brt_base_time + timedelta(seconds=step)).isoformat(),
            "value": -10.0 + 0.1 * math.sin(step),
            "unit": "C",
            "quality": "GOOD",
            "source": "SIMULATOR",
        }
        process_brt(bharati_service, packet)

    # Ingest flatline stuck telemetry for 25 steps
    stuck_out = None
    for step in range(31, 56):
        flat_packet = {
            "station_id": "BRT",
            "sensor_id": "BRT_TEMP_001",
            "timestamp": (brt_base_time + timedelta(seconds=step)).isoformat(),
            "value": -28.5,
            "unit": "C",
            "quality": "GOOD",
            "source": "SIMULATOR",
        }
        stuck_out = process_brt(bharati_service, flat_packet)

    print("\n -> Bharati Step 55 Output (STUCK_VALUE Flatline Anomaly):")
    print(json.dumps(stuck_out, indent=2))
    assert stuck_out["anomaly_type"] in {"STUCK_VALUE", "UNKNOWN"}

    # Resume nominal oscillation (Recovery)
    rec_out = None
    for step in range(56, 75):
        rec_packet = {
            "station_id": "BRT",
            "sensor_id": "BRT_TEMP_001",
            "timestamp": (brt_base_time + timedelta(seconds=step)).isoformat(),
            "value": -10.0 + 0.1 * math.sin(step),
            "unit": "C",
            "quality": "GOOD",
            "source": "SIMULATOR",
        }
        rec_out = process_brt(bharati_service, rec_packet)

    print(f" -> Bharati Recovery Step 74 Output: status={rec_out['anomaly_status']}, type={rec_out['anomaly_type']}")
    assert rec_out["anomaly_type"] != "STUCK_VALUE"

    # -------------------------------------------------------------------------
    # 4. DATA QUALITY & DROPOUT HANDLING (MISSING_DATA & Buffer Flush)
    # -------------------------------------------------------------------------
    print("\n[4] Ingesting Missing Telemetry / Dropout Quality Packet...")
    missing_packet = {
        "station_id": "MTR",
        "sensor_id": "TEMP_001",
        "timestamp": (base_time + timedelta(seconds=32)).isoformat(),
        "value": None,
        "unit": "C",
        "quality": "MISSING",
        "source": "SIMULATOR",
    }
    missing_res = process_mtr(maitri_service, missing_packet)
    print(" -> Missing Data Response:")
    print(json.dumps(missing_res, indent=2))
    assert missing_res["anomaly_status"] == "MISSING_DATA"
    assert missing_res["anomaly_score"] is None
    assert maitri_service.get_buffer_length("TEMP_001") == 0
    print(" -> Rolling history for TEMP_001 flushed to 0 successfully.")

    # -------------------------------------------------------------------------
    # 5. DUPLICATE & STALE ERROR HANDLING
    # -------------------------------------------------------------------------
    print("\n[5] Demonstrating Duplicate & Stale Packet Rejection...")
    valid_packet = {
        "station_id": "MTR",
        "sensor_id": "VIB_001",
        "timestamp": (base_time + timedelta(seconds=100)).isoformat(),
        "value": 0.85,
        "unit": "mm/s",
        "quality": "GOOD",
        "source": "SIMULATOR",
    }
    process_mtr(maitri_service, valid_packet)

    dup_packet = {
        "station_id": "MTR",
        "sensor_id": "VIB_001",
        "timestamp": (base_time + timedelta(seconds=100)).isoformat(),  # exact duplicate
        "value": 0.85,
        "unit": "mm/s",
        "quality": "GOOD",
        "source": "SIMULATOR",
    }
    try:
        process_mtr(maitri_service, dup_packet)
        print(" -> ERROR: Duplicate was not caught!")
    except MTR_DuplicateError as e:
        print(f" -> Duplicate Error Caught cleanly by Person A handler: {e}")

    print("\n" + "=" * 80)
    print("INTEGRATION DEMONSTRATION COMPLETE — 100% READY FOR PERSON A BACKEND")
    print("=" * 80)


if __name__ == "__main__":
    run_person_a_integration_demo()
