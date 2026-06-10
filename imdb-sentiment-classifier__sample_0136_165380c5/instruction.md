## Task: Build a Text Sentiment Classifier with Scikit-learn

Build, tune, and evaluate a sentiment-analysis pipeline on the IMDb movie-review dataset, reaching ≥85% accuracy on the held-out test set.

### Technical Requirements

- **Language**: Python 3.x
- **Required Libraries**: scikit-learn, joblib, numpy
- **Input**: IMDb dataset (25k train / 25k test split)
- **Output**:
  - Trained model file: `/app/sentiment_model.joblib`
  - Evaluation results: `/app/results.json`
  - CLI prediction script: `/app/predict.py`

### Implementation Requirements

1. **Data Processing**
   - Download and preprocess the IMDb movie review dataset
   - Use 25,000 reviews for training and 25,000 for testing
   - Handle text cleaning and preparation

2. **Model Pipeline**
   - Implement a scikit-learn pipeline with TfidfVectorizer and LinearSVC
   - Perform hyperparameter tuning using 3-fold cross-validation on training data
   - Tune at minimum: C parameter and n-gram range
   - Train final model on full training set with best parameters

3. **Evaluation**
   - Evaluate on the test set
   - Save results to `/app/results.json` with the following structure:
     ```json
     {
       "accuracy": 0.87,
       "precision": 0.86,
       "recall": 0.88,
       "f1_score": 0.87
     }
     ```
   - Accuracy must be ≥ 0.85

4. **Model Persistence**
   - Save the trained pipeline to `/app/sentiment_model.joblib` using joblib

5. **CLI Prediction Script**
   - Create `/app/predict.py` that loads the trained model
   - Accept text input via command-line argument
   - Output prediction as "positive" or "negative"
   - Example usage: `python /app/predict.py "This movie was amazing!"`
   - Output format: Single line with prediction label

### Deliverables

- `/app/sentiment_model.joblib`: Trained model file
- `/app/results.json`: Evaluation metrics
- `/app/predict.py`: CLI prediction script that accepts text and outputs sentiment classification
