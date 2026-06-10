## Customer Churn Prediction with Imbalanced Dataset Handling

Build a customer churn prediction pipeline in Python that generates a synthetic telecom dataset, handles class imbalance, trains multiple models, and evaluates them with emphasis on recall.

### Technical Requirements

- Language: Python 3
- Required libraries: pandas, numpy, scikit-learn, imbalanced-learn, matplotlib, seaborn
- All output files must be written under `/app/`

### Step 1: Generate Synthetic Dataset

Create a synthetic telecom customer churn dataset and save it to `/app/churn_dataset.csv`. The dataset must have:

- At least 5000 rows
- A binary target column named `Churn` with values `1` (churned) and `0` (not churned)
- Approximately 15% churn rate (class imbalance)
- At least the following feature columns:
  - `CustomerID` (unique string identifier)
  - `Tenure` (integer, months with the company)
  - `MonthlyCharges` (float)
  - `TotalCharges` (float)
  - `Contract` (categorical: "Month-to-month", "One year", "Two year")
  - `InternetService` (categorical: "DSL", "Fiber optic", "No")
  - `NumSupportTickets` (integer)
  - `PaymentMethod` (categorical: at least 3 distinct values)
- Introduce missing values in at least 2 numeric columns (between 2% and 10% missing rate per column)

### Step 2: Exploratory Data Analysis

- Save a class distribution bar chart to `/app/class_distribution.png`
- Save a correlation heatmap of numeric features to `/app/correlation_heatmap.png`

### Step 3: Data Preprocessing

- Handle all missing values (imputation or removal)
- Encode categorical features appropriately for model training
- Split data into 80% train and 20% test sets with stratification on the `Churn` column
- Save the processed test set (features only, no target) to `/app/test_features.csv`

### Step 4: Handle Class Imbalance

Apply at least one resampling technique (e.g., SMOTE, random oversampling, or undersampling) on the training data only.

### Step 5: Model Training

Train at least 3 different classification models (e.g., Logistic Regression, Random Forest, Gradient Boosting, SVM, etc.).

### Step 6: Evaluation and Results

Evaluate all models on the held-out test set. Save evaluation results to `/app/evaluation_results.json` with the following structure:

```json
{
  "models": [
    {
      "model_name": "<string>",
      "accuracy": <float>,
      "precision": <float>,
      "recall": <float>,
      "f1_score": <float>,
      "roc_auc": <float>
    }
  ],
  "best_model": "<model_name with highest recall>"
}
```

All metric values must be between 0.0 and 1.0.

Requirements for the best model:
- The `best_model` field must match the `model_name` of the model with the highest `recall` in the `models` list.
- The best model must achieve a recall of at least 0.60 on the test set.

### Step 7: Visualizations

- Save a model performance comparison bar chart (showing recall and F1-score for each model) to `/app/model_comparison.png`
- Save a feature importance chart (from the best model or a tree-based model) to `/app/feature_importance.png`

### Step 8: Predictions and Model Persistence

- Save the best model as a pickle file to `/app/best_model.pkl`
- Generate predictions on the test set using the best model and save to `/app/test_predictions.csv` with columns: `CustomerID`, `Churn_Predicted`, `Churn_Probability`
  - `Churn_Predicted`: integer 0 or 1
  - `Churn_Probability`: float between 0.0 and 1.0 (probability of churn)

### Expected Output Files

| File | Format |
|---|---|
| `/app/churn_dataset.csv` | CSV with header |
| `/app/class_distribution.png` | PNG image |
| `/app/correlation_heatmap.png` | PNG image |
| `/app/test_features.csv` | CSV with header |
| `/app/evaluation_results.json` | JSON |
| `/app/model_comparison.png` | PNG image |
| `/app/feature_importance.png` | PNG image |
| `/app/best_model.pkl` | Pickle file |
| `/app/test_predictions.csv` | CSV with header |
