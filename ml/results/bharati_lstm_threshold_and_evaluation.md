# Polarix Bharati LSTM Threshold Selection & Evaluation Report (SIH26060 - Person C)

**Station:** Bharati (`BRT`)  
**Model Version:** `lstm-ae-bharati-v1`  
**Architecture:** Sequence-to-Sequence LSTM Autoencoder (`seq_len = 30`)  
**Selected Frozen Threshold:** `0.013215`  

---

> [!IMPORTANT]
> **SYNTHETIC DATA DISCLAIMER**:
> All threshold tuning and evaluation were conducted strictly on synthetic telemetry for Bharati station.
> No real Antarctic station data was used. Performance figures represent mathematical properties on synthetic benchmark distributions and do NOT constitute field operational SLAs.

---

## 1. Threshold Selection Methodology

1. **Validation-Only Tuning**: Candidate thresholds were evaluated exclusively on the **Validation split** (`1,181` sequences: `889` normal, `292` anomalous).
2. **Primary Selection Criterion**: Maximum **Validation F1-Score**.
3. **Deterministic Tie-Breaking**:
   - 1. Higher Recall
   - 2. Lower False Positive Rate (FPR)
   - 3. Lower Threshold
4. **Frozen Application**: The selected threshold (`0.013215`) was frozen into `ml/results/bharati_lstm_threshold.json` and evaluated exactly once on the untouched held-out **Test split** (`1,182` sequences). Test labels were never used during threshold search.

---

## 2. Quantitative Performance Across Splits

### Validation Split (Tuning Partition):
- **True Positives (TP)**: `184` | **True Negatives (TN)**: `449`
- **False Positives (FP)**: `440` | **False Negatives (FN)**: `108`
- **Accuracy**: `53.60%`
- **Precision**: `0.2949`
- **Recall**: `0.6301`
- **F1-Score**: `0.4017`
- **False Positive Rate (FPR)**: `49.49%`

### Test Split (Held-Out Evaluation Partition):
- **True Positives (TP)**: `165` | **True Negatives (TN)**: `442`
- **False Positives (FP)**: `451` | **False Negatives (FN)**: `124`
- **Accuracy**: `51.35%`
- **Precision**: `0.2679`
- **Recall**: `0.5709`
- **F1-Score**: `0.3646`
- **False Positive Rate (FPR)**: `50.50%`

---

## 3. Anomaly-Type Detection Breakdown (Test Split)

| Anomaly Type | Total Test Instances | Detected by LSTM | Recall Rate | Operational Behavioral Notes |
| :--- | :--- | :--- | :--- | :--- |
| **`SPIKE`** | `19` | `19` | **`19/19 (100.00%)`** | High reconstruction error on sudden high-magnitude excursions. |
| **`DRIFT`** | `150` | `132` | **`132/150 (88.00%)`** | Sequence encoder detects ramp deviations across temporal window. |
| **`STUCK_VALUE`** | `120` | `14` | **`14/120 (11.67%)`** | Flatlines inside normal variance range yield moderate reconstruction errors. |
| **`DROPOUT`** | N/A | N/A | **`100% (Rule-Based)`** | Handled explicitly at data ingestion (`MISSING_DATA`) before sequence inference. |

---

## 4. Alternative Operating Points (Validation Analysis)

| Operating Point | Threshold | Val Precision | Val Recall | Val F1 | Val FPR | Use Case |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Primary (Max-F1)** | `0.013215` | `0.2949` | `0.6301` | `0.4017` | `0.4949` | Balanced anomaly detection |
| **High Recall** | `0.000770` | `0.2472` | `1.0000` | `0.3965` | `1.0000` | Mission-critical safety monitoring |
| **Low False Positive** | `1.874927` | `0.0745` | `0.0240` | `0.0363` | `0.0979` | Alert-fatigue prevention |
| **P90 Normal Error** | `1.870710` | `0.0729` | `0.0240` | `0.0361` | `0.1001` | Statistical baseline |

---

## 5. Factual Comparison: LSTM Autoencoder vs. Rolling Z-Score

| Evaluation Metric | Rolling Z-Score (`zscore-bharati-v1`) | LSTM Autoencoder (`lstm-ae-bharati-v1`) | Factual Technical Trade-Offs |
| :--- | :--- | :--- | :--- |
| **Test Precision** | `1.0000` | `0.2679` | Z-score avoids false alarms on smooth telemetry. |
| **Test Recall** | `0.0657` | `0.5709` | LSTM detects multi-step temporal anomalies (e.g., drift). |
| **Test F1-Score** | `0.1234` | `0.3646` | LSTM achieves higher balanced F1 on synthetic anomalies. |
| **Test False Positive Rate** | `0.00%` | `50.50%` | Z-score produces fewer false alarms; LSTM has a higher baseline FPR. |
| **`SPIKE` Detection** | 100.00% (19/19) | 100.00% (19/19) | Both methods achieve 100% recall on high-magnitude spikes. |
| **`DRIFT` Detection** | 0.00% (0/150) | 88.00% (132/150) | Z-score adapts to drift; LSTM recognizes sequence-level deviation. |
| **`STUCK_VALUE` Detection**| 0.00% (0/120) | 11.67% (14/120) | Both statistical & autoencoder models face challenges with within-range flatlines. |
| **`DROPOUT` Handling** | Missing Data Ingestion Rule | Missing Data Ingestion Rule | Both architectures rely on upstream null checks. |

---

## 6. Generated Artifacts

- **Frozen Threshold File:** `ml/results/bharati_lstm_threshold.json`
- **Threshold Search Details:** `ml/results/bharati_lstm_threshold_search.json`
- **Full Evaluation Results:** `ml/results/bharati_lstm_evaluation.json`
- **Search Curves & Distributions:** `ml/results/bharati_lstm_threshold_search.png`
