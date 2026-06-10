## PyTorch Linear Regression to Predict California Housing Prices

Train a PyTorch linear-regression model on the sklearn California Housing dataset, evaluate its performance, and save all artifacts.

### Technical Requirements

- Language: Python 3.x
- Libraries: torch, scikit-learn, pandas, matplotlib
- All output files must be written under `/app/`

### Data Preparation

- Load the California Housing dataset via `sklearn.datasets.fetch_california_housing`.
- Standardize all features using `sklearn.preprocessing.StandardScaler` (fit on training data only, then transform both train and test).
- Split into train/test sets with `test_size=0.2` and `random_state=42`.

### Model Specification

- A single `torch.nn.Linear` layer mapping the 8 input features to 1 output (no hidden layers).
- Loss function: MSELoss.
- Optimizer: SGD with learning rate `0.01`.
- Train for exactly `500` epochs.

### Output Files

1. `/app/linear_regression_cali_housing.pt`
   - The model's `state_dict()` saved via `torch.save`.
   - Must be loadable with `torch.load()` and contain keys `weight` and `bias`.

2. `/app/training_info.json`
   - A JSON file with the following keys (all required):
     - `"learning_rate"`: float (the learning rate used)
     - `"epochs"`: int (number of training epochs)
     - `"optimizer"`: string (name of the optimizer, e.g. `"SGD"`)
     - `"loss_function"`: string (name of the loss function, e.g. `"MSELoss"`)
     - `"test_rmse"`: float (RMSE on the test set)
     - `"test_r2"`: float (R² score on the test set)

3. `/app/pred_vs_actual.png`
   - A scatter plot of predicted vs. actual house values on the test set.
   - Must be a valid PNG image file.

### Performance Constraints

- The test-set RMSE must be less than `0.80` (on standardized-target scale, or equivalently a reasonable value on the original scale given proper preprocessing).
- The test-set R² must be greater than `0.5`.
