## Task: End-to-End News Article Topic Classifier

Build a CPU-based news article topic classifier pipeline that processes articles, trains a model, and achieves ≥0.85 macro-averaged F1 score on a test split.

**Technical Requirements:**
- Python 3.x
- CPU-only execution (no GPU dependencies)
- Required libraries: pandas, scikit-learn, nltk, joblib, tqdm
- Input: BBC News classification dataset (CSV format with 'text' and 'category' columns)
- Dataset URL: https://www.kaggle.com/datasets/syedalirocks/bbc-news-classificationdataset

**Input Specifications:**
- Dataset file: `/app/bbc-news.csv`
- CSV columns: `text` (article content), `category` (label)
- Expected categories: politics, technology, sports, business, entertainment

**Output Specifications:**
- Classification report: `/app/outputs/classification_report.txt`
  - Must include: precision, recall, f1-score, support for each class
  - Must include: macro-averaged F1 score
- Trained model: `/app/outputs/model.joblib`
- Trained vectorizer: `/app/outputs/vectorizer.joblib`
- All output files must be saved under `/app/outputs/` directory

**Implementation Requirements:**

1. **Data Preprocessing:**
   - Text cleaning: lowercase conversion, HTML tag removal, stop-word removal, lemmatization
   - Data split: 80% train, 10% validation, 10% test (use random_state=42 for reproducibility)

2. **Feature Engineering:**
   - TF-IDF vectorization with max_features=20000, ngram_range=(1,2)

3. **Model Training:**
   - Linear SVM classifier with C=1.0
   - Train on training set, tune on validation set, evaluate on test set

4. **Performance Requirement:**
   - Macro-averaged F1 score on test set must be ≥ 0.85

5. **Execution:**
   - Pipeline must be executable via: `python /app/main.py`
   - Script must handle dataset download, preprocessing, training, and evaluation end-to-end

**Output Format:**
The classification report must contain at minimum:
```
              precision    recall  f1-score   support

   business       X.XX      X.XX      X.XX       XXX
entertainment       X.XX      X.XX      X.XX       XXX
   politics       X.XX      X.XX      X.XX       XXX
      sports       X.XX      X.XX      X.XX       XXX
 technology       X.XX      X.XX      X.XX       XXX

   macro avg       X.XX      X.XX      X.XX       XXX
```
