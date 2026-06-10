## Build a Sentiment Analysis Pipeline with scikit-learn

Train, evaluate, and save a scikit-learn sentiment classifier on a provided movie-review dataset, then expose it through a command-line prediction script.

### Technical Requirements

- Language: Python 3
- Libraries: scikit-learn, pandas, joblib (save all dependencies to `/app/requirements.txt`)
- Working directory: `/app`

### Input

A CSV file at `/app/data/reviews.csv` with the following columns:

| Column    | Type   | Description                          |
|-----------|--------|--------------------------------------|
| review    | string | The text of the movie review         |
| sentiment | string | Label: `"positive"` or `"negative"` |
| split     | string | `"train"` or `"test"`                |

The dataset contains at least 200 rows (roughly balanced between positive and negative, and between train and test splits).

### Tasks

1. **Data Loading**: Read `/app/data/reviews.csv` and split it into train and test sets based on the `split` column.

2. **Pipeline Construction**: Build a scikit-learn `Pipeline` that includes:
   - TF-IDF vectorization with `max_features=10000` and English stop-word removal
   - A classifier component

3. **Classifier Benchmarking**: Benchmark at least three classifiers — Logistic Regression, Multinomial Naive Bayes, and Linear SVM — using 3-fold cross-validation on the training set. Write results to `/app/results.txt` with one line per classifier in the format:
   ```
   <ClassifierName>: mean=<X.XXXX>, std=<X.XXXX>
   ```
   Each line must contain the classifier name, a `mean=` value (4 decimal places), and a `std=` value (4 decimal places). There must be at least 3 such lines.

4. **Hyperparameter Tuning**: Perform randomized search (`n_iter>=10`, 3-fold CV) on the best-performing classifier from step 3. Save the final tuned pipeline (the full pipeline including TF-IDF and classifier) to `/app/sentiment_model.joblib` using `joblib.dump`.

5. **Test Evaluation**: Train the tuned pipeline on the full training split, evaluate on the test split, and write the test accuracy to `/app/test_accuracy.txt` as a single line:
   ```
   Test accuracy: <X.XXXX>
   ```
   The value must be a float rounded to 4 decimal places (e.g., `Test accuracy: 0.7850`). The accuracy must be above `0.55` (better than random).

6. **CLI Prediction Script**: Create `/app/predict.py` that:
   - Loads the model from `/app/sentiment_model.joblib`
   - Accepts a review text as a command-line argument
   - Prints exactly one line to stdout: either `positive` or `negative` (lowercase, no extra whitespace)
   - Example usage: `python predict.py "This movie was absolutely wonderful"`
   - Example output: `positive`

### Output Files

| File                          | Description                                      |
|-------------------------------|--------------------------------------------------|
| `/app/results.txt`            | Cross-validation results for each classifier     |
| `/app/sentiment_model.joblib` | Serialized best pipeline (loadable via `joblib.load`) |
| `/app/test_accuracy.txt`      | Single line with test accuracy                   |
| `/app/predict.py`             | CLI script for single-review prediction          |
| `/app/requirements.txt`       | Python dependencies                              |
