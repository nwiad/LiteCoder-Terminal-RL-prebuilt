## Classical ML vs. Deep Learning Accuracy Duel on Tabular Titanic

Benchmark the generalization accuracy of a classical ML pipeline (feature-engineering + Gradient-Boosting) against a simple Multilayer Perceptron (MLP) on the Titanic dataset, producing a structured comparison report.

### Technical Requirements

- Language: Python 3.x
- Input: `/app/data/train.csv` (Titanic training data with columns: PassengerId, Survived, Pclass, Name, Sex, Age, SibSp, Parch, Ticket, Fare, Cabin, Embarked)
- The input CSV uses standard Titanic dataset schema. `Survived` is the binary target (0 or 1).

### Pipeline Requirements

1. **Data Split**: Create a deterministic 80/20 train/validation split using `random_state=42`. Save the split indices to `/app/data/split_indices.json` as a JSON object with keys `"train_indices"` and `"val_indices"`, each containing a list of integer row indices.

2. **Gradient-Boosting Model**:
   - Build a feature-engineering + Gradient-Boosting pipeline (any GB library: scikit-learn, XGBoost, LightGBM, etc.).
   - Evaluate with 5-fold stratified cross-validation on the training portion (80%) using `random_state=42`.
   - Save the best model to `/app/models/gb_best.joblib`.

3. **MLP Model**:
   - Design a compact MLP with at most 3 hidden layers.
   - Use early stopping based on validation loss.
   - Evaluate with the same 5-fold stratified CV strategy and `random_state=42`.
   - Save the best model to `/app/models/mlp_best.pt`.

4. **Evaluation on Hold-out Set**: Evaluate both final models on the 20% validation split. Compute: Accuracy, Precision, Recall, F1, and AUC (ROC-AUC).

5. **Plots**:
   - Save learning curves (training vs. validation loss per epoch/iteration) for both models to `/app/plots/learning_curves.png`.
   - Save ROC curves for both models (on the hold-out 20% split) to `/app/plots/roc_curves.png`.

6. **Results File**: Write `/app/results.json` with the following exact structure:

```json
{
  "gradient_boosting": {
    "cv_accuracy_mean": <float>,
    "cv_accuracy_std": <float>,
    "holdout_accuracy": <float>,
    "holdout_precision": <float>,
    "holdout_recall": <float>,
    "holdout_f1": <float>,
    "holdout_auc": <float>
  },
  "mlp": {
    "cv_accuracy_mean": <float>,
    "cv_accuracy_std": <float>,
    "holdout_accuracy": <float>,
    "holdout_precision": <float>,
    "holdout_recall": <float>,
    "holdout_f1": <float>,
    "holdout_auc": <float>
  }
}
```

All float values must be rounded to 4 decimal places. Metrics use scikit-learn conventions (binary classification, positive label = 1).

7. **Requirements File**: Pin all non-system package versions in `/app/requirements.txt`.

### Output Files Summary

| File | Description |
|---|---|
| `/app/data/split_indices.json` | Train/val split indices |
| `/app/models/gb_best.joblib` | Best Gradient-Boosting model |
| `/app/models/mlp_best.pt` | Best MLP model |
| `/app/plots/learning_curves.png` | Learning curves for both models |
| `/app/plots/roc_curves.png` | ROC curves for both models |
| `/app/results.json` | Structured metrics comparison |
| `/app/requirements.txt` | Pinned dependencies |
