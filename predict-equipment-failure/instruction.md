Build a machine learning model to predict equipment failure before it occurs using historical sensor data from industrial machines.

## Technical Requirements

- Language: Python 3.x
- Input file: `/app/sensor_data.csv` - Historical sensor readings with columns: `timestamp`, `machine_id`, `temperature`, `vibration`, `pressure`, `power_consumption`, `failure_occurred` (binary: 0 or 1)
- Output file: `/app/predictions.csv` - Test set predictions with columns: `timestamp`, `machine_id`, `failure_probability`, `predicted_failure` (binary: 0 or 1)
- Model performance file: `/app/metrics.json` - Evaluation metrics in JSON format

## Input Specifications

The sensor_data.csv contains:
- 50 unique machines monitored over 2 years
- Hourly sensor readings (temperature in Celsius, vibration in mm/s, pressure in bar, power_consumption in kW)
- Binary failure indicator (1 = failure occurred within next 24 hours, 0 = normal operation)
- Temporal ordering by timestamp (format: YYYY-MM-DD HH:MM:SS)

## Output Specifications

predictions.csv must contain:
- All test set records with their original timestamp and machine_id
- `failure_probability`: Float between 0 and 1 representing predicted failure risk
- `predicted_failure`: Binary prediction (1 if failure_probability >= threshold, 0 otherwise)

metrics.json must contain:
- `precision`: Precision score for the positive class (failure prediction)
- `recall`: Recall score for the positive class
- `f1_score`: F1 score for the positive class
- `confusion_matrix`: 2x2 array [[TN, FP], [FN, TP]]

## Requirements

1. Perform temporal train-test split: first 18 months for training, last 6 months for testing
2. Engineer time-based features using rolling windows (e.g., rolling mean, std, trends over past hours)
3. Handle class imbalance appropriately (failures are rare events)
4. Train at least one machine learning model (Random Forest, XGBoost, Gradient Boosting, or similar)
5. Achieve minimum 85% precision on the positive class (failure prediction) on the test set
6. Save predictions and metrics in the specified formats

## Data Format

sensor_data.csv example:
```
timestamp,machine_id,temperature,vibration,pressure,power_consumption,failure_occurred
2022-01-01 00:00:00,M001,75.2,3.1,5.2,120.5,0
2022-01-01 01:00:00,M001,76.8,3.3,5.1,122.1,0
```

predictions.csv example:
```
timestamp,machine_id,failure_probability,predicted_failure
2023-07-01 00:00:00,M001,0.12,0
2023-07-01 01:00:00,M001,0.89,1
```

metrics.json example:
```json
{
  "precision": 0.87,
  "recall": 0.72,
  "f1_score": 0.79,
  "confusion_matrix": [[9500, 150], [280, 720]]
}
```
