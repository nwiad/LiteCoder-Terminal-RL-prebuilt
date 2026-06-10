## Train a Binary Text Sentiment Classifier with NLTK Movie Reviews Dataset

Build, evaluate, and optimize a binary sentiment classifier (positive vs. negative) for movie reviews using the NLTK `movie_reviews` corpus, achieving ≥ 80% accuracy on the test split. Write a Python script `/app/solution.py` that, when executed, performs the full pipeline and produces all required output files.

### Technical Requirements

- Language: Python 3.x
- Libraries: `nltk`, `scikit-learn`, `pandas`, `joblib` (additional libraries like `matplotlib`, `seaborn` are allowed but not required)
- The script must download the NLTK `movie_reviews` corpus and `punkt` tokenizer automatically if not already present
- All processing must run on CPU

### Pipeline Requirements

1. **Data Loading**: Load the NLTK `movie_reviews` corpus (1000 positive, 1000 negative reviews).

2. **Text Preprocessing**: Apply a cleaning pipeline that includes at minimum: lower-casing and removal of non-alphabetic tokens.

3. **Train/Test Split**: Split the data into train and test sets using an 80/20 ratio with stratification on the label. Use `random_state=42` for reproducibility.

4. **Vectorization and Classification**: Train at least one vectorizer + classifier combination. At minimum, evaluate TF-IDF vectorization with one of: Multinomial Naive Bayes, Logistic Regression, or Linear SVM.

5. **Hyperparameter Tuning**: Perform hyperparameter tuning (e.g., GridSearchCV or similar) on the training set to optimize the pipeline.

6. **Evaluation**: Evaluate the final tuned model on the held-out test set.

### Output Files

All output files must be written to `/app/`.

1. **`/app/metrics.json`** — A JSON file containing test-set evaluation metrics with the following structure:
   ```json
   {
     "accuracy": 0.85,
     "macro_f1": 0.85,
     "model_name": "LogisticRegression"
   }
   ```
   - `accuracy`: float, test-set accuracy (must be ≥ 0.80)
   - `macro_f1`: float, macro-averaged F1 score
   - `model_name`: string, name of the classifier used (e.g., `"LogisticRegression"`, `"MultinomialNB"`, `"LinearSVC"`)

2. **`/app/predictions.csv`** — A CSV file with test-set predictions containing these columns:
   - `text`: the original review text
   - `true_label`: the ground-truth label (`"pos"` or `"neg"`)
   - `predicted_label`: the model's predicted label (`"pos"` or `"neg"`)

   The file must have a header row and one row per test sample.

3. **`/app/model.joblib`** — The final trained pipeline (vectorizer + classifier) serialized using `joblib.dump()`. The saved object must be loadable with `joblib.load()` and support a `.predict()` method that accepts a list of raw text strings and returns predicted labels.

### Constraints

- Test-set accuracy must be ≥ 0.80.
- The `predictions.csv` must contain exactly as many data rows as there are test samples.
- Labels in `predictions.csv` must use the strings `"pos"` and `"neg"` only.
- The `model.joblib` file must be a scikit-learn Pipeline or equivalent object that can vectorize and classify raw text input in a single `.predict()` call.
