## Analyze Product Review Sentiment & Performance

Build a sentiment-analysis pipeline that downloads an Amazon product-review dataset, trains a text classifier, evaluates it with per-class metrics, and visualizes results.

### Technical Requirements

- Language: Python 3.x
- Allowed libraries: pandas, scikit-learn, matplotlib, seaborn, and any standard-library modules. You may use additional pip-installable packages if needed.
- Dataset: Download from `https://raw.githubusercontent.com/justmarkham/DAT8/master/data/amazon_baby.csv` and save to `/app/amazon_baby.csv`.

### Pipeline Steps

1. **Data Loading & EDA**
   - Load the CSV into a pandas DataFrame. The file has columns including `review` (text) and `rating` (1–5 integer).
   - Drop any rows where `review` is missing/NaN.
   - Save a JSON summary of the exploratory analysis to `/app/eda_summary.json` with the following keys:
     - `total_rows`: integer, number of rows after dropping missing reviews
     - `rating_distribution`: object mapping each rating (as string key "1"–"5") to its count
     - `num_categories`: integer, number of unique product categories (column name may vary — use whichever column represents the product category; if none exists, set to `null`)

2. **Sentiment Labeling & Splitting**
   - Map ratings to 3 sentiment classes: `"negative"` (rating 1–2), `"neutral"` (rating 3), `"positive"` (rating 4–5).
   - Split data into train/test sets with a 80/20 ratio, stratified by sentiment label, using `random_state=42`.

3. **Model Training**
   - Train a text classification model (e.g., TF-IDF + classifier) on the training set to predict the 3 sentiment classes.
   - The model must achieve a macro-averaged F1 score of at least **0.55** on the test set.

4. **Evaluation**
   - Evaluate the model on the test set and save results to `/app/evaluation.json` with the following structure:
     ```json
     {
       "accuracy": <float, rounded to 4 decimal places>,
       "macro_f1": <float, rounded to 4 decimal places>,
       "per_class": {
         "negative": {"precision": <float>, "recall": <float>, "f1": <float>},
         "neutral": {"precision": <float>, "recall": <float>, "f1": <float>},
         "positive": {"precision": <float>, "recall": <float>, "f1": <float>}
       }
     }
     ```
     All floats in `per_class` should also be rounded to 4 decimal places.

5. **Visualizations** — Save the following plots:
   - `/app/sentiment_distribution.png`: Bar chart showing the count of each sentiment class across the full dataset.
   - `/app/confusion_matrix.png`: Confusion matrix heatmap of test-set predictions. Axis labels must be the three sentiment class names.

6. **Export**
   - Save the test-set predictions to `/app/predictions.csv` with columns:
     - `review`: the original review text
     - `true_label`: the ground-truth sentiment label
     - `predicted_label`: the model's predicted sentiment label

### Output Files Summary

| File | Format |
|---|---|
| `/app/amazon_baby.csv` | Downloaded raw CSV |
| `/app/eda_summary.json` | JSON |
| `/app/evaluation.json` | JSON |
| `/app/sentiment_distribution.png` | PNG image |
| `/app/confusion_matrix.png` | PNG image |
| `/app/predictions.csv` | CSV with header |
