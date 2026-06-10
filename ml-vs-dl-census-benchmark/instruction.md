## Classical ML vs. Deep Learning Benchmark on Census Income Dataset

Compare classical ML models against a deep learning model for binary classification (income >50K vs ≤50K) on the UCI Adult dataset. Produce a structured JSON report of all evaluation metrics and save trained model predictions.

### Technical Requirements

- Language: Python 3.x
- Use scikit-learn for classical ML models and PyTorch or TensorFlow/Keras for the deep learning model.
- All work in `/app/`. The main script must be `/app/benchmark.py`.

### Data

- Download the UCI Adult dataset programmatically (from `https://archive.ics.uci.edu/ml/machine-learning-databases/adult/adult.data` and `adult.test`), or use `sklearn.datasets.fetch_openml("adult", version=2)` or any equivalent method.
- The dataset has 14 features and a binary target label (`>50K` / `<=50K`).

### Preprocessing

- Handle missing values (marked as `?` or `NaN`) by dropping rows or imputing — document which strategy is used.
- Encode categorical features numerically (one-hot or label encoding).
- Standardize/normalize numerical features.
- Use an 80/20 train-test split with `random_state=42`.

### Models to Train

Train exactly these four models:

1. **Logistic Regression** — key: `logistic_regression`
2. **Random Forest** — key: `random_forest`
3. **Gradient Boosting** — key: `gradient_boosting`
4. **Multi-layer Perceptron (deep learning)** — key: `mlp`

The MLP must have at least 2 hidden layers and use a deep learning framework (PyTorch or TensorFlow/Keras), not `sklearn.neural_network.MLPClassifier`.

### Evaluation Metrics

Evaluate every model on the test set using:
- Accuracy
- Precision (weighted)
- Recall (weighted)
- F1-score (weighted)
- ROC-AUC

### Output Files

1. `/app/results.json` — Main results file with the following structure:

```json
{
  "models": {
    "logistic_regression": {
      "accuracy": <float>,
      "precision": <float>,
      "recall": <float>,
      "f1_score": <float>,
      "roc_auc": <float>
    },
    "random_forest": {
      "accuracy": <float>,
      "precision": <float>,
      "recall": <float>,
      "f1_score": <float>,
      "roc_auc": <float>
    },
    "gradient_boosting": {
      "accuracy": <float>,
      "precision": <float>,
      "recall": <float>,
      "f1_score": <float>,
      "roc_auc": <float>
    },
    "mlp": {
      "accuracy": <float>,
      "precision": <float>,
      "recall": <float>,
      "f1_score": <float>,
      "roc_auc": <float>
    }
  },
  "best_model": "<key of model with highest roc_auc>",
  "feature_importance": {
    "model": "random_forest",
    "top_5_features": ["<feature_name>", "<feature_name>", "<feature_name>", "<feature_name>", "<feature_name>"]
  }
}
```

All metric floats must be rounded to 4 decimal places. The `best_model` field must contain the key of the model with the highest `roc_auc`. The `top_5_features` list must contain the top 5 most important features from the Random Forest model, ordered by descending importance.

2. `/app/predictions.csv` — CSV file with columns: `model`, `y_true`, `y_pred`, `y_prob`. Each model's test-set predictions are appended as rows. `y_true` and `y_pred` are integer labels (0 or 1). `y_prob` is the predicted probability for the positive class (>50K), rounded to 4 decimal places.

3. `/app/comparison_chart.png` — A bar chart comparing ROC-AUC scores across all four models. Each bar must be labeled with the model name.

### Constraints

- All metric values (accuracy, precision, recall, f1_score, roc_auc) must be between 0.0 and 1.0.
- Every model must achieve an accuracy of at least 0.75 on the test set.
- `/app/results.json` must be valid JSON and parseable.
- `/app/predictions.csv` must contain exactly `4 * N_test` rows (excluding header), where `N_test` is the number of test samples.
- Running `python /app/benchmark.py` must produce all three output files without error.
