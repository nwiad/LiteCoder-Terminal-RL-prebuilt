## Analyze Wine Quality Dataset and Build Predictive Model

Perform exploratory data analysis on the UCI Wine Quality dataset (red and white wines) and build a classification model to predict wine quality ratings. Write a Python script `/app/solution.py` that, when executed, produces all required outputs.

### Technical Requirements
- Language: Python 3
- Input data: Download the red and white wine quality datasets from the UCI Machine Learning Repository:
  - Red: `https://archive.ics.uci.edu/ml/machine-learning-databases/wine-quality/winequality-red.csv`
  - White: `https://archive.ics.uci.edu/ml/machine-learning-databases/wine-quality/winequality-white.csv`
  - Both files are semicolon-delimited CSVs with a header row.
- The datasets contain 12 columns: `fixed acidity`, `volatile acidity`, `citric acid`, `residual sugar`, `chlorides`, `free sulfur dioxide`, `total sulfur dioxide`, `density`, `pH`, `sulphates`, `alcohol`, and `quality` (integer target, range 3-9).

### Required Steps

1. **Data Loading & Validation**: Load both datasets. Add a column `wine_type` with values `"red"` or `"white"`. Combine into a single DataFrame.

2. **Exploratory Data Analysis**: Compute summary statistics (mean, std, min, max) for all numeric features. Check for missing values.

3. **Data Preparation**: Handle any missing values. Split the combined dataset into training (80%) and testing (20%) sets using stratified splitting on the `quality` column with `random_state=42`.

4. **Model Training**: Train at least three classifiers — Random Forest, SVM, and Logistic Regression — on the training set to predict `quality`.

5. **Evaluation**: Evaluate each model on the test set. Compute accuracy and macro-averaged F1 score for each model. Select the best model by highest accuracy on the test set.

6. **Feature Importance**: Extract feature importance rankings from the best model (or from the Random Forest model if the best model does not natively support feature importances). Report the top 5 most important features.

### Output Requirements

1. **`/app/output.json`** — A JSON file with the following structure:
```json
{
  "dataset_info": {
    "total_samples": <int>,
    "red_samples": <int>,
    "white_samples": <int>,
    "num_features": <int>,
    "missing_values": <int>
  },
  "model_results": [
    {
      "model_name": "<string>",
      "accuracy": <float>,
      "f1_macro": <float>
    }
  ],
  "best_model": {
    "model_name": "<string>",
    "accuracy": <float>,
    "f1_macro": <float>
  },
  "top_features": [
    {"feature": "<string>", "importance": <float>},
    {"feature": "<string>", "importance": <float>},
    {"feature": "<string>", "importance": <float>},
    {"feature": "<string>", "importance": <float>},
    {"feature": "<string>", "importance": <float>}
  ]
}
```
- `model_results` must contain exactly 3 entries (one per model), each with `model_name` being one of `"RandomForest"`, `"SVM"`, `"LogisticRegression"`.
- `accuracy` and `f1_macro` are floats rounded to 4 decimal places.
- `top_features` contains exactly 5 items sorted by importance descending.
- `num_features` counts only the input features (excluding `quality` and `wine_type`).

2. **`/app/best_model.pkl`** — The trained best model serialized via `joblib` or `pickle`.
