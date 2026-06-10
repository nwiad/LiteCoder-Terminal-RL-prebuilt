## PyTorch RNN for Stock Price Prediction

Build a PyTorch-based RNN model to predict the next-day closing price of Apple stock using synthetic historical price data. Generate the data, train the model, evaluate it against a naïve baseline, and persist all artifacts.

### Technical Requirements

- Language: Python 3.x
- Libraries: PyTorch (CPU), pandas, numpy, scikit-learn, matplotlib
- Random seed: use `42` for all random number generators (numpy, torch) to ensure reproducibility

### Step 1: Generate Synthetic Data

Create a synthetic 30-day AAPL OHLCV dataset and save it to `/app/aapl_30d.csv`.

CSV columns (in order): `Date`, `Open`, `High`, `Low`, `Close`, `Volume`

- `Date`: 30 consecutive business days starting from `2024-01-02`
- Prices should start with a Close near 180.0, include a slight upward drift and realistic daily noise
- `Volume`: integer values, realistic daily trading volumes (e.g., in the millions range)
- All price columns (`Open`, `High`, `Low`, `Close`) must be float values rounded to 2 decimal places
- The file must contain exactly 31 lines (1 header + 30 data rows)

### Step 2: Feature Engineering

- Use a 5-day look-back window of normalized daily returns as input features
- Target: next-day closing price
- Split data into training and test sets. The last 5 data points (by date order) form the test set; all earlier usable samples form the training set.
- Normalize features using min-max scaling fitted on the training set only

### Step 3: Model Architecture

Implement an RNN model in PyTorch with the following structure:

- Input layer accepting sequences of shape `(batch, 5, 1)` (5 timesteps, 1 feature per step)
- A single `nn.RNN` layer with `nonlinearity='tanh'`, `hidden_size=16`, `num_layers=1`, `batch_first=True`
- A fully connected output layer (`nn.Linear`) mapping from 16 hidden units to 1 output
- Train for at least 100 epochs using MSE loss and Adam optimizer

### Step 4: Evaluation

Evaluate the trained model on the test set and compare against a naïve baseline (predicted price = previous day's close).

Compute for both the RNN model and the naïve baseline:
- MAE (Mean Absolute Error)
- RMSE (Root Mean Squared Error)

### Step 5: Output Artifacts

Save the following files:

1. `/app/aapl_30d.csv` — the synthetic dataset (from Step 1)

2. `/app/model.pt` — the trained model's `state_dict` saved via `torch.save()`

3. `/app/actual_vs_predicted.png` — a plot showing:
   - Actual closing prices (test set)
   - RNN predicted prices (test set)
   - X-axis: Date, Y-axis: Price
   - A legend distinguishing the two series

4. `/app/report.json` — a JSON file with the following exact top-level keys:
   ```json
   {
     "model": {
       "type": "RNN",
       "hidden_size": 16,
       "num_layers": 1,
       "nonlinearity": "tanh",
       "lookback": 5,
       "epochs": <int>,
       "learning_rate": <float>,
       "optimizer": "Adam",
       "loss_function": "MSE"
     },
     "metrics": {
       "rnn": {
         "mae": <float>,
         "rmse": <float>
       },
       "naive_baseline": {
         "mae": <float>,
         "rmse": <float>
       }
     },
     "data": {
       "total_samples": 30,
       "train_size": <int>,
       "test_size": 5,
       "start_date": "2024-01-02",
       "end_date": "<last business day>"
     }
   }
   ```
   All float values in the JSON must be rounded to 4 decimal places.
