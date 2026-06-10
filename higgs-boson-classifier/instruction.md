Build a machine learning pipeline to classify Higgs boson events from background noise using the UCI Higgs dataset, achieving specific performance metrics and generating analysis artifacts.

**Technical Requirements:**
- Python 3.x
- Input: UCI Higgs dataset (download from UCI ML Repository or use provided data)
- Output directory: /app/output/
- Required libraries: scikit-learn, xgboost or lightgbm, optuna, shap, pandas, numpy

**Dataset Specifications:**
- Use the UCI Higgs Boson Machine Learning dataset (11 million events, 28 features)
- Split: 67% training/validation, 33% test (held-out)
- Missing values are encoded as -999.0
- Target variable: binary classification (signal=1, background=0)

**Implementation Requirements:**

1. **Data Processing:**
   - Load and split the dataset into train/validation/test sets
   - Handle -999.0 missing value flags appropriately
   - Apply feature scaling/normalization

2. **Baseline Model:**
   - Train a scikit-learn GradientBoostingClassifier with: learning_rate=0.1, n_estimators=100, max_depth=3, subsample=0.5
   - Evaluate using Approximate Median Significance (AMS) metric
   - Save baseline AMS score to /app/output/baseline_ams.txt (single float value)

3. **Optimized Model:**
   - Train XGBoost or LightGBM model with hyperparameter optimization
   - Use Bayesian optimization (optuna) to tune hyperparameters
   - Achieve test set AMS ≥ 0.85
   - Save final test AMS score to /app/output/final_ams.txt (single float value)

4. **Feature Importance Analysis:**
   - Compute permutation feature importance and SHAP values
   - Generate visualization showing top-15 most important features
   - Save figure to /app/output/feature_importance.png
   - Save feature importance data to /app/output/feature_importance.csv with columns: feature_name, importance_score

5. **Model Artifacts:**
   - Save trained model to /app/output/model.pkl
   - Save preprocessing pipeline to /app/output/preprocessor.pkl
   - Create /app/output/metrics.json containing: {"baseline_ams": float, "final_ams": float, "n_features": int, "test_size": int}

**Output Format:**

/app/output/baseline_ams.txt - Single line with baseline AMS score (e.g., "0.834")
/app/output/final_ams.txt - Single line with final AMS score (e.g., "0.856")
/app/output/feature_importance.png - Horizontal bar chart (PNG format)
/app/output/feature_importance.csv - CSV with header row
/app/output/metrics.json - Valid JSON object
/app/output/model.pkl - Serialized model (pickle format)
/app/output/preprocessor.pkl - Serialized preprocessor (pickle format)

**Performance Target:**
- Final model must achieve AMS ≥ 0.85 on the held-out test set
