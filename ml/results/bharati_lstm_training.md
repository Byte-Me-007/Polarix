# Polarix Bharati LSTM Autoencoder Training Report (SIH26060 - Person C)

**Station:** Bharati (`BRT`)  
**Model Version:** `lstm-ae-bharati-v1`  
**Architecture:** Sequence-to-Sequence LSTM Autoencoder  
**Training Status:** Model Trained & Saved (Validation-Selected Best Epoch)  

---

> [!IMPORTANT]
> **SYNTHETIC DATA DISCLAIMER**:
> This model was trained and evaluated strictly on synthetic telemetry generated for Bharati station.
> No real Antarctic sensor telemetry was used or claimed.
> **Notice on Anomaly Threshold**: The anomaly detection threshold has **NOT** been selected in this step. A dedicated threshold selection and calibration step will be performed next.

---

## 1. Model Architecture & Hyperparameters

- **Input Dimension**: `1` (univariate sliding sequence per sensor)
- **Sequence Length**: `30` time steps
- **Encoder LSTM**: `32` hidden units (`num_layers = 1`)
- **Latent Bottleneck**: `16` linear units
- **Decoder LSTM**: `32` hidden units with Linear output projection
- **Trainable Parameters**: `11,441`
- **Loss Function**: `MSELoss` (Mean Squared Error)
- **Optimizer**: `Adam(lr=0.001)`, Batch Size: `64`
- **Random Seed**: `42`

---

## 2. Training Data & Leakage Prevention Strategy

- **Source Dataset**: `ml/data/bharati_synthetic_telemetry.csv` (10,000 synthetic records)
- **Chronological Split**: 70% Train (7,000 records), 15% Validation (1,500 records), 15% Test (1,500 records).
- **Normal-Only Training**: Scalers and training sequences are constructed **exclusively from NORMAL training records** (`is_anomaly == 0`). Zero labeled anomalies were included during training.
- **Sequence Counts**:
  - **Training Sequences (Normal Only)**: `6,855`
  - **Validation Sequences**: `1,181`
  - **Test Sequences**: `1,182` (held-out untouched)

---

## 3. Training Dynamics & Convergence

- **Epochs Completed**: `30` (Max: `30`, Early Stopping Patience: `7`)
- **Best Epoch**: `30`
- **Best Validation Loss (MSE)**: `0.405560`
- **Final Training Loss (MSE)**: `0.012275`
- **Final Validation Loss (MSE)**: `0.405560`
- **Loss Observation**: `Validation loss reflects mixed normal and injected anomaly sequences in the validation split.`

---

## 4. Generated Bharati Artifacts & Checksums

| Artifact Role | File Path | Size (Bytes) | SHA-256 Checksum |
| :--- | :--- | :--- | :--- |
| **Model Weights** | `ml/models/lstm-ae-bharati-v1.pt` | `50,757` | `412b6cb782c533db6d6024b86f2cfe709e1485f888099b429d4c8a2a8bf6111a` |
| **Architecture Config** | `ml/models/lstm-ae-bharati-v1_config.json` | `218` | `16614a022b6508863d8476eb65d9e695cd0ceed118c142be8e740bbdf9ab3ad7` |
| **Sensor Scalers** | `ml/models/lstm-ae-bharati-v1_scaler.json` | `691` | `b9c1d1077912743c0bd0f7046e7a9c52fd646f2e4a9c7f85773629939ef70899` |

---

## 5. Next Step

The model weights and evaluation reconstruction errors (`ml/results/bharati_lstm_reconstruction_errors.csv`) are prepared for subsequent validation threshold optimization and quantitative baseline comparison against `zscore-bharati-v1`.
