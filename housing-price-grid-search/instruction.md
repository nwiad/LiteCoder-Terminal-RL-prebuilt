## Task: Optimized Hyperparameter Grid Search for Housing Prices

Perform hyperparameter grid search on the Boston Housing dataset using Gradient Boosting Regressor to minimize RMSE. Implement cross-validation, track experiments, and generate visualizations and reports.

**Technical Requirements:**
- Python 3.x with scikit-learn, pandas, numpy, matplotlib
- Input: Boston Housing dataset from sklearn.datasets
- Output files in /app directory

**Implementation Requirements:**

1. **Data Preparation:**
   - Load Boston Housing dataset using sklearn.datasets
   - Split into train/test sets (80/20 ratio, random_state=42)

2. **Hyperparameter Grid Search:**
   - Use GradientBoostingRegressor from sklearn.ensemble
   - Define hyperparameter grid with at least 5 different parameters (e.g., n_estimators, learning_rate, max_depth, min_samples_split, subsample)
   - Implement GridSearchCV with 5-fold cross-validation
   - Use n_jobs=-1 for parallel processing

3. **Model Evaluation:**
   - Train using GridSearchCV to find best hyperparameters
   - Evaluate best model on test set
   - Calculate and report RMSE metric

**Output Requirements:**

1. **Model File:** `/app/best_model.pkl`
   - Serialized best model using pickle or joblib

2. **Results File:** `/app/results.json`
   - JSON format containing:
     - `best_params`: Dictionary of best hyperparameters
     - `best_cv_score`: Best cross-validation score
     - `test_rmse`: RMSE on test set
     - `train_rmse`: RMSE on training set

3. **Hyperparameter Performance Plot:** `/app/hyperparameter_analysis.png`
   - Visualization showing how different hyperparameters affect model performance
   - Must include at least 2 key hyperparameters

4. **Learning Curve Plot:** `/app/learning_curve.png`
   - Plot showing training and validation scores vs training set size
   - Must include error bands or confidence intervals

5. **Summary Report:** `/app/summary_report.txt`
   - Plain text format containing:
     - Best hyperparameters found
     - Performance metrics (RMSE on train and test sets)
     - Key findings about hyperparameter impact
     - Recommendations for model deployment

**Data Format Specifications:**

- `results.json` structure:
```json
{
  "best_params": {
    "n_estimators": 100,
    "learning_rate": 0.1,
    ...
  },
  "best_cv_score": -12.345,
  "test_rmse": 3.456,
  "train_rmse": 2.123
}
```

**Edge Cases:**
- Handle deprecated Boston Housing dataset warnings appropriately
- Ensure all output files are created even if performance is suboptimal
- Plots must be saved as PNG files with readable labels and legends
