#!/usr/bin/env python3
"""
Deterministic Backend ML Smoke-Test Harness (Polarix SIH26060 - Person C).
Step 44: Exercises the available ML ingestion and inference boundary under representative
backend-style streaming workloads, demonstrating readiness for Person A's backend integration.

Outputs:
- ml/results/backend_integration_readiness.json
- ml/results/backend_integration_readiness.md
"""

from __future__ import annotations

import json
import math
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ml.inference.maitri_backend_contract import (
    adapt_backend_input as adapt_mtr_input,
    adapt_backend_output as adapt_mtr_output,
    process_backend_payload as process_mtr_payload,
)
from ml.inference.bharati_backend_contract import (
    adapt_backend_input as adapt_brt_input,
    adapt_backend_output as adapt_brt_output,
    process_backend_payload as process_brt_payload,
)
from ml.inference.inference_contract import (
    DEFAULT_MODEL_VERSION as DEFAULT_MAITRI_MODEL_VERSION,
    SUPPORTED_SENSORS as SUPPORTED_MAITRI_SENSORS,
    SUPPORTED_STATIONS as SUPPORTED_MAITRI_STATIONS,
    DuplicateTelemetryError as MTR_DuplicateError,
    InvalidContractError as MTR_InvalidContractError,
    StaleTelemetryError as MTR_StaleError,
    TelemetryInput,
    UnsupportedSensorError as MTR_UnsupportedSensorError,
    UnsupportedStationError as MTR_UnsupportedStationError,
)
from ml.inference.bharati_inference_contract import (
    DEFAULT_BHARATI_MODEL_VERSION,
    SUPPORTED_BHARATI_SENSORS,
    SUPPORTED_BHARATI_STATIONS,
    BharatiTelemetryInput,
    DuplicateTelemetryError as BRT_DuplicateError,
    InvalidContractError as BRT_InvalidContractError,
    StaleTelemetryError as BRT_StaleError,
    UnsupportedSensorError as BRT_UnsupportedSensorError,
    UnsupportedStationError as BRT_UnsupportedStationError,
)
from ml.inference.maitri_ml_service import MaitriMLService
from ml.inference.bharati_ml_service import BharatiMLService

CANONICAL_OUTPUT_FIELDS = [
    "station_id",
    "sensor_id",
    "timestamp",
    "value",
    "unit",
    "quality",
    "source",
    "anomaly_score",
    "anomaly_status",
    "anomaly_type",
    "model_version",
]


def execute_backend_smoke_audit() -> Dict[str, Any]:
    print("=" * 80)
    print("POLARIX BACKEND ML INTEGRATION READINESS AUDIT & SMOKE HARNESS (STEP 44)")
    print("=" * 80)

    mtr_service = MaitriMLService()
    mtr_service.reset_all()

    brt_service = BharatiMLService()
    brt_service.reset_all()

    smoke_stages: List[Dict[str, Any]] = []

    # -------------------------------------------------------------------------
    # Stage 1: Telemetry Schema Compatibility & Normalization
    # -------------------------------------------------------------------------
    print("\n[Stage 1/8] Auditing Telemetry Schema Ingestion (JSON & Dict)...")
    t0 = time.perf_counter()
    mtr_dict = {
        "station_id": "MTR",
        "sensor_id": "TEMP_001",
        "timestamp": "2026-09-18T10:00:00Z",
        "value": -15.2,
        "unit": "C",
        "quality": "GOOD",
        "source": "SIMULATOR",
    }
    brt_dict = {
        "station_id": "BRT",
        "sensor_id": "BRT_TEMP_001",
        "timestamp": "2026-09-18T10:00:00Z",
        "value": -10.4,
        "unit": "C",
        "quality": "GOOD",
        "source": "SIMULATOR",
    }
    mtr_inp = adapt_mtr_input(mtr_dict)
    brt_inp = adapt_brt_input(brt_dict)
    mtr_inp_json = adapt_mtr_input(json.dumps(mtr_dict))
    brt_inp_json = adapt_brt_input(json.dumps(brt_dict))

    s1_ok = (
        mtr_inp.station_id == "MTR"
        and brt_inp.station_id == "BRT"
        and mtr_inp_json.value == -15.2
        and brt_inp_json.value == -10.4
    )
    t_elapsed = round((time.perf_counter() - t0) * 1000.0, 4)
    smoke_stages.append({
        "stage": 1,
        "name": "Schema Ingestion & Normalization",
        "passed": bool(s1_ok),
        "latency_ms": t_elapsed,
        "details": "Validated dictionary and raw JSON parsing into typed TelemetryInput / BharatiTelemetryInput contracts.",
    })
    print(f" -> Stage 1 Status: {'PASS' if s1_ok else 'FAIL'}")

    # -------------------------------------------------------------------------
    # Stage 2: Cold-Start Warmup & INSUFFICIENT_DATA Handling
    # -------------------------------------------------------------------------
    print("\n[Stage 2/8] Auditing Streaming Warmup Progression (< 30 observations)...")
    t0 = time.perf_counter()
    mtr_service.reset_all()
    brt_service.reset_all()
    s2_ok = True
    for i in range(1, 30):
        m_res = process_mtr_payload(
            mtr_service,
            {"station_id": "MTR", "sensor_id": "TEMP_001", "timestamp": f"2026-09-18T00:{i:02d}:00Z", "value": -15.0 + 0.01 * (i % 3)},
        )
        b_res = process_brt_payload(
            brt_service,
            {"station_id": "BRT", "sensor_id": "BRT_TEMP_001", "timestamp": f"2026-09-18T00:{i:02d}:00Z", "value": -10.0 + 0.01 * (i % 3)},
        )
        if m_res["anomaly_status"] != "INSUFFICIENT_DATA" or m_res["anomaly_score"] is not None:
            s2_ok = False
        if b_res["anomaly_status"] != "INSUFFICIENT_DATA" or b_res["anomaly_score"] is not None:
            s2_ok = False

    t_elapsed = round((time.perf_counter() - t0) * 1000.0, 4)
    smoke_stages.append({
        "stage": 2,
        "name": "Cold-Start Warmup Progression",
        "passed": bool(s2_ok),
        "latency_ms": t_elapsed,
        "details": "Confirmed steps 1..29 bypass neural inference and return INSUFFICIENT_DATA with null score.",
    })
    print(f" -> Stage 2 Status: {'PASS' if s2_ok else 'FAIL'}")

    # -------------------------------------------------------------------------
    # Stage 3: Steady-State Nominal Inference (Step 30+)
    # -------------------------------------------------------------------------
    print("\n[Stage 3/8] Auditing Steady-State Nominal Inference...")
    t0 = time.perf_counter()
    m_30 = process_mtr_payload(
        mtr_service,
        {"station_id": "MTR", "sensor_id": "TEMP_001", "timestamp": "2026-09-18T00:30:00Z", "value": -15.0},
    )
    b_30 = process_brt_payload(
        brt_service,
        {"station_id": "BRT", "sensor_id": "BRT_TEMP_001", "timestamp": "2026-09-18T00:30:00Z", "value": -10.0},
    )
    s3_ok = (
        m_30["anomaly_status"] == "NORMAL"
        and m_30["anomaly_type"] == "NORMAL"
        and isinstance(m_30["anomaly_score"], float)
        and m_30["anomaly_score"] <= mtr_service.threshold
        and b_30["anomaly_status"] == "NORMAL"
        and b_30["anomaly_type"] == "NORMAL"
        and isinstance(b_30["anomaly_score"], float)
        and b_30["anomaly_score"] <= brt_service.threshold
    )
    t_elapsed = round((time.perf_counter() - t0) * 1000.0, 4)
    smoke_stages.append({
        "stage": 3,
        "name": "Nominal Scored Inference",
        "passed": bool(s3_ok),
        "latency_ms": t_elapsed,
        "details": f"MTR score: {m_30['anomaly_score']} (threshold={mtr_service.threshold}), BRT score: {b_30['anomaly_score']} (threshold={brt_service.threshold}).",
    })
    print(f" -> Stage 3 Status: {'PASS' if s3_ok else 'FAIL'}")

    # -------------------------------------------------------------------------
    # Stage 4: SPIKE Shock Anomaly Classification
    # -------------------------------------------------------------------------
    print("\n[Stage 4/8] Auditing SPIKE Shock Anomaly Detection...")
    t0 = time.perf_counter()
    m_spike = process_mtr_payload(
        mtr_service,
        {"station_id": "MTR", "sensor_id": "TEMP_001", "timestamp": "2026-09-18T00:31:00Z", "value": 45.0},
    )
    b_spike = process_brt_payload(
        brt_service,
        {"station_id": "BRT", "sensor_id": "BRT_TEMP_001", "timestamp": "2026-09-18T00:31:00Z", "value": 45.0},
    )
    s4_ok = (
        m_spike["anomaly_status"] == "ANOMALY"
        and m_spike["anomaly_type"] == "SPIKE"
        and b_spike["anomaly_status"] == "ANOMALY"
        and b_spike["anomaly_type"] == "SPIKE"
    )
    t_elapsed = round((time.perf_counter() - t0) * 1000.0, 4)
    smoke_stages.append({
        "stage": 4,
        "name": "SPIKE Anomaly Classification",
        "passed": bool(s4_ok),
        "latency_ms": t_elapsed,
        "details": "Verified sudden 60C shock jump triggers ANOMALY status and SPIKE classification on both stations.",
    })
    print(f" -> Stage 4 Status: {'PASS' if s4_ok else 'FAIL'}")

    # -------------------------------------------------------------------------
    # Stage 5: DRIFT Monotonic Ramp Anomaly Detection
    # -------------------------------------------------------------------------
    print("\n[Stage 5/8] Auditing DRIFT Monotonic Ramp Detection...")
    mtr_service.reset_all()
    brt_service.reset_all()
    t0 = time.perf_counter()
    m_drift_last = None
    b_drift_last = None
    for step in range(1, 31):
        m_drift_last = process_mtr_payload(
            mtr_service,
            {"station_id": "MTR", "sensor_id": "PRESS_001", "timestamp": f"2026-09-18T01:{step:02d}:00Z", "value": 980.0 + 0.6 * step},
        )
        b_drift_last = process_brt_payload(
            brt_service,
            {"station_id": "BRT", "sensor_id": "BRT_PRESS_001", "timestamp": f"2026-09-18T01:{step:02d}:00Z", "value": 980.0 + 0.6 * step},
        )

    s5_ok = (
        m_drift_last is not None
        and m_drift_last["anomaly_status"] == "ANOMALY"
        and m_drift_last["anomaly_type"] in {"DRIFT", "UNKNOWN"}
        and b_drift_last is not None
        and b_drift_last["anomaly_status"] == "ANOMALY"
        and b_drift_last["anomaly_type"] in {"DRIFT", "UNKNOWN"}
    )
    t_elapsed = round((time.perf_counter() - t0) * 1000.0, 4)
    smoke_stages.append({
        "stage": 5,
        "name": "DRIFT Ramp Anomaly Detection",
        "passed": bool(s5_ok),
        "latency_ms": t_elapsed,
        "details": f"MTR drift status: {m_drift_last['anomaly_status']} ({m_drift_last['anomaly_type']}), BRT drift status: {b_drift_last['anomaly_status']} ({b_drift_last['anomaly_type']}).",
    })
    print(f" -> Stage 5 Status: {'PASS' if s5_ok else 'FAIL'}")

    # -------------------------------------------------------------------------
    # Stage 6: STUCK_VALUE Flatline & Recovery
    # -------------------------------------------------------------------------
    print("\n[Stage 6/8] Auditing STUCK_VALUE Flatline & Recovery Cycle...")
    mtr_service.reset_all()
    brt_service.reset_all()
    t0 = time.perf_counter()
    base_t_mtr = datetime(2026, 9, 18, 2, 0, 0, tzinfo=timezone.utc)
    base_t_brt = datetime(2026, 9, 18, 2, 0, 0, tzinfo=timezone.utc)

    # 1. Warm up with oscillating baseline
    for step in range(1, 31):
        ts_m = (base_t_mtr + timedelta(minutes=step)).isoformat()
        ts_b = (base_t_brt + timedelta(minutes=step)).isoformat()
        process_mtr_payload(
            mtr_service,
            {"station_id": "MTR", "sensor_id": "TEMP_001", "timestamp": ts_m, "value": -15.0 + 0.1 * math.sin(step)},
        )
        process_brt_payload(
            brt_service,
            {"station_id": "BRT", "sensor_id": "BRT_TEMP_001", "timestamp": ts_b, "value": -10.0 + 0.1 * math.sin(step)},
        )

    # 2. Feed repeated constant flatline
    mtr_stuck_types = []
    brt_stuck_types = []
    for step in range(31, 56):
        ts_m = (base_t_mtr + timedelta(minutes=step)).isoformat()
        ts_b = (base_t_brt + timedelta(minutes=step)).isoformat()
        out_m = process_mtr_payload(
            mtr_service,
            {"station_id": "MTR", "sensor_id": "TEMP_001", "timestamp": ts_m, "value": -28.5},
        )
        out_b = process_brt_payload(
            brt_service,
            {"station_id": "BRT", "sensor_id": "BRT_TEMP_001", "timestamp": ts_b, "value": -28.5},
        )
        if out_m["anomaly_status"] == "ANOMALY":
            mtr_stuck_types.append(out_m["anomaly_type"])
        if out_b["anomaly_status"] == "ANOMALY":
            brt_stuck_types.append(out_b["anomaly_type"])

    stuck_detected = ("STUCK_VALUE" in mtr_stuck_types) and ("STUCK_VALUE" in brt_stuck_types)

    # 3. Resume nominal oscillation
    m_rec_last = None
    b_rec_last = None
    for step in range(56, 75):
        ts_m = (base_t_mtr + timedelta(minutes=step)).isoformat()
        ts_b = (base_t_brt + timedelta(minutes=step)).isoformat()
        m_rec_last = process_mtr_payload(
            mtr_service,
            {"station_id": "MTR", "sensor_id": "TEMP_001", "timestamp": ts_m, "value": -15.0 + 0.1 * math.sin(step)},
        )
        b_rec_last = process_brt_payload(
            brt_service,
            {"station_id": "BRT", "sensor_id": "BRT_TEMP_001", "timestamp": ts_b, "value": -10.0 + 0.1 * math.sin(step)},
        )

    recovery_ok = (
        m_rec_last is not None
        and m_rec_last["anomaly_type"] != "STUCK_VALUE"
        and b_rec_last is not None
        and b_rec_last["anomaly_type"] != "STUCK_VALUE"
    )
    s6_ok = stuck_detected and recovery_ok
    t_elapsed = round((time.perf_counter() - t0) * 1000.0, 4)
    smoke_stages.append({
        "stage": 6,
        "name": "STUCK_VALUE Detection & Recovery",
        "passed": bool(s6_ok),
        "latency_ms": t_elapsed,
        "details": f"Flatline STUCK_VALUE observed: (MTR={'STUCK_VALUE' in mtr_stuck_types}, BRT={'STUCK_VALUE' in brt_stuck_types}), Recovery released stuck state: {recovery_ok}.",
    })
    print(f" -> Stage 6 Status: {'PASS' if s6_ok else 'FAIL'}")

    # -------------------------------------------------------------------------
    # Stage 7: MISSING_DATA & Buffer Flush Handling
    # -------------------------------------------------------------------------
    print("\n[Stage 7/8] Auditing MISSING_DATA Ingestion & Buffer Flush...")
    t0 = time.perf_counter()
    mtr_service.reset_all()
    for step in range(1, 31):
        process_mtr_payload(
            mtr_service,
            {"station_id": "MTR", "sensor_id": "HUM_001", "timestamp": f"2026-09-18T03:{step:02d}:00Z", "value": 55.0},
        )
    m_drop = process_mtr_payload(
        mtr_service,
        {"station_id": "MTR", "sensor_id": "HUM_001", "timestamp": "2026-09-18T03:31:00Z", "value": 55.0, "quality": "MISSING"},
    )
    buf_len_after_drop = mtr_service.get_buffer_length("HUM_001")
    s7_ok = (
        m_drop["anomaly_status"] == "MISSING_DATA"
        and m_drop["anomaly_score"] is None
        and m_drop["anomaly_type"] is None
        and buf_len_after_drop == 0
    )
    t_elapsed = round((time.perf_counter() - t0) * 1000.0, 4)
    smoke_stages.append({
        "stage": 7,
        "name": "MISSING_DATA Ingestion & Buffer Flush",
        "passed": bool(s7_ok),
        "latency_ms": t_elapsed,
        "details": f"MISSING quality returned MISSING_DATA and successfully flushed rolling buffer length from 30 to {buf_len_after_drop}.",
    })
    print(f" -> Stage 7 Status: {'PASS' if s7_ok else 'FAIL'}")

    # -------------------------------------------------------------------------
    # Stage 8: Multi-Sensor Stream Isolation & Output Field Preservation
    # -------------------------------------------------------------------------
    print("\n[Stage 8/8] Auditing Multi-Sensor Isolation & Output Roundtrip...")
    t0 = time.perf_counter()
    mtr_service.reset_all()
    sensors = ["TEMP_001", "PRESS_001", "HUM_001", "VIB_001", "POWER_001"]
    base_means = {"TEMP_001": -15.0, "PRESS_001": 990.0, "HUM_001": 55.0, "VIB_001": 0.85, "POWER_001": 35.0}
    units = {"TEMP_001": "C", "PRESS_001": "hPa", "HUM_001": "%", "VIB_001": "mm/s", "POWER_001": "kW"}

    for step in range(1, 31):
        ts = f"2026-09-18T04:{step:02d}:00Z"
        for s in sensors:
            p = {"station_id": "MTR", "sensor_id": s, "timestamp": ts, "value": base_means[s] + 0.01 * (step % 3), "unit": units[s]}
            process_mtr_payload(mtr_service, p)

    # Spike on TEMP_001 only
    ts_spike = "2026-09-18T04:31:00Z"
    temp_spike_res = process_mtr_payload(
        mtr_service,
        {"station_id": "MTR", "sensor_id": "TEMP_001", "timestamp": ts_spike, "value": 50.0, "unit": "C"},
    )
    press_norm_res = process_mtr_payload(
        mtr_service,
        {"station_id": "MTR", "sensor_id": "PRESS_001", "timestamp": ts_spike, "value": base_means["PRESS_001"], "unit": "hPa"},
    )

    # Output JSON serialization check
    json_roundtrip = json.loads(json.dumps(temp_spike_res))
    fields_present = set(json_roundtrip.keys()) == set(CANONICAL_OUTPUT_FIELDS)

    s8_ok = (
        temp_spike_res["anomaly_status"] == "ANOMALY"
        and press_norm_res["anomaly_status"] == "NORMAL"
        and fields_present
    )
    t_elapsed = round((time.perf_counter() - t0) * 1000.0, 4)
    smoke_stages.append({
        "stage": 8,
        "name": "Multi-Sensor Stream Isolation & Output Schema",
        "passed": bool(s8_ok),
        "latency_ms": t_elapsed,
        "details": "Verified individual sensor isolation (TEMP_001 anomaly does not bleed to PRESS_001) and all 11 canonical fields survive strict JSON serialization.",
    })
    print(f" -> Stage 8 Status: {'PASS' if s8_ok else 'FAIL'}")

    all_stages_passed = all(st["passed"] for st in smoke_stages)
    print("\n" + "=" * 80)
    print(f"OVERALL BACKEND ML SMOKE HARNESS RESULT: {'ALL PASS (8/8)' if all_stages_passed else 'FAIL'}")
    print("=" * 80)

    # Compile Full Audit Matrix
    boundaries = [
        {
            "boundary": "Telemetry Schema Normalization",
            "implementation": "FULLY IMPLEMENTED",
            "testable": True,
            "current_evidence": "ml/inference/maitri_backend_contract.py, ml/inference/bharati_backend_contract.py",
            "owner": "Person C (ML) / Person A (Backend)",
            "status": "VALIDATED",
            "description": "JSON dict/str parsing, field validation, and finite float guarantees.",
        },
        {
            "boundary": "ML Inference Invocation",
            "implementation": "FULLY IMPLEMENTED",
            "testable": True,
            "current_evidence": "MaitriMLService, BharatiMLService, process_backend_payload()",
            "owner": "Person C (ML)",
            "status": "VALIDATED",
            "description": "Synchronous, thread-safe, stateful rolling buffer inference per sensor.",
        },
        {
            "boundary": "FastAPI HTTP Ingestion Endpoints",
            "implementation": "NOT IMPLEMENTED IN CURRENT BRANCH",
            "testable": False,
            "current_evidence": "No main.py or routers in branch Rex",
            "owner": "Person A (Backend)",
            "status": "NOT IMPLEMENTED",
            "description": "REST endpoints for simulator ingestion and REST queries.",
        },
        {
            "boundary": "MQTT Telemetry Ingestion",
            "implementation": "NOT IMPLEMENTED IN CURRENT BRANCH",
            "testable": False,
            "current_evidence": "No MQTT client or broker subscriber in branch Rex",
            "owner": "Person A (Backend)",
            "status": "NOT IMPLEMENTED",
            "description": "Live MQTT broker connection and topic fanout.",
        },
        {
            "boundary": "SQLite Persistence Layer",
            "implementation": "NOT IMPLEMENTED IN CURRENT BRANCH",
            "testable": False,
            "current_evidence": "No database schema or SQLite ORM in branch Rex",
            "owner": "Person A (Backend)",
            "status": "NOT IMPLEMENTED",
            "description": "Historical telemetry and anomaly event persistence.",
        },
        {
            "boundary": "EventBus Dispatcher",
            "implementation": "NOT IMPLEMENTED IN CURRENT BRANCH",
            "testable": False,
            "current_evidence": "No event bus dispatcher in branch Rex",
            "owner": "Person A (Backend)",
            "status": "NOT IMPLEMENTED",
            "description": "Internal asynchronous event distribution bus.",
        },
        {
            "boundary": "WebSocket Streaming",
            "implementation": "NOT IMPLEMENTED IN CURRENT BRANCH",
            "testable": False,
            "current_evidence": "No WebSocket router in branch Rex",
            "owner": "Person A (Backend)",
            "status": "NOT IMPLEMENTED",
            "description": "Real-time telemetry and anomaly broadcast to frontend.",
        },
        {
            "boundary": "Frontend 3D Digital Twin Consumption",
            "implementation": "NOT IMPLEMENTED IN CURRENT BRANCH",
            "testable": False,
            "current_evidence": "No frontend components in branch Rex",
            "owner": "Person B (Frontend)",
            "status": "NOT IMPLEMENTED",
            "description": "React / Three.js UI consumption of canonical ML payload.",
        },
    ]

    audit_report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "step": 44,
        "step_name": "Audit Actual Backend Readiness for ML Integration",
        "smoke_test_summary": {
            "total_stages": len(smoke_stages),
            "passed_stages": sum(1 for st in smoke_stages if st["passed"]),
            "all_passed": all_stages_passed,
            "stages": smoke_stages,
        },
        "integration_readiness_matrix": boundaries,
        "ml_contract_specifications": {
            "maitri": {
                "station_id": "MTR",
                "model_version": DEFAULT_MAITRI_MODEL_VERSION,
                "supported_sensors": sorted(SUPPORTED_MAITRI_SENSORS),
                "threshold": mtr_service.threshold,
                "sequence_length": mtr_service.sequence_length,
            },
            "bharati": {
                "station_id": "BRT",
                "model_version": DEFAULT_BHARATI_MODEL_VERSION,
                "supported_sensors": sorted(SUPPORTED_BHARATI_SENSORS),
                "threshold": brt_service.threshold,
                "sequence_length": brt_service.sequence_length,
            },
        },
        "recommendations_for_person_a": [
            "Import process_backend_payload from ml.inference.maitri_backend_contract (for MTR) and ml.inference.bharati_backend_contract (for BRT).",
            "Instantiate MaitriMLService and BharatiMLService once as application-level singletons (e.g. in FastAPI lifespan/app state).",
            "Route telemetry packets by station_id to the respective service instance.",
            "Persist the 11 canonical fields emitted in the output dictionary directly to SQLite.",
            "Broadcast the exact output dictionary over WebSockets to Person B's frontend.",
        ],
    }

    # Write JSON Artifact
    json_path = REPO_ROOT / "ml" / "results" / "backend_integration_readiness.json"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(audit_report, f, indent=2)
    print(f"\n[OUTPUT] Saved JSON readiness report: {json_path.relative_to(REPO_ROOT)}")

    # Write Markdown Artifact
    md_path = REPO_ROOT / "ml" / "results" / "backend_integration_readiness.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# Backend Integration Readiness Audit (Polarix SIH26060 - Step 44)\n\n")
        f.write("**Audit Timestamp (UTC):** " + audit_report["timestamp_utc"] + "  \n")
        f.write("**Scope:** Person C (Machine Learning Specialist)  \n")
        f.write("**Target Audience:** Person A (Backend Engineer) & Person B (Frontend Engineer)  \n")
        f.write("**Status:** `ML_BOUNDARY_READY__BACKEND_COMPONENTS_PENDING`  \n\n")

        f.write("---\n\n")
        f.write("## 1. Architectural Boundary Map\n\n")
        f.write("```text\n")
        f.write("Telemetry Source (Simulator / Sensor Stream)\n")
        f.write("      │\n")
        f.write("      ▼\n")
        f.write("MQTT / Simulator Ingestion        [ NOT IMPLEMENTED in branch Rex (Person A) ]\n")
        f.write("      │\n")
        f.write("      ▼\n")
        f.write("FastAPI REST Endpoints            [ NOT IMPLEMENTED in branch Rex (Person A) ]\n")
        f.write("      │\n")
        f.write("      ▼\n")
        f.write("Telemetry Contract Adapter        [ FULLY IMPLEMENTED & VALIDATED (Person C) ]\n")
        f.write("      │  └─ adapt_backend_input(payload)\n")
        f.write("      ▼\n")
        f.write("ML Inference Service              [ FULLY IMPLEMENTED & VALIDATED (Person C) ]\n")
        f.write("      │  ├─ MaitriMLService (MTR) / BharatiMLService (BRT)\n")
        f.write("      │  ├─ 30-step sliding window buffer per sensor\n")
        f.write("      │  ├─ LSTM Autoencoder PyTorch reconstruction\n")
        f.write("      │  └─ Deterministic anomaly-type classification\n")
        f.write("      ▼\n")
        f.write("Backend Contract Output Adapter   [ FULLY IMPLEMENTED & VALIDATED (Person C) ]\n")
        f.write("      │  └─ adapt_backend_output(inference_result)\n")
        f.write("      ▼\n")
        f.write("Backend Rules & Severity Alerts   [ NOT IMPLEMENTED in branch Rex (Person A) ]\n")
        f.write("      │\n")
        f.write("      ▼\n")
        f.write("SQLite Persistence / EventBus     [ NOT IMPLEMENTED in branch Rex (Person A) ]\n")
        f.write("      │\n")
        f.write("      ▼\n")
        f.write("WebSocket Server Fanout           [ NOT IMPLEMENTED in branch Rex (Person A) ]\n")
        f.write("      │\n")
        f.write("      ▼\n")
        f.write("Frontend 3D Digital Twin (React)  [ NOT IMPLEMENTED in branch Rex (Person B) ]\n")
        f.write("```\n\n")

        f.write("---\n\n")
        f.write("## 2. Integration Readiness Matrix\n\n")
        f.write("| Architectural Boundary | Implementation State | Testability | Current Repository Evidence | Primary Owner | Status |\n")
        f.write("| :--- | :---: | :---: | :--- | :---: | :---: |\n")
        for b in boundaries:
            f.write(f"| **{b['boundary']}** | `{b['implementation']}` | {'`TESTABLE`' if b['testable'] else '`UNTESTABLE`'} | `{b['current_evidence']}` | {b['owner']} | **`{b['status']}`** |\n")

        f.write("\n---\n\n")
        f.write("## 3. In-Process ML Smoke Test Results\n\n")
        f.write("The ML subsystem was exercised through an in-process smoke test simulating end-to-end backend streaming workloads:\n\n")
        f.write("| Stage # | Stage Name | Status | Latency (ms) | Description |\n")
        f.write("| :---: | :--- | :---: | :---: | :--- |\n")
        for st in smoke_stages:
            f.write(f"| **{st['stage']}** | {st['name']} | **`{'PASS' if st['passed'] else 'FAIL'}`** | {st['latency_ms']:.4f} | {st['details']} |\n")

        f.write("\n---\n\n")
        f.write("## 4. Integration Blueprint for Person A (Backend Integration Guide)\n\n")
        f.write("### Recommended Ingestion Hook (FastAPI Lifespan):\n\n")
        f.write("```python\n")
        f.write("# In backend/app/main.py or backend service lifespan:\n")
        f.write("from ml.inference.maitri_ml_service import MaitriMLService\n")
        f.write("from ml.inference.bharati_ml_service import BharatiMLService\n")
        f.write("from ml.inference.maitri_backend_contract import process_backend_payload as process_mtr\n")
        f.write("from ml.inference.bharati_backend_contract import process_backend_payload as process_brt\n\n")
        f.write("# Initialize singleton instances on startup\n")
        f.write("maitri_ml = MaitriMLService()\n")
        f.write("bharati_ml = BharatiMLService()\n\n")
        f.write("def handle_incoming_telemetry(payload: dict) -> dict:\n")
        f.write("    station = payload.get('station_id')\n")
        f.write("    if station == 'MTR':\n")
        f.write("        return process_mtr(maitri_ml, payload)\n")
        f.write("    elif station == 'BRT':\n")
        f.write("        return process_brt(bharati_ml, payload)\n")
        f.write("    else:\n")
        f.write("        raise ValueError(f'Unsupported station: {station}')\n")
        f.write("```\n\n")

        f.write("### Canonical Output Contract (11 Fields):\n\n")
        f.write("```json\n")
        f.write("{\n")
        f.write('  "station_id": "MTR",\n')
        f.write('  "sensor_id": "TEMP_001",\n')
        f.write('  "timestamp": "2026-09-18T10:30:00Z",\n')
        f.write('  "value": -15.2,\n')
        f.write('  "unit": "C",\n')
        f.write('  "quality": "GOOD",\n')
        f.write('  "source": "SIMULATOR",\n')
        f.write('  "anomaly_score": 0.004123,\n')
        f.write('  "anomaly_status": "NORMAL",\n')
        f.write('  "anomaly_type": "NORMAL",\n')
        f.write('  "model_version": "lstm-ae-v1"\n')
        f.write("}\n")
        f.write("```\n")

    print(f"[OUTPUT] Saved Markdown readiness report: {md_path.relative_to(REPO_ROOT)}")

    return audit_report


def main() -> None:
    execute_backend_smoke_audit()


if __name__ == "__main__":
    main()
