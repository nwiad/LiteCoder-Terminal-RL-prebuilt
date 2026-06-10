"""
Tests for the Multiclass Text Sentiment Classifier task.

Validates that the agent produced all required output files with correct
format, structure, and quality (macro F1 >= 0.75).
"""

import os
import re
import ast

# All output files live under /app
APP_DIR = "/app"

REPORT_PATH = os.path.join(APP_DIR, "report.txt")
PIPELINE_PATH = os.path.join(APP_DIR, "sentiment_pipeline.pkl")
CONFUSION_MATRIX_PATH = os.path.join(APP_DIR, "confusion_matrix.png")
TRAIN_SCRIPT_PATH = os.path.join(APP_DIR, "train_sentiment.py")

EXPECTED_LABELS = {"negative", "neutral", "positive"}


# =========================================================================
# 1. File existence tests
# =========================================================================

def test_train_script_exists():
    """train_sentiment.py must exist."""
    assert os.path.isfile(TRAIN_SCRIPT_PATH), (
        f"Training script not found at {TRAIN_SCRIPT_PATH}"
    )


def test_pipeline_file_exists():
    """sentiment_pipeline.pkl must exist."""
    assert os.path.isfile(PIPELINE_PATH), (
        f"Pipeline file not found at {PIPELINE_PATH}"
    )


def test_report_file_exists():
    """report.txt must exist."""
    assert os.path.isfile(REPORT_PATH), (
        f"Report file not found at {REPORT_PATH}"
    )


def test_confusion_matrix_file_exists():
    """confusion_matrix.png must exist."""
    assert os.path.isfile(CONFUSION_MATRIX_PATH), (
        f"Confusion matrix image not found at {CONFUSION_MATRIX_PATH}"
    )


# =========================================================================
# 2. File non-emptiness tests
# =========================================================================

def test_train_script_not_empty():
    """train_sentiment.py must not be empty."""
    assert os.path.getsize(TRAIN_SCRIPT_PATH) > 100, (
        "Training script is empty or suspiciously small"
    )


def test_pipeline_file_not_empty():
    """sentiment_pipeline.pkl must not be empty."""
    assert os.path.getsize(PIPELINE_PATH) > 100, (
        "Pipeline pickle file is empty or suspiciously small"
    )


def test_report_file_not_empty():
    """report.txt must not be empty."""
    assert os.path.getsize(REPORT_PATH) > 50, (
        "Report file is empty or suspiciously small"
    )


def test_confusion_matrix_not_empty():
    """confusion_matrix.png must not be empty."""
    assert os.path.getsize(CONFUSION_MATRIX_PATH) > 1000, (
        "Confusion matrix PNG is empty or suspiciously small"
    )


# =========================================================================
# 3. train_sentiment.py validity
# =========================================================================

def test_train_script_valid_python():
    """train_sentiment.py must be syntactically valid Python."""
    with open(TRAIN_SCRIPT_PATH, "r") as f:
        source = f.read()
    # ast.parse will raise SyntaxError if invalid
    ast.parse(source)


def test_train_script_uses_tfidf():
    """train_sentiment.py must reference TfidfVectorizer."""
    with open(TRAIN_SCRIPT_PATH, "r") as f:
        source = f.read()
    assert "TfidfVectorizer" in source, (
        "Training script does not use TfidfVectorizer as required"
    )


def test_train_script_uses_pipeline():
    """train_sentiment.py must reference sklearn Pipeline."""
    with open(TRAIN_SCRIPT_PATH, "r") as f:
        source = f.read()
    assert "Pipeline" in source, (
        "Training script does not use sklearn Pipeline as required"
    )


def test_train_script_uses_randomized_search():
    """train_sentiment.py must reference RandomizedSearchCV."""
    with open(TRAIN_SCRIPT_PATH, "r") as f:
        source = f.read()
    assert "RandomizedSearchCV" in source, (
        "Training script does not use RandomizedSearchCV as required"
    )


def test_train_script_uses_random_state_42():
    """train_sentiment.py must use random_state=42 for reproducibility."""
    with open(TRAIN_SCRIPT_PATH, "r") as f:
        source = f.read()
    assert "random_state=42" in source or "random_state = 42" in source, (
        "Training script does not set random_state=42"
    )


# =========================================================================
# 4. report.txt content validation
# =========================================================================

def _read_report():
    with open(REPORT_PATH, "r") as f:
        return f.read()


def test_report_contains_negative_class():
    """report.txt must contain metrics for the 'negative' class."""
    report = _read_report()
    assert "negative" in report.lower(), (
        "Report does not contain 'negative' class"
    )


def test_report_contains_neutral_class():
    """report.txt must contain metrics for the 'neutral' class."""
    report = _read_report()
    assert "neutral" in report.lower(), (
        "Report does not contain 'neutral' class"
    )


def test_report_contains_positive_class():
    """report.txt must contain metrics for the 'positive' class."""
    report = _read_report()
    assert "positive" in report.lower(), (
        "Report does not contain 'positive' class"
    )


def test_report_contains_macro_avg():
    """report.txt must contain a 'macro avg' row."""
    report = _read_report()
    assert "macro avg" in report.lower(), (
        "Report does not contain 'macro avg' row"
    )


def test_report_contains_precision_recall_f1_headers():
    """report.txt must contain precision, recall, f1-score columns."""
    report = _read_report().lower()
    assert "precision" in report, "Report missing 'precision' header"
    assert "recall" in report, "Report missing 'recall' header"
    assert "f1-score" in report, "Report missing 'f1-score' header"


def test_report_macro_f1_at_least_075():
    """The macro-averaged F1-score in report.txt must be >= 0.75."""
    report = _read_report()
    # Find the macro avg line and extract the f1-score
    # Typical format: "macro avg    0.80    0.79    0.79    1234"
    macro_line = None
    for line in report.strip().split("\n"):
        if "macro avg" in line.lower():
            macro_line = line
            break

    assert macro_line is not None, "Could not find 'macro avg' line in report"

    # Extract all float values from the macro avg line
    floats = re.findall(r"\d+\.\d+", macro_line)
    assert len(floats) >= 3, (
        f"Expected at least 3 float values (precision, recall, f1) in macro avg line, "
        f"got {len(floats)}: {macro_line}"
    )

    # The third float is the f1-score (precision, recall, f1-score, support)
    macro_f1 = float(floats[2])
    assert macro_f1 >= 0.75, (
        f"Macro-averaged F1-score is {macro_f1:.4f}, which is below the 0.75 threshold"
    )


def test_report_f1_scores_are_valid():
    """All F1 scores in the report must be between 0 and 1."""
    report = _read_report()
    for label in ["negative", "neutral", "positive"]:
        for line in report.strip().split("\n"):
            if label in line.lower():
                floats = re.findall(r"\d+\.\d+", line)
                for val_str in floats:
                    val = float(val_str)
                    # Support column can be > 1 (it's a count), so only check
                    # values that look like scores (< 2.0 to be safe)
                    if val < 2.0:
                        assert 0.0 <= val <= 1.0, (
                            f"Invalid score {val} found for class '{label}'"
                        )
                break


# =========================================================================
# 5. sentiment_pipeline.pkl validation
# =========================================================================

def test_pipeline_is_loadable():
    """sentiment_pipeline.pkl must be loadable via joblib or pickle."""
    loaded = _load_pipeline()
    assert loaded is not None, "Failed to load pipeline"


def _load_pipeline():
    """Helper to load the pipeline, trying joblib first then pickle."""
    try:
        import joblib
        return joblib.load(PIPELINE_PATH)
    except Exception:
        pass
    try:
        import pickle
        with open(PIPELINE_PATH, "rb") as f:
            return pickle.load(f)
    except Exception as e:
        raise AssertionError(f"Cannot load pipeline with joblib or pickle: {e}")


def test_pipeline_is_sklearn_pipeline():
    """The loaded object must be a sklearn Pipeline."""
    from sklearn.pipeline import Pipeline
    loaded = _load_pipeline()
    assert isinstance(loaded, Pipeline), (
        f"Loaded object is {type(loaded).__name__}, not a sklearn Pipeline"
    )


def test_pipeline_has_predict_method():
    """The pipeline must expose a .predict() method."""
    loaded = _load_pipeline()
    assert hasattr(loaded, "predict") and callable(loaded.predict), (
        "Pipeline does not have a callable .predict() method"
    )


def test_pipeline_contains_tfidf_step():
    """The pipeline must contain a TfidfVectorizer step."""
    from sklearn.feature_extraction.text import TfidfVectorizer
    loaded = _load_pipeline()
    has_tfidf = False
    for name, step in loaded.steps:
        if isinstance(step, TfidfVectorizer):
            has_tfidf = True
            break
    assert has_tfidf, (
        "Pipeline does not contain a TfidfVectorizer step"
    )


def test_pipeline_accepts_raw_text():
    """The pipeline must accept raw text (list of strings) as input."""
    loaded = _load_pipeline()
    test_texts = [
        "This product is wonderful and I love it",
        "Terrible quality, broke after one day",
        "It is okay, nothing special",
    ]
    try:
        predictions = loaded.predict(test_texts)
    except Exception as e:
        raise AssertionError(
            f"Pipeline failed to predict on raw text input: {e}"
        )
    assert len(predictions) == 3, (
        f"Expected 3 predictions, got {len(predictions)}"
    )


def test_pipeline_predicts_valid_labels():
    """Pipeline predictions must be from {negative, neutral, positive}."""
    loaded = _load_pipeline()
    test_texts = [
        "Absolutely fantastic, best purchase ever!",
        "Worst product I have ever bought, total waste of money",
        "Average product, does the job but nothing more",
        "I love this so much, highly recommend",
        "Broken on arrival, very disappointed",
    ]
    predictions = loaded.predict(test_texts)
    pred_set = set(predictions)
    assert pred_set.issubset(EXPECTED_LABELS), (
        f"Predictions contain invalid labels: {pred_set - EXPECTED_LABELS}. "
        f"Expected only {EXPECTED_LABELS}"
    )


def test_pipeline_positive_review_prediction():
    """A clearly positive review should be predicted as 'positive'."""
    loaded = _load_pipeline()
    strongly_positive = [
        "This is the best product I have ever purchased! Amazing quality, "
        "fast shipping, and it works perfectly. I would buy this again "
        "in a heartbeat. Highly recommended to everyone!"
    ]
    preds = loaded.predict(strongly_positive)
    assert preds[0] == "positive", (
        f"Strongly positive review predicted as '{preds[0]}' instead of 'positive'"
    )


def test_pipeline_negative_review_prediction():
    """A clearly negative review should be predicted as 'negative'."""
    loaded = _load_pipeline()
    strongly_negative = [
        "Terrible product! Broke after one day. Complete waste of money. "
        "The quality is awful and it does not work at all. "
        "Do not buy this, worst purchase ever. Very disappointed."
    ]
    preds = loaded.predict(strongly_negative)
    assert preds[0] == "negative", (
        f"Strongly negative review predicted as '{preds[0]}' instead of 'negative'"
    )


# =========================================================================
# 6. confusion_matrix.png validation
# =========================================================================

def test_confusion_matrix_is_valid_png():
    """confusion_matrix.png must be a valid PNG file (check magic bytes)."""
    with open(CONFUSION_MATRIX_PATH, "rb") as f:
        header = f.read(8)
    # PNG magic bytes: 137 80 78 71 13 10 26 10
    png_magic = b"\x89PNG\r\n\x1a\n"
    assert header == png_magic, (
        "confusion_matrix.png does not have valid PNG magic bytes"
    )


def test_confusion_matrix_reasonable_size():
    """confusion_matrix.png should be a reasonable size for a plot (>5KB)."""
    size = os.path.getsize(CONFUSION_MATRIX_PATH)
    assert size > 5000, (
        f"confusion_matrix.png is only {size} bytes, too small for a real plot"
    )
