## Text Preprocessing & TF-IDF Recommendation Baseline

Build a content-based product recommendation baseline using TF-IDF vectorization and cosine-similarity nearest neighbours. Implement custom text preprocessing, train/evaluate the model, and log everything with MLflow.

### Technical Requirements

- Language: Python 3
- Libraries: pandas, scikit-learn, nltk, mlflow, matplotlib
- All work under `/app`

### Input

`/app/input.json` — a JSON file containing an array of product objects. Each object has:

| Field        | Type   | Description                        |
|--------------|--------|------------------------------------|
| `product_id` | string | Unique product identifier          |
| `title`      | string | Product title text                 |
| `description`| string | Product description text (may be empty or null) |
| `category`   | string | Product category                   |

Example (minimum 50 records will be provided):
```json
[
  {"product_id": "B001", "title": "Soft Baby Blanket", "description": "Ultra-soft fleece blanket for newborns. Machine washable!", "category": "bedding"},
  {"product_id": "B002", "title": "Baby Bottle Set (3-pack)", "description": null, "category": "feeding"},
  {"product_id": "B003", "title": "Organic Cotton Onesie", "description": "100% organic cotton. Sizes: 0-3mo, 3-6mo.", "category": "clothing"}
]
```

### Text Preprocessing Helper Module

Create `/app/text_preprocessor.py` containing a function:

```
def clean_text(text: str) -> str
```

This function must perform, in order:
1. Lowercasing
2. Punctuation removal (remove all non-alphanumeric characters except spaces)
3. Stop-word removal (using NLTK English stop words)
4. Porter stemming (using NLTK PorterStemmer)

If the input is `None` or empty string, return an empty string `""`.

The module must also contain:

```
def combine_text_fields(row: dict) -> str
```

This function takes a single product dict (with keys `title`, `description`, `category`) and returns a single concatenated string of all three fields separated by spaces, with null/missing values treated as empty strings.

### Pipeline & Evaluation

1. Combine each product's `title`, `description`, and `category` into a single text field using `combine_text_fields`, then clean it with `clean_text`.
2. Build a scikit-learn `Pipeline` with:
   - `TfidfVectorizer` using `clean_text` as a custom tokenizer (via the `tokenizer` parameter, where the tokenizer function accepts a string and returns a list of tokens — i.e., the output of `clean_text` split by whitespace).
   - `NearestNeighbors` with `metric="cosine"` and `n_neighbors=5`.
3. Split data into 80% train / 20% test using `train_test_split` with `random_state=42`.
4. Perform a grid search over these hyperparameters on the training set with 3-fold cross-validation:
   - `tfidf__max_df`: [0.85, 0.95]
   - `tfidf__min_df`: [1, 2]
   - `tfidf__ngram_range`: [(1,1), (1,2)]
5. Fit the best pipeline on the full training set.
6. Evaluate on the test set by computing **Mean Reciprocal Rank @ 5 (MRR@5)**:
   - For each test product, query the fitted model for 5 nearest neighbours from the training set.
   - A neighbour is "relevant" if it shares the same `category` as the query product.
   - Reciprocal rank = `1 / rank_of_first_relevant_neighbour` (0 if none in top 5).
   - MRR@5 = mean of reciprocal ranks across all test products.

### MLflow Logging

- Start an MLflow experiment named `"tfidf_recommendation"` with tracking URI set to `/app/mlruns`.
- Log the following in a single MLflow run:
  - Parameters: best `max_df`, `min_df`, `ngram_range` from grid search.
  - Metric: `mrr_at_5` (the test MRR@5 value).
  - Artifact: the trained pipeline saved as `/app/model.pkl` (using joblib or pickle), logged as an MLflow artifact.
  - Artifact: a bar chart saved as `/app/mrr_distribution.png` showing the distribution of per-query reciprocal ranks on the test set (histogram with 10 bins), logged as an MLflow artifact.

### Output Files

1. `/app/model.pkl` — the trained scikit-learn pipeline (serialized with joblib).

2. `/app/mrr_distribution.png` — the MRR distribution bar chart.

3. `/app/output.json` — a JSON file with this exact structure:
```json
{
  "dataset_stats": {
    "total_records": <int>,
    "train_size": <int>,
    "test_size": <int>,
    "num_categories": <int>,
    "missing_descriptions": <int>
  },
  "best_params": {
    "max_df": <float>,
    "min_df": <int>,
    "ngram_range": [<int>, <int>]
  },
  "mrr_at_5": <float>,
  "mlflow_run_id": "<string>"
}
```

4. `/app/text_preprocessor.py` — the helper module as specified above.
