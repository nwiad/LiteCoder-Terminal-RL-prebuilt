## Anomaly Detection & Clustering in IoT Sensor Data

Detect anomalies and identify behavioral clusters in IoT sensor data using unsupervised learning techniques.

**Technical Requirements:**
- Python 3.x
- Input: `/app/sensors.json` (JSONL format with sensor readings)
- Outputs: `/app/anomalies.csv`, `/app/clusters.json`

**Input Specification:**

The file `/app/sensors.json` contains newline-delimited JSON records with this structure:
```json
{"timestamp": "2024-01-15T10:00:00Z", "sensor_id": "S001", "temperature": 72.5, "vibration": 0.3, "power": 150.2}
```

Each record has:
- `timestamp`: ISO 8601 datetime string
- `sensor_id`: string identifier (e.g., "S001", "S002")
- `temperature`: float (Celsius)
- `vibration`: float (arbitrary units)
- `power`: float (Watts)

**Task Requirements:**

1. **Feature Engineering**: Calculate 5-minute rolling window statistics for each sensor:
   - mean, standard deviation, min, max for each metric (temperature, vibration, power)

2. **Anomaly Detection**: Implement an Isolation Forest model to detect anomalies based on the rolling statistics. Output `/app/anomalies.csv` with columns:
   - `timestamp`: ISO 8601 string
   - `sensor_id`: string
   - `anomaly_score`: float (model's anomaly score)
   - `is_anomaly`: boolean (true if anomalous)

3. **Clustering**: Apply dimensionality reduction (UMAP or PCA) and clustering (HDBSCAN or K-means) on daily aggregated statistics per sensor. Output `/app/clusters.json` with structure:
```json
[
  {
    "sensor_id": "S001",
    "cluster": 0,
    "x": -2.34,
    "y": 1.56
  }
]
```

Where `x` and `y` are 2D coordinates from dimensionality reduction, and `cluster` is the assigned cluster label (integer, or -1 for noise).

**Output Format:**

`/app/anomalies.csv`:
```
timestamp,sensor_id,anomaly_score,is_anomaly
2024-01-15T10:05:00Z,S001,0.45,false
2024-01-15T10:05:00Z,S002,0.78,true
```

`/app/clusters.json`: JSON array of objects as specified above.
