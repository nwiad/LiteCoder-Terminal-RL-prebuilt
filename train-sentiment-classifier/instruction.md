## Multiclass Text Sentiment Classifier for Product Reviews

Build a reproducible Python script (`/app/train_sentiment.py`) that trains and evaluates a multiclass sentiment classifier on Amazon product reviews using scikit-learn, achieving ≥0.75 macro-averaged F1-score on a hold-out test set.

### Technical Requirements

- **Language:** Python 3.x
- **Core libraries:** scikit-learn, pandas, numpy, matplotlib (or seaborn), joblib (or pickle)
- **No deep-learning frameworks** (PyTorch, TensorFlow, etc.). Only classical ML with scikit-learn pipelines.

### Dataset

Download the Amazon product reviews dataset from:
`https://raw.githubusercontent.com/pycaret/pycaret/master/datasets/amazon.csv`

Save it to `/app/amazon.csv`. The CSV contains at least two columns:
- `reviewText`: the review string
- `overall`: a numeric star rating (1–5)

### Sentiment Mapping

Convert the 5-star `overall` rating into a 3-class `sentiment` label using these exact rules:
- **negative**: `overall` ∈ {1, 2}
- **neutral**: `overall` == 3
- **positive**: `overall` ∈ {4, 5}

### Pipeline Requirements

1. Build a single scikit-learn `Pipeline` object that includes at minimum:
   - A text vectorization step using `TfidfVectorizer`
   - A classifier step (e.g., `LinearSVC`, `SGDClassifier`, `LogisticRegression`, or similar scikit-learn estimator)
2. Perform hyperparameter tuning using `RandomizedSearchCV` with **at least 75 fits** (e.g., `n_iter` × number of CV folds ≥ 75).
3. Use a **stratified 80/20 train/test split** with `random_state=42`.

### Output Files

All output files must be written to `/app/`.

| File | Description |
|------|-------------|
| `/app/train_sentiment.py` | The complete, runnable training script |
| `/app/sentiment_pipeline.pkl` | The best trained pipeline, persisted via `joblib.dump()` or `pickle.dump()` |
| `/app/report.txt` | A text file containing scikit-learn's `classification_report` output on the test set. Must include per-class precision, recall, f1-score for each of the three labels (`negative`, `neutral`, `positive`) and the `macro avg` row. |
| `/app/confusion_matrix.png` | A saved confusion-matrix plot (PNG format) generated from test-set predictions. Axis labels must include the three sentiment class names. |

### Evaluation Criteria

- `/app/train_sentiment.py` runs end-to-end without errors.
- `/app/sentiment_pipeline.pkl` exists and is loadable via `joblib.load()` (or `pickle.load()`). The loaded object must be a scikit-learn `Pipeline` that exposes a `.predict()` method accepting raw text input (list of strings).
- `/app/report.txt` exists and contains a valid classification report with a `macro avg` f1-score ≥ 0.75.
- `/app/confusion_matrix.png` exists and is a valid PNG image file.
- The stratified test split uses `random_state=42` and a test size of 20%.
