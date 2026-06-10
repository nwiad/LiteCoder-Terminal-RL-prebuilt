Build and evaluate a logistic regression model to predict binary wine quality ('good' vs 'bad') from physicochemical properties using the UCI Wine Quality dataset.

**Technical Requirements:**
- Python 3.x with pandas, numpy, scikit-learn
- Input: Download red wine data from UCI Machine Learning Repository (Wine Quality Data Set)
- Output: Trained model saved to `/app/wine_logreg.pkl` using joblib

**Implementation Requirements:**

1. **Data Acquisition & Preprocessing:**
   - Download the red wine quality dataset from UCI repository
   - Load into pandas DataFrame
   - Create binary target variable: quality ≥ 7 → 1 (good), otherwise → 0 (bad)

2. **Model Training:**
   - Split data: 90% training, 10% test (stratified split, random_state=42)
   - Train scikit-learn LogisticRegression with default parameters on training set
   - Features: all 11 physicochemical properties (fixed acidity, volatile acidity, citric acid, residual sugar, chlorides, free sulfur dioxide, total sulfur dioxide, density, pH, sulphates, alcohol)
   - Target: binary quality label

3. **Model Evaluation:**
   - Perform 5-fold stratified cross-validation on training data
   - Calculate ROC-AUC score for both cross-validation (mean) and test set
   - Both ROC-AUC scores must be ≥ 0.70

4. **Feature Analysis:**
   - Identify top-3 features with largest absolute coefficient values
   - Output format: feature name and coefficient value

5. **Model Persistence:**
   - Save trained LogisticRegression model to `/app/wine_logreg.pkl` using joblib
   - Model must be loadable and produce predictions on new data

**Expected Outputs:**
- Cross-validation ROC-AUC (mean across 5 folds)
- Test set ROC-AUC
- Top-3 most influential features with their coefficients
- Serialized model file at `/app/wine_logreg.pkl`
