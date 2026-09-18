# Bharati ML Inference Performance & Latency Benchmark Report

**Polarix Smart India Hackathon 2026 — Team Byte Me_26 (Team ID: 143760)**  
**Person C — ML Specialist Scope (Step 34)**  
**Station**: Bharati (`BRT`)  
**Model Version**: `lstm-ae-bharati-v1`  
**Decision Threshold**: `0.013215307652775843`  
**Evaluation Scope**: **Synthetic / Offline Performance Benchmark Only**

---

## 1. Executive Summary & Objective

Step 34 executes a rigorous quantitative benchmark of the frozen Bharati ML streaming inference service (`BharatiMLService`). 

The objective is to profile inference latency, initialization overhead, short-circuit bypass paths (insufficient/missing telemetry), multi-sensor concurrency handling, diagnostic observability overhead, and memory boundedness under representative synthetic workloads without altering model weights, configuration, threshold, or contract behaviors.

> [!NOTE]
> **Synthetic Workload Disclaimer**: All metrics and latencies reported herein are derived from controlled synthetic telemetry streams running on local evaluation hardware (`macOS-arm64`). They do not represent real Antarctic field operational conditions or certified production SLAs.

---

## 2. Benchmark Environment & Workload Specifications

- **Station**: Bharati (`BRT`)
- **Monitored Sensors (5)**: `BRT_TEMP_001`, `BRT_PRESS_001`, `BRT_HUM_001`, `BRT_VIB_001`, `BRT_POWER_001`
- **Model Architecture**: LSTM Autoencoder (Sequence Length: 30, Hidden Dimension: 32, Bottleneck: 16)
- **Runtime Environment**: Python 3.11.15 | PyTorch CPU Execution
- **Sample Sizes**: 10 Cold-Start Initializations, 200 Scored Invocations per scenario (after 20 warmup cycles)

---

## 3. Quantitative Latency Benchmarks (in milliseconds)

| Scenario | Sample Count | Min (ms) | Median / P50 (ms) | Mean (ms) | P90 (ms) | P95 (ms) | P99 (ms) | Max (ms) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Cold-Start Initialization** | 10 | 0.7755 | **0.8053** | 1.6061 | 1.7870 | 5.2197 | 7.9658 | 8.6524 |
| **Warm Scored Normal (`WARM_NORMAL`)** | 200 | 0.3740 | **0.4013** | 0.4034 | 0.4097 | 0.4220 | 0.4785 | 0.5492 |
| **Anomalous Inference (`ANOMALY`)** | 200 | 0.4115 | **0.4415** | 0.4435 | 0.4525 | 0.4634 | 0.4916 | 0.5244 |
| **Missing Data Bypass (`MISSING_DATA`)** | 200 | 0.0028 | **0.0032** | 0.0033 | 0.0035 | 0.0036 | 0.0067 | 0.0111 |
| **Insufficient Data Warmup (`INSUFFICIENT_DATA`)** | 200 | 0.0033 | **0.0035** | 0.0037 | 0.0039 | 0.0046 | 0.0083 | 0.0109 |
| **Multi-Sensor Interleaved Stream (`MULTI_SENSOR`)** | 200 | 0.4108 | **0.4429** | 0.4504 | 0.4554 | 0.4660 | 0.4910 | 1.6179 |
| **Direct Engine Baseline (`DIRECT_ENGINE_INFERENCE`)** | 200 | 0.3685 | **0.3955** | 0.3967 | 0.4075 | 0.4149 | 0.4282 | 0.4368 |

---

## 4. Key Performance Observations

### A. Sub-Millisecond Scored Inference
- Steady-state warm inference executes in **~0.40 ms (P50)** and **~0.42 ms (P95)** on CPU.
- Throughput exceeds **2,400 inference evaluations per second** per core under steady-state sliding window conditions.

### B. Ultra-Fast Bypass Short-Circuiting
- Both `INSUFFICIENT_DATA` (warmup $< 30$ points) and `MISSING_DATA` (null / NaN / non-GOOD quality) execute in **~0.003 ms (~3 µs)**.
- Telemetry dropouts and initial buffer accumulations cleanly bypass the neural network forward pass without unnecessary computational load.

### C. Observability & Diagnostic Instrumentation Overhead
- Comparing the direct underlying inference engine (`DIRECT_ENGINE_INFERENCE` P50 = 0.3955 ms) with the fully observable service (`WARM_NORMAL` P50 = 0.4013 ms) indicates an instrumentation overhead of **$\approx 0.0058\text{ ms}$ ($\approx 5.8\text{ µs}$)**.
- Diagnostic audit recording, timestamp parsing, and bounded history tracking introduce negligible computational cost ($< 1.5\%$ runtime delta).

### D. Multi-Sensor Stream Isolation
- Interleaved traffic across all 5 Bharati sensors (`BRT_TEMP_001` through `BRT_POWER_001`) maintains consistent sub-millisecond latency (P50 = 0.4429 ms, P95 = 0.4660 ms).
- No cross-sensor state contamination, memory leakage, or buffer thrashing was observed.

### E. Memory & State Boundedness
- Diagnostic history in `BharatiMLService` was strictly bounded to `max_diagnostics_history = 100` records after processing 150 consecutive events.
- Rolling window observation history for each sensor was strictly bounded to `sequence_length = 30` observations.

### F. Repeated Run Stability
- Consecutive runs under identical workloads demonstrated tight reproducibility: Run 1 P50 = 0.4013 ms vs Run 2 P50 = 0.4008 ms ($< 0.15\%$ variance).

---

## 5. Frozen Artifact Integrity Verification

| Artifact Path | Expected SHA-256 Hash | Status |
| :--- | :--- | :---: |
| `ml/models/lstm-ae-bharati-v1.pt` | `412b6cb782c533db6d6024b86f2cfe709e1485f888099b429d4c8a2a8bf6111a` | **VERIFIED** |
| `ml/models/lstm-ae-bharati-v1_config.json` | `16614a022b6508863d8476eb65d9e695cd0ceed118c142be8e740bbdf9ab3ad7` | **VERIFIED** |
| `ml/models/lstm-ae-bharati-v1_scaler.json` | `b9c1d1077912743c0bd0f7046e7a9c52fd646f2e4a9c7f85773629939ef70899` | **VERIFIED** |
| `ml/results/bharati_lstm_threshold.json` | `95b45031504a584e582cb4c36918cfb9a22fb6c599d530f3a47cd4e21c1f1a9d` | **VERIFIED** |

---

## 6. Known Limitations

1. **Hardware Specificity**: Measurements reflect single-thread CPU execution on host development hardware (`Apple Silicon arm64`). Actual performance on field gateways (e.g. Raspberry Pi, Intel NUC, or industrial edge compute units) will scale with target CPU IPC and clock speed.
2. **Synthetic Data Profiling**: Telemetry values are generated synthetically; network transmission delays, disk serialization, and IPC socket latency are not included in pure ML inference benchmarks.
