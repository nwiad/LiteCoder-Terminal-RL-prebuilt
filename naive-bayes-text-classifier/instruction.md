## Scalable Text Classification Pipeline with Naive Bayes and TF-IDF

Build a reproducible text classification pipeline in Python that classifies research-paper abstracts into Computer Science sub-fields using TF-IDF and Multinomial Naive Bayes via scikit-learn.

### Technical Requirements

- Language: Python 3.x
- Libraries: pandas, scikit-learn, matplotlib, seaborn, numpy, joblib
- All random seeds (`random`, `numpy`) must be set to **42**
- All code must be in a single script: `/app/train.py`
- The script must accept CLI arguments: `--data` (path to input CSV) and `--output-dir` (path to output directory)
- Default values: `--data /app/data.csv`, `--output-dir /app/output`

### Input

A CSV file at `/app/data.csv` with the following columns:

| Column     | Type   | Description                                      |
|------------|--------|--------------------------------------------------|
| `id`       | int    | Unique paper identifier                          |
| `abstract` | string | The research paper abstract text                 |
| `category` | string | CS sub-field label (e.g., `cs.AI`, `cs.CV`, etc.)|

The dataset contains **11,000 abstracts** evenly distributed across **11 CS categories** (1,000 per category). The 11 categories are: `cs.AI`, `cs.CL`, `cs.CR`, `cs.CV`, `cs.DB`, `cs.DS`, `cs.IT`, `cs.LG`, `cs.NI`, `cs.RO`, `cs.SE`.

### Processing Steps

1. Read `/app/data.csv`
2. Split into 80% train / 20% test using stratified splitting (random_state=42)
3. Build a scikit-learn `Pipeline` consisting of `TfidfVectorizer` followed by `MultinomialNB`
4. Tune hyperparameters (`max_df`, `min_df`, `alpha`) using **5-fold stratified cross-validation** on the training set
5. Refit the best model on the full training set and evaluate on the test set

### Output

All outputs go into the directory specified by `--output-dir` (default `/app/output/`):

1. **`model.joblib`** — The trained scikit-learn Pipeline object, saved via `joblib.dump`.

2. **`label_map.json`** — A JSON object mapping each category string to a zero-based integer index, sorted alphabetically by category name. Example structure:
   ```json
   {
     "cs.AI": 0,
     "cs.CL": 1,
     "cs.CR": 2
   }
   ```
   Must contain exactly 11 entries.

3. **`confusion_matrix.png`** — A heatmap image of the confusion matrix on the test set. Must be a valid PNG file.

4. **`report.json`** — A JSON file containing the classification results with the following structure:
   ```json
   {
     "macro_f1": 0.87,
     "accuracy": 0.88,
     "per_class": {
       "cs.AI": {"precision": 0.85, "recall": 0.88, "f1-score": 0.86, "support": 200},
       "cs.CL": {"precision": 0.90, "recall": 0.87, "f1-score": 0.88, "support": 200}
     },
     "train_size": 8800,
     "test_size": 2200
   }
   ```
   - `macro_f1` and `accuracy` are floats rounded to 4 decimal places
   - `per_class` contains an entry for each of the 11 categories
   - Each per-class entry has `precision`, `recall`, `f1-score` (floats rounded to 4 decimal places) and `support` (integer)
   - `train_size` must be 8800 and `test_size` must be 2200

### Constraints

- The pipeline must achieve **macro-F1 ≥ 0.60** on the test set (reported in `report.json` under `macro_f1`)
- The `model.joblib` file must be loadable via `joblib.load()` and must expose a `.predict(X)` method that accepts a list of raw abstract strings and returns predicted category labels
- The script must print the final macro-F1 score to stdout in the format: `Macro-F1: <score>`
- The script must exit with code 0 on successful completion
