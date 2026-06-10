## CPU-based Sentiment Analysis with Random Forests

Build a sentiment analysis pipeline that classifies IMDB movie reviews as positive or negative using Random Forest classifiers, comparing TF-IDF and Word2Vec feature extraction approaches.

### Technical Requirements

- Language: Python 3
- Libraries: scikit-learn, pandas, numpy, nltk, gensim
- All processing must be CPU-based (no GPU dependencies)
- Entry point: `/app/solution.py` — running `python solution.py` must produce all output files

### Dataset

Use the IMDB movie reviews dataset (50,000 reviews). Download it programmatically (e.g., via `datasets` library, direct URL, or any reliable source). If download fails, the script should exit with a non-zero exit code and print an error message to stderr.

### Preprocessing

Apply a text preprocessing pipeline to all reviews using NLTK:
1. Convert to lowercase
2. Remove HTML tags
3. Remove non-alphabetic characters
4. Tokenize
5. Remove English stopwords (NLTK stopword list)

### Feature Extraction

1. **TF-IDF**: Fit a TF-IDF vectorizer on the training set with a maximum of 10,000 features.
2. **Word2Vec**: Train a Word2Vec model (vector size 100, window 5, min_count 2) on the training set. Represent each document as the mean of its word vectors. If a document has no known words, represent it as a zero vector.

### Model Training & Evaluation

- Split the dataset into 80% train / 20% test using a fixed `random_state=42`.
- Train a separate `RandomForestClassifier` (with `n_estimators=100`, `random_state=42`) for each feature type.
- Evaluate each model on the test set.

### Output

#### 1. `/app/results.json`

A JSON file with the following exact structure:

```json
{
  "tfidf": {
    "accuracy": <float>,
    "precision": <float>,
    "recall": <float>,
    "f1_score": <float>
  },
  "word2vec": {
    "accuracy": <float>,
    "precision": <float>,
    "recall": <float>,
    "f1_score": <float>
  },
  "best_method": "<string: 'tfidf' or 'word2vec'>"
}
```

- All metric values are floats rounded to 4 decimal places.
- `best_method` is determined by the higher F1 score.

#### 2. `/app/comparison_plot.png`

A grouped bar chart comparing accuracy, precision, recall, and F1 score for both methods. The chart must have:
- A title
- X-axis labels for each metric
- A legend distinguishing TF-IDF and Word2Vec
- Saved as a PNG file

### Performance Expectations

- The TF-IDF model accuracy must be at least 0.80.
- The Word2Vec model accuracy must be at least 0.65.
