## Optimized CPU-Based Matrix Factorization for Recommendation Systems

Implement an ALS (Alternating Least Squares) matrix factorization recommender in Python that outperforms a baseline k-NN collaborative filter on the MovieLens 100K dataset. All computation must be CPU-only (no GPU libraries). The solution must download the dataset automatically if not present.

### Technical Requirements

- Language: Python 3.x
- Allowed libraries: NumPy, SciPy, pandas, scikit-learn, requests/urllib (for downloading). No GPU libraries, no Cython, no implicit library.
- Working directory: `/app`
- Random seed: `42` for all random operations (train/test split, etc.)

### Dataset

Download the MovieLens 100K dataset from `https://files.grouplens.org/datasets/movielens/ml-100k.zip`. Extract and use the `u.data` file (tab-separated: user_id, item_id, rating, timestamp). If the dataset already exists at `/app/ml-100k/u.data`, skip downloading.

### Steps and Output Files

**1. Train/Test Split**

Split the ratings into 80% train / 20% test using random seed `42`. Save to:
- `/app/train.csv` — columns: `user_id,item_id,rating` (no header)
- `/app/test.csv` — columns: `user_id,item_id,rating` (no header)

**2. Baseline k-NN Collaborative Filter**

Implement a user-based k-NN collaborative filter with cosine similarity and k=20 neighbors. Evaluate test RMSE.

**3. ALS Matrix Factorization**

Implement a CSR-based ALS solver with configurable:
- Rank (latent factors): search within 20–100
- Regularization: search within 0.01–1.0
- Iterations: search within 10–30

Tune hyperparameters and train the final model on the training set.

**4. Model Persistence**

Save the trained model factors to:
- `/app/user_factors.npy` — NumPy array of shape `(n_users, rank)`, float32
- `/app/item_factors.npy` — NumPy array of shape `(n_items, rank)`, float32

**5. Metrics Output**

Write `/app/metrics.json` with the following structure:
```json
{
  "baseline_knn_rmse": <float>,
  "als_rmse": <float>,
  "training_time_seconds": <float>,
  "prediction_latency_ms": <float>,
  "peak_ram_mb": <float>,
  "als_rank": <int>,
  "als_reg": <float>,
  "als_iterations": <int>
}
```

- `baseline_knn_rmse`: Test RMSE of the k-NN baseline.
- `als_rmse`: Test RMSE of the ALS model. Must be strictly less than `baseline_knn_rmse`.
- `training_time_seconds`: Wall-clock ALS training time in seconds. Must be ≤ 300.
- `prediction_latency_ms`: Average prediction latency per user-item pair in milliseconds, measured over 1000 random test pairs. Must be ≤ 5.
- `peak_ram_mb`: Peak RAM usage in MB during training. Must be < 2048.
- `als_rank`, `als_reg`, `als_iterations`: The chosen hyperparameters.

All float values should be rounded to 4 decimal places.

**6. Recommendations Output**

Write `/app/recommendations.json` containing top-10 item recommendations for users 1 through 5:
```json
{
  "1": [item_id, item_id, ...],
  "2": [item_id, item_id, ...],
  "3": [item_id, item_id, ...],
  "4": [item_id, item_id, ...],
  "5": [item_id, item_id, ...]
}
```
Each value is a list of 10 integer item IDs ranked by predicted rating (descending). Exclude items already rated by the user in the training set.

### Entry Point

Provide a single script `/app/run.py` that executes the full pipeline (download, split, train baseline, train ALS, evaluate, save outputs). Running `python /app/run.py` must produce all output files listed above.
