## Titanic Survivability Analysis & Prediction Engine

Build an end-to-end machine-learning pipeline that predicts Titanic passenger survival using classical ML models, producing automated insights, evaluation metrics, and a production-ready model artifact.

### Technical Requirements

- Language: Python 3.x
- Key libraries: scikit-learn, pandas, seaborn, matplotlib, joblib
- All work must be CPU-only and fully reproducible (set `random_state=42` for all random seeds)
- Dataset: Titanic dataset from OpenML (dataset ID 40945). Download programmatically via `sklearn.datasets.fetch_openml(name="titanic", version=1, as_frame=True)` or equivalent OpenML API call.
- All output files must be written under `/app/`

### Pipeline Steps

1. **Data Loading & EDA**
   - Load the Titanic dataset programmatically from OpenML.
   - Generate and save the following plots to `/app/plots/`:
     - `missing_values_heatmap.png` — heatmap of missing values
     - `correlation_heatmap.png` — correlation heatmap of numeric features
     - `survival_by_category.png` — survival rate by at least 2 categorical features (e.g., sex, pclass)
     - `age_distribution.png` — age distribution plot

2. **Feature Engineering**
   - Create the following derived features: `Title` (extracted from passenger name), `FamilySize`, `IsAlone` (1 if solo traveler, 0 otherwise), `FarePerPerson`, and `AgeBand` (binned age groups).
   - Handle missing values with appropriate imputation strategies for both numeric and categorical columns.

3. **Model Training & Comparison**
   - Split data into train (80%) and test (20%) sets with `random_state=42`.
   - Build preprocessing pipelines (numeric: impute + scale; categorical: impute + one-hot encode).
   - Train at least 3 candidate models: Logistic Regression, Random Forest, and Gradient Boosting.
   - Perform 5-fold cross-validation on the training set for each model.
   - Save a model comparison table to `/app/model_comparison.csv` with columns: `model_name`, `mean_cv_score`, `std_cv_score`. Rows sorted descending by `mean_cv_score`. Scores should be accuracy values rounded to 4 decimal places.

4. **Evaluation**
   - Evaluate the best model (highest mean CV score) on the held-out test set.
   - Save test-set metrics to `/app/evaluation_metrics.json` with the following structure:
     ```json
     {
       "best_model": "<model name string>",
       "accuracy": <float>,
       "precision": <float>,
       "recall": <float>,
       "f1_score": <float>,
       "roc_auc": <float>
     }
     ```
     All metric values rounded to 4 decimal places.
   - Save plots to `/app/plots/`:
     - `confusion_matrix.png`
     - `feature_importance.png`

5. **Model Persistence & Prediction CLI**
   - Save the best full pipeline (preprocessor + model) to `/app/titanic_pipeline.joblib`.
   - Create `/app/predict.py` — a CLI script that:
     - Reads a single JSON passenger record from stdin
     - Loads `/app/titanic_pipeline.joblib`
     - Prints a JSON object to stdout with the format:
       ```json
       {"survived": <0 or 1>, "survival_probability": <float rounded to 4 decimals>}
       ```
     - Example input (via stdin):
       ```json
       {"pclass": 1, "name": "Smith, Mr. John", "sex": "male", "age": 30, "sibsp": 0, "parch": 0, "fare": 50.0, "embarked": "S"}
       ```
     - Example output:
       ```json
       {"survived": 0, "survival_probability": 0.3241}
       ```

6. **Documentation**
   - Create `/app/requirements.txt` with pinned dependency versions.
   - Create `/app/README.md` documenting setup, training, evaluation metrics, and CLI usage.
   - Create `/app/report.md` summarizing key findings, model comparison, and business implications in non-technical language.

### Output Files Summary

| File | Description |
|---|---|
| `/app/plots/missing_values_heatmap.png` | Missing values heatmap |
| `/app/plots/correlation_heatmap.png` | Correlation heatmap |
| `/app/plots/survival_by_category.png` | Survival rate by categorical features |
| `/app/plots/age_distribution.png` | Age distribution |
| `/app/plots/confusion_matrix.png` | Confusion matrix of best model |
| `/app/plots/feature_importance.png` | Feature importance bar chart |
| `/app/model_comparison.csv` | CV scores for all models |
| `/app/evaluation_metrics.json` | Test-set metrics for best model |
| `/app/titanic_pipeline.joblib` | Serialized best pipeline |
| `/app/predict.py` | CLI prediction script |
| `/app/requirements.txt` | Pinned dependencies |
| `/app/README.md` | Project documentation |
| `/app/report.md` | Non-technical summary report |
