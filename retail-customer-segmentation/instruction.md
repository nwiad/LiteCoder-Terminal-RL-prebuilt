## Customer Segmentation Analysis for Retail Chain

Build a customer segmentation pipeline using K-means clustering on a synthetic retail customer dataset. The pipeline must generate data, preprocess it, find optimal clusters, and output structured results.

### Technical Requirements

- Language: Python 3
- Libraries: pandas, numpy, scikit-learn, matplotlib/seaborn
- All scripts and outputs under `/app/`

### Step 1: Generate Synthetic Dataset

Write a script `/app/generate_data.py` that creates `/app/customers.csv` with exactly 500 rows and the following columns:

| Column | Type | Description |
|---|---|---|
| customer_id | int | Unique ID from 1 to 500 |
| age | int | Random integer in [18, 70] |
| gender | str | "M" or "F" (roughly 50/50) |
| annual_income | float | Random in [15000.0, 150000.0] |
| total_purchases | int | Random integer in [1, 200] |
| avg_order_value | float | Random in [10.0, 500.0] |
| days_since_last_purchase | int | Random integer in [0, 365] |
| online_purchase_ratio | float | Random in [0.0, 1.0] |
| loyalty_score | float | Random in [0.0, 100.0] |
| num_returns | int | Random integer in [0, 30] |

- Use `numpy.random.seed(42)` for reproducibility.
- Introduce missing values: randomly set approximately 5% of cells in `annual_income`, `avg_order_value`, and `loyalty_score` to NaN.

### Step 2: Segmentation Pipeline

Write `/app/segmentation.py` that reads `/app/customers.csv` and performs:

1. **Data Cleaning**: Handle missing values using median imputation for numeric columns. Drop the `customer_id` and `gender` columns before clustering (keep them for the final output mapping).
2. **Feature Scaling**: Standardize all numeric features used for clustering (zero mean, unit variance).
3. **Optimal K Selection**: Evaluate K-means for k = 2 through 8 (inclusive). Compute inertia and silhouette score for each k. Select the k with the highest silhouette score as the optimal number of clusters.
4. **Final Clustering**: Run K-means with the optimal k using `random_state=42`.
5. **Outputs** — the script must produce all of the following:

#### `/app/output.json`

A JSON file with this exact structure:

```json
{
  "optimal_k": <int>,
  "silhouette_scores": {
    "2": <float>, "3": <float>, "4": <float>,
    "5": <float>, "6": <float>, "7": <float>, "8": <float>
  },
  "inertia_values": {
    "2": <float>, "3": <float>, "4": <float>,
    "5": <float>, "6": <float>, "7": <float>, "8": <float>
  },
  "cluster_sizes": {
    "0": <int>, "1": <int>, ...
  },
  "cluster_centers": [
    [<float>, ...],
    ...
  ],
  "feature_names": ["age", "annual_income", "total_purchases", "avg_order_value", "days_since_last_purchase", "online_purchase_ratio", "loyalty_score", "num_returns"]
}
```

- `silhouette_scores` and `inertia_values`: keys are string representations of k.
- `cluster_centers`: list of lists, each inner list has length equal to the number of features (8). These are the centers in the **scaled** feature space.
- `cluster_sizes`: keys are string cluster labels ("0", "1", ...), values are the count of customers in each cluster.
- All floats rounded to 4 decimal places.

#### `/app/customer_segments.csv`

A CSV file with columns: `customer_id`, `cluster`. One row per customer (500 rows), mapping each customer to their assigned cluster label (integer starting from 0).

#### `/app/elbow_plot.png`

A plot showing inertia vs. k (x-axis: k from 2 to 8, y-axis: inertia).

#### `/app/silhouette_plot.png`

A plot showing silhouette score vs. k (x-axis: k from 2 to 8, y-axis: silhouette score).

### Execution

Running the following commands in sequence should produce all outputs:

```bash
cd /app
python3 generate_data.py
python3 segmentation.py
```
