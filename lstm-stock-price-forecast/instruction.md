## Stock Price Forecasting with LSTM

Build an end-to-end CPU-only LSTM pipeline that reads historical daily OHLCV stock data, engineers features, trains an LSTM model, produces 1-step-ahead closing-price forecasts, and persists the model and scaler to disk.

### Technical Requirements

- Language: Python 3.x
- Deep learning framework: TensorFlow/Keras (CPU only)
- Input file: `/app/input.csv`
- Output files:
  - `/app/output.json` — evaluation metrics and metadata
  - `/app/aapl_features.csv` — engineered feature set
  - `/app/lstm_stock.h5` — trained Keras model (HDF5 format)
  - `/app/mm_scaler.pkl` — fitted MinMaxScaler serialized via joblib

### Input Specification

`/app/input.csv` is a CSV file with daily OHLCV data containing at least 500 rows. Columns:

| Column   | Type   | Description              |
|----------|--------|--------------------------|
| Date     | string | Format `YYYY-MM-DD`      |
| Open     | float  | Daily open price         |
| High     | float  | Daily high price         |
| Low      | float  | Daily low price          |
| Close    | float  | Daily close price        |
| Volume   | int    | Daily trading volume     |

Rows are sorted by Date in ascending order. No missing values.

### Feature Engineering

Read `/app/input.csv` and produce `/app/aapl_features.csv` with the following additional columns appended to the original data:

- `Return_1` through `Return_5`: lagged daily returns for lags 1–5, where `Return_k = (Close[t] - Close[t-k]) / Close[t-k]`
- `Volatility_5`: 5-day realized volatility, computed as the rolling standard deviation of daily log-returns over a 5-day window
- `DayOfWeek_0` through `DayOfWeek_4`: one-hot encoded day-of-week columns (Monday=0 … Friday=4)

Drop any rows that contain NaN values resulting from the lagged/rolling computations. Save the result to `/app/aapl_features.csv` with a header row and no index column.

### Model Architecture & Training

- Sliding window: use a 60-day look-back window to create (X, y) sequence pairs, where y is the next-day Close price.
- Scaling: apply `sklearn.preprocessing.MinMaxScaler` fitted on the training set only. Scale all feature columns used as model input.
- Train/test split: first 90% of samples (chronological order) for training, last 10% for testing. No shuffling.
- Architecture: Sequential model with exactly these layers in order:
  1. LSTM layer with 64 units (return_sequences=False)
  2. Dropout layer with rate 0.2
  3. Dense layer with 1 output unit
- Optimizer: Adam
- Loss: mean squared error
- Training: use EarlyStopping with `patience=5` monitoring validation loss; use 20% of the training data as a validation split.

### Evaluation & Output

Produce 1-step-ahead forecasts on the test set. Inverse-transform predictions and actuals back to original price scale.

Write `/app/output.json` with the following structure:

```json
{
  "rmse": <float>,
  "mae": <float>,
  "test_size": <int>,
  "train_size": <int>,
  "lookback": 60,
  "features_shape": [<rows>, <cols>],
  "predictions": [<float>, ...]
}
```

- `rmse`: root mean squared error on the test set (original scale)
- `mae`: mean absolute error on the test set (original scale)
- `test_size`: number of test samples
- `train_size`: number of training samples
- `lookback`: the look-back window size (must be 60)
- `features_shape`: `[num_rows, num_columns]` of `/app/aapl_features.csv`
- `predictions`: list of predicted closing prices for the test set (original scale, each value a float)

### Model & Scaler Persistence

- Save the trained Keras model to `/app/lstm_stock.h5` in HDF5 format.
- Save the fitted MinMaxScaler to `/app/mm_scaler.pkl` using `joblib.dump`.

### Constraints

- The pipeline must run entirely on CPU.
- All numeric values in `output.json` must be JSON-serializable (no numpy types).
- `rmse` and `mae` must be finite positive numbers.
- The `predictions` array length must equal `test_size`.
