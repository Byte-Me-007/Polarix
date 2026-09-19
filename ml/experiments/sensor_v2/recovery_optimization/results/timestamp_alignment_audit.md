# Sensor ML V2 — Timestamp Alignment and Population Audit

## 1. Audit Overview

This audit verifies the chronological integrity, synchronized channel alignment, and exact sample counts across Maitri and Bharati test telemetry.

---

## 2. Sample Count Reconciliation

| Station | Station-Level Synchronized $N$ | Normal $N$ | Anomaly $N$ | Per-Channel Concatenated $N$ | Channel Count | Alignment Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Maitri (MTR)** | **238** | 179 | 59 | 1182 | 5 channels | **SYNCHRONIZED (100%)** |
| **Bharati (BRT)** | **238** | 179 | 59 | 1182 | 5 channels | **SYNCHRONIZED (100%)** |

### Key Population Distinction:
- **Station-Level Population ($N = 238$):** The true evaluation set size for multivariate station decision, consisting of 238 distinct chronological timestamps where all 5 station sensors are simultaneously observed.
- **Per-Channel Concatenated Population ($N = 1,182$):** The sum of individual univariate sequence windows across all 5 separate sensor channels ($~236.4$ windows per channel).

---

## 3. Chronological Integrity Verification

### Maitri (MTR) Channel Breakdown
| Sensor ID | Windows ($N$) | Strictly Chronological | Duplicate Timestamps |
| :--- | :---: | :---: | :---: |
| `HUM_001` | 236 | `True` | `False` |
| `POWER_001` | 237 | `True` | `False` |
| `PRESS_001` | 234 | `True` | `False` |
| `TEMP_001` | 237 | `True` | `False` |
| `VIB_001` | 238 | `True` | `False` |

### Bharati (BRT) Channel Breakdown
| Sensor ID | Windows ($N$) | Strictly Chronological | Duplicate Timestamps |
| :--- | :---: | :---: | :---: |
| `BRT_HUM_001` | 236 | `True` | `False` |
| `BRT_POWER_001` | 237 | `True` | `False` |
| `BRT_PRESS_001` | 234 | `True` | `False` |
| `BRT_TEMP_001` | 237 | `True` | `False` |
| `BRT_VIB_001` | 238 | `True` | `False` |
