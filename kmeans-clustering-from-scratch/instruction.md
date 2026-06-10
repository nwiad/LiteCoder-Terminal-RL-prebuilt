## K-Means Clustering from Scratch

Implement a K-Means clustering algorithm from scratch in Python and apply it to synthetic 2D data. Evaluate performance across different K values and produce a structured JSON report.

### Technical Requirements

- Language: Python 3.x
- Allowed libraries: `numpy`, `matplotlib`, `scikit-learn` (only for `make_blobs` and `silhouette_score`), `json`
- You must NOT use any existing clustering implementation (e.g., `sklearn.cluster.KMeans`). The core K-Means logic (initialization, assignment, update) must be implemented from scratch.
- All code in a single script: `/app/solution.py`
- Running `python /app/solution.py` must produce all output files described below.

### Data Generation

Use `sklearn.datasets.make_blobs` to generate synthetic 2D data with these exact parameters:
- `n_samples=500`
- `centers=4`
- `cluster_std=1.0`
- `random_state=42`

### K-Means Implementation Requirements

The from-scratch K-Means must:
1. Accept parameters: data array, number of clusters `k`, and `max_iterations` (default 300).
2. Use a fixed `random_state=42` (via `numpy.random.seed`) for reproducible centroid initialization.
3. Initialize centroids by randomly selecting `k` data points from the dataset.
4. Iteratively assign each point to the nearest centroid (Euclidean distance) and recompute centroids as the mean of assigned points.
5. Converge when centroid positions do not change between iterations or `max_iterations` is reached.
6. Return: final cluster labels (array of integers), final centroid positions (array of shape `(k, 2)`), and number of iterations until convergence.

### Output Files

1. `/app/output.json` — A JSON file containing the evaluation results with this exact structure:

```json
{
  "data_info": {
    "n_samples": 500,
    "n_features": 2,
    "true_centers": 4
  },
  "kmeans_results": [
    {
      "k": 2,
      "silhouette_score": <float rounded to 4 decimal places>,
      "iterations": <int>,
      "centroids": [[<float>, <float>], ...]
    },
    {
      "k": 3,
      "silhouette_score": <float rounded to 4 decimal places>,
      "iterations": <int>,
      "centroids": [[<float>, <float>], ...]
    },
    {
      "k": 4,
      "silhouette_score": <float rounded to 4 decimal places>,
      "iterations": <int>,
      "centroids": [[<float>, <float>], ...]
    },
    {
      "k": 5,
      "silhouette_score": <float rounded to 4 decimal places>,
      "iterations": <int>,
      "centroids": [[<float>, <float>], ...]
    }
  ],
  "best_k": <int>,
  "best_silhouette_score": <float rounded to 4 decimal places>
}
```

- `best_k`: the K value (from 2, 3, 4, 5) that achieved the highest silhouette score.
- `best_silhouette_score`: the corresponding silhouette score.
- Centroid coordinate floats should be rounded to 4 decimal places.

2. `/app/clusters_k4.png` — Scatter plot of the clustering result for K=4. Each cluster should be shown in a different color, and centroids should be marked distinctly (e.g., with an "X" marker).

3. `/app/elbow_plot.png` — A line plot showing inertia (sum of squared distances of points to their assigned centroid) on the y-axis vs. K values (2, 3, 4, 5) on the x-axis.

4. `/app/silhouette_comparison.png` — A bar chart comparing silhouette scores for K values 2, 3, 4, 5.
