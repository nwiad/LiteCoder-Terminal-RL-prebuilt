## Network Traffic Simulator with Synthetic Attack Detection

Build a Python program that generates synthetic network traffic data with embedded attack patterns, applies anomaly detection and classification algorithms, and produces a comprehensive security report.

### Technical Requirements

- Language: Python 3.x
- Input: `/app/config.json` (simulation configuration)
- Outputs:
  - `/app/traffic_data.csv` (generated synthetic traffic)
  - `/app/detection_results.csv` (anomaly detection and classification results)
  - `/app/security_report.json` (comprehensive security assessment)
  - `/app/attack_timeline.png` (visualization of attacks over time)

### Input Specification

`/app/config.json` has the following structure:

```json
{
  "num_records": 10000,
  "attack_ratio": 0.15,
  "attack_types": ["dos", "port_scan", "data_exfiltration"],
  "random_seed": 42,
  "duration_seconds": 3600
}
```

- `num_records`: total number of traffic records to generate (integer, >= 100)
- `attack_ratio`: fraction of records that are attacks (float, 0.0–1.0)
- `attack_types`: list of attack types to embed; valid values are `"dos"`, `"port_scan"`, `"data_exfiltration"` (at least one)
- `random_seed`: seed for reproducibility (integer)
- `duration_seconds`: simulated time window in seconds (integer, > 0)

### Output Specifications

#### 1. `/app/traffic_data.csv`

Each row represents one network traffic record. Required columns:

| Column | Type | Description |
|---|---|---|
| `timestamp` | ISO 8601 string | Simulated timestamp within the duration window |
| `src_ip` | string | Source IP address (valid IPv4) |
| `dst_ip` | string | Destination IP address (valid IPv4) |
| `src_port` | int | Source port (1–65535) |
| `dst_port` | int | Destination port (1–65535) |
| `protocol` | string | One of `"TCP"`, `"UDP"`, `"ICMP"` |
| `bytes_sent` | int | Bytes sent (>= 0) |
| `bytes_received` | int | Bytes received (>= 0) |
| `packets` | int | Number of packets (>= 1) |
| `duration_ms` | float | Connection duration in milliseconds (>= 0) |
| `label` | string | `"normal"` or one of the attack type strings from config |

- The total number of rows must equal `num_records`.
- The proportion of attack records (label != `"normal"`) must be approximately equal to `attack_ratio` (within ±2%).
- Attack records must be distributed across the specified `attack_types` (each type must appear at least once).
- Timestamps must be sorted in ascending order and fall within `[T0, T0 + duration_seconds]` for some base time T0.

#### 2. `/app/detection_results.csv`

One row per traffic record (same order as `traffic_data.csv`). Required columns:

| Column | Type | Description |
|---|---|---|
| `record_index` | int | 0-based index matching `traffic_data.csv` row |
| `true_label` | string | Ground truth label from `traffic_data.csv` |
| `anomaly_score` | float | Anomaly score from Isolation Forest (higher = more anomalous) |
| `is_anomaly` | bool | `true` if detected as anomaly, `false` otherwise |
| `predicted_attack_type` | string | Predicted class: `"normal"`, `"dos"`, `"port_scan"`, or `"data_exfiltration"` |

- Anomaly detection must use the Isolation Forest algorithm (from scikit-learn or equivalent).
- Attack classification must use the Random Forest algorithm (from scikit-learn or equivalent).
- The row count must equal `num_records`.

#### 3. `/app/security_report.json`

A JSON object with the following top-level keys:

```json
{
  "summary": {
    "total_records": <int>,
    "total_attacks": <int>,
    "total_normal": <int>,
    "attack_ratio": <float>,
    "detection_rate": <float>,
    "false_positive_rate": <float>
  },
  "attack_breakdown": {
    "dos": {"count": <int>, "detected": <int>},
    "port_scan": {"count": <int>, "detected": <int>},
    "data_exfiltration": {"count": <int>, "detected": <int>}
  },
  "classification_metrics": {
    "accuracy": <float>,
    "precision_macro": <float>,
    "recall_macro": <float>,
    "f1_macro": <float>
  },
  "timeline": {
    "start_time": "<ISO 8601>",
    "end_time": "<ISO 8601>",
    "peak_attack_window": "<ISO 8601 start> / <ISO 8601 end>"
  }
}
```

- `detection_rate`: proportion of actual attacks correctly flagged as anomalies (recall for attacks).
- `false_positive_rate`: proportion of normal records incorrectly flagged as anomalies.
- `accuracy`, `precision_macro`, `recall_macro`, `f1_macro`: standard classification metrics for the Random Forest classifier (values between 0.0 and 1.0).
- `attack_breakdown` must include an entry for every attack type listed in the config, even if its count is 0.
- `peak_attack_window` is the 60-second window containing the most attack records.

#### 4. `/app/attack_timeline.png`

A visualization (PNG image, minimum 800×600 pixels) showing attack occurrences over the simulated time window. The image file must be a valid PNG.

### Execution

The program entry point must be `/app/main.py`. Running `python /app/main.py` should read `/app/config.json` and produce all four output files.
