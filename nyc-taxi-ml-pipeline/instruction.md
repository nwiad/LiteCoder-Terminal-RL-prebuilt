Build an end-to-end ML pipeline that reads a raw NYC Yellow Taxi Trip Record Parquet file, cleans and engineers features, trains a regression model to predict `total_amount`, evaluates it, and serializes the trained model to disk. Everything must be packaged in a single runnable Python script.

## Technical Requirements

- Language: Python 3
- Required libraries: dask, scikit-learn, joblib (install as needed)
- Input file: `/app/data/yellow_tripdata_2022-01.parquet`
- Main script: `/app/train_nyc_taxi_revenue.py`
- Trained model output: `/app/nyc_taxi_model.joblib`
- Evaluation metrics output: `/app/metrics.json`

## Input Data

The input Parquet file contains NYC Yellow Taxi trip records with the following columns:

`VendorID`, `tpep_pickup_datetime`, `tpep_dropoff_datetime`, `passenger_count`, `trip_distance`, `RatecodeID`, `store_and_fwd_flag`, `PULocationID`, `DOLocationID`, `payment_type`, `fare_amount`, `extra`, `mta_tax`, `tip_amount`, `tolls_amount`, `improvement_surcharge`, `total_amount`, `congestion_surcharge`, `airport_fee`

## Pipeline Requirements

1. **Data Loading**: Use Dask to read the Parquet file for out-of-core processing.

2. **Data Cleaning**: Remove or handle rows with invalid or missing values. At minimum:
   - Drop rows where `trip_distance <= 0` or `total_amount <= 0`
   - Drop rows with null values in key numeric columns

3. **Feature Engineering**: Create at least the following derived features from the raw data:
   - `trip_duration_minutes`: computed from pickup and dropoff datetime columns
   - `pickup_hour`: hour of day extracted from `tpep_pickup_datetime`
   - `pickup_dayofweek`: day of week extracted from `tpep_pickup_datetime`

4. **Train/Validation Split**: Split the cleaned data into training (80%) and validation (20%) sets using a fixed `random_state=42` for reproducibility.

5. **Model Training**: Train a Gradient Boosting Regressor (scikit-learn compatible, e.g., `GradientBoostingRegressor` or `HistGradientBoostingRegressor`) to predict `total_amount`. The model must NOT use `total_amount` itself or any of its direct sub-components (`fare_amount`, `extra`, `mta_tax`, `tip_amount`, `tolls_amount`, `improvement_surcharge`, `congestion_surcharge`, `airport_fee`) as input features — these would constitute data leakage.

6. **Evaluation**: Evaluate the trained model on the validation set. Compute both RMSE and MAE.

7. **Model Serialization**: Save the trained model to `/app/nyc_taxi_model.joblib` using `joblib.dump`.

8. **Metrics Output**: Write a JSON file to `/app/metrics.json` with the following structure:
   ```json
   {
     "rmse": <float>,
     "mae": <float>,
     "n_train": <int>,
     "n_val": <int>
   }
   ```
   Where `n_train` and `n_val` are the number of samples in the training and validation sets respectively.

## Script Requirements

- The script `/app/train_nyc_taxi_revenue.py` must be executable via `python /app/train_nyc_taxi_revenue.py` with no additional arguments.
- The script must print progress messages to stdout (at minimum: data loading, cleaning stats, training start, evaluation results).
- After successful execution, both `/app/nyc_taxi_model.joblib` and `/app/metrics.json` must exist.
- The saved model must be loadable via `joblib.load('/app/nyc_taxi_model.joblib')` and must have a `.predict()` method.
- RMSE on the validation set must be finite and positive (i.e., `0 < rmse < inf`).
- MAE on the validation set must be finite and positive (i.e., `0 < mae < inf`).
- `n_train` and `n_val` must both be positive integers, and `n_train > n_val`.
