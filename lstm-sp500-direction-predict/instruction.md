## CPU-Based PyTorch LSTM for S&P 500 Time Series Prediction

Build a CPU-optimized PyTorch LSTM model that predicts next-day S&P 500 closing price direction (up or down) from historical daily data, and evaluate it on a held-out test set.

### Technical Requirements

- Language: Python 3.x
- Libraries: torch (CPU only), pandas, matplotlib, scikit-learn, numpy
- Input file: `/app/input.csv`
- Output files:
  - `/app/output.json` — evaluation metrics and metadata
  - `/app/sp500_lstm_cpu.pth` — saved model state_dict
  - `/app/test_directions.png` — plot of actual vs predicted directions on the test set

### Input Specification

`/app/input.csv` is a CSV file with at least 252 rows of daily S&P 500 data. Columns:

| Column | Type   | Description                  |
|--------|--------|------------------------------|
| Date   | string | Trading date (YYYY-MM-DD)    |
| Open   | float  | Opening price                |
| High   | float  | Daily high price             |
| Low    | float  | Daily low price              |
| Close  | float  | Closing price                |
| Volume | int    | Daily trading volume         |

The file is sorted by Date in ascending order (oldest first). There are no missing values.

### Feature Engineering

From the input data, compute the following features for each row:

1. **Log-return of Close**: `ln(Close_t / Close_{t-1})`
2. **5-day rolling volatility**: standard deviation of the log-return over the past 5 days (inclusive of current day)

The prediction target is **next-day direction**: `1` if tomorrow's Close > today's Close, else `0`.

Drop any rows where features cannot be computed (e.g., the first 4 rows for rolling volatility). Drop the last row (no next-day target available).

### Data Splitting

Split the resulting dataset chronologically (do not shuffle):

- Train: first 60% of rows
- Validation: next 20% of rows
- Test: final 20% of rows

### Model Architecture

Build a PyTorch LSTM model with exactly:

- 1 LSTM layer with `hidden_size=32` and `dropout=0.2`
- Input size = 2 (log-return, rolling volatility)
- A single fully-connected linear output layer producing 1 logit for binary classification
- The model must run on CPU only (no `.cuda()` or device transfers to GPU)

### Training

- Optimizer: Adam with `learning_rate=0.001`
- Loss: `BCEWithLogitsLoss`
- Batch size: 32
- Maximum epochs: 30
- Early stopping: stop training if validation loss does not improve for 5 consecutive epochs
- Save the best model (lowest validation loss) state_dict to `/app/sp500_lstm_cpu.pth`

### Evaluation & Output

Evaluate the best model on the test set. Compute **directional accuracy**: the fraction of test samples where the predicted direction matches the actual direction. A predicted direction is `1` if the model's sigmoid output ≥ 0.5, else `0`.

Write `/app/output.json` with the following structure:

```json
{
  "directional_accuracy": <float between 0.0 and 1.0>,
  "train_size": <int>,
  "val_size": <int>,
  "test_size": <int>,
  "epochs_trained": <int>,
  "best_val_loss": <float>
}
```

All float values should be rounded to 4 decimal places.

Print exactly one line to stdout: `DirectionalAccuracy: <score>` where `<score>` is the directional accuracy rounded to 4 decimal places (e.g., `DirectionalAccuracy: 0.5417`).

### Plot

Generate `/app/test_directions.png` containing a plot of the test set with:

- X-axis: test sample index (integer)
- Two series: actual directions and predicted directions
- A legend distinguishing "Actual" and "Predicted"
- A title containing "Test Set Directions"
