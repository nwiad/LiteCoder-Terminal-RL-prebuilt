## Predictive Customer Churn Analysis

Build a classification pipeline in Python that predicts customer churn using the Telco Customer Churn dataset. Download the data, preprocess it, train at least three models, and produce a set of deliverable artifacts.

### Technical Requirements

- Language: Python 3
- Required libraries: pandas, scikit-learn, xgboost, matplotlib, seaborn, joblib
- Working directory: `/app`

### Step-by-step Requirements

1. **Download the dataset** from `https://huggingface.co/datasets/scikit-learn/churn-prediction` into `/app/customers.csv`. Use the Hugging Face `datasets` library (`load_dataset("scikit-learn/churn-prediction")`) and export the `train` split to CSV format. The resulting CSV must contain all original columns including `customerID` and the target column `Churn`.

2. **Preprocessing pipeline** — Build a scikit-learn `Pipeline` (or `ColumnTransformer`) that:
   - Drops the `customerID` column (not a feature).
   - Imputes missing values for numeric columns (e.g., `TotalCharges` may contain blanks).
   - Scales numeric features.
   - One-hot or ordinal encodes categorical features.
   - Converts the target column `Churn` from `Yes`/`No` strings to binary `1`/`0`.

3. **Train/test split** — Use an 80/20 stratified split with `random_state=42`.

4. **Train at least three classifiers:**
   - Logistic Regression
   - Random Forest
   - XGBoost (gradient boosting)

5. **Evaluate each model** using these metrics: accuracy, precision, recall, F1-score, and ROC-AUC. All metrics must be computed on the test set.

6. **Select the best model** by highest ROC-AUC on the test set.

7. **Output artifacts** — All output files must be saved directly under `/app/`:

   - `/app/model_comparison.csv` — A CSV file with one row per model and the following columns (exact names):
     - `model` — model name string (e.g., `LogisticRegression`, `RandomForest`, `XGBoost`)
     - `accuracy` — float rounded to 4 decimal places
     - `precision` — float rounded to 4 decimal places
     - `recall` — float rounded to 4 decimal places
     - `f1_score` — float rounded to 4 decimal places
     - `roc_auc` — float rounded to 4 decimal places

   - `/app/best_churn_model.pkl` — The best model (by ROC-AUC) serialized with `joblib.dump()`. It must be loadable via `joblib.load()` and expose a `.predict()` and `.predict_proba()` method.

   - `/app/roc_curves.png` — A single plot showing the ROC curve for all three models overlaid, with a legend identifying each model.

   - `/app/feature_importance.png` — A bar chart of feature importances for the best model. If the best model does not natively support `feature_importances_`, use permutation importance instead.

   - `/app/confusion_matrix.png` — A confusion matrix heatmap for the best model on the test set.

   - `/app/README.txt` — A plain text file explaining how to load and use the saved model (at minimum: which library to import, how to load the `.pkl` file, and how to call predict).

### Constraints

- All metric values in `model_comparison.csv` must be between 0.0 and 1.0.
- The `model_comparison.csv` must contain exactly 3 or more rows (one per trained model).
- The best model in `best_churn_model.pkl` must correspond to the model with the highest `roc_auc` value in `model_comparison.csv`.
- All three PNG plot files must be valid image files (non-zero file size).
- `README.txt` must be non-empty and contain the word "joblib" (since that is the serialization method).
