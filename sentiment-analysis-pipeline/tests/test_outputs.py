"""
Tests for Sentiment Analysis Pipeline task.

Validates all required output files, formats, model quality,
and CLI prediction script behavior.
"""
import os
import re
import subprocess
import sys

# ---------------------------------------------------------------------------
# Paths – all relative to /app (the WORKDIR defined in the Dockerfile)
# ---------------------------------------------------------------------------
APP_DIR = "/app"
RESULTS_FILE = os.path.join(APP_DIR, "results.txt")
ACCURACY_FILE = os.path.join(APP_DIR, "test_accuracy.txt")
MODEL_FILE = os.path.join(APP_DIR, "sentiment_model.joblib")
PREDICT_SCRIPT = os.path.join(APP_DIR, "predict.py")
REQUIREMENTS_FILE = os.path.join(APP_DIR, "requirements.txt")
DATA_FILE = os.path.join(APP_DIR, "data", "reviews.csv")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read_text(path):
    """Read a text file, return stripped content. Raises AssertionError if missing/empty."""
    assert os.path.isfile(path), f"File not found: {path}"
    with open(path, "r") as f:
        content = f.read()
    assert len(content.strip()) > 0, f"File is empty: {path}"
    return content.strip()


def _run_predict(review_text, timeout=60):
    """Run predict.py with a review string and return stripped stdout."""
    result = subprocess.run(
        [sys.executable, PREDICT_SCRIPT, review_text],
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=APP_DIR,
    )
    assert result.returncode == 0, (
        f"predict.py failed with return code {result.returncode}.\n"
        f"stderr: {result.stderr}"
    )
    return result.stdout.strip()


# ===================================================================
# 1. FILE EXISTENCE TESTS
# ===================================================================

def test_results_file_exists():
    assert os.path.isfile(RESULTS_FILE), "results.txt not found"


def test_accuracy_file_exists():
    assert os.path.isfile(ACCURACY_FILE), "test_accuracy.txt not found"


def test_model_file_exists():
    assert os.path.isfile(MODEL_FILE), "sentiment_model.joblib not found"


def test_predict_script_exists():
    assert os.path.isfile(PREDICT_SCRIPT), "predict.py not found"


def test_requirements_file_exists():
    assert os.path.isfile(REQUIREMENTS_FILE), "requirements.txt not found"


# ===================================================================
# 2. results.txt – FORMAT AND CONTENT
# ===================================================================

# Pattern: <Name>: mean=<float>, std=<float>
_RESULT_LINE_RE = re.compile(
    r"^(.+?):\s*mean\s*=\s*(\d+\.\d{4})\s*,\s*std\s*=\s*(\d+\.\d{4})\s*$"
)


def test_results_has_at_least_three_classifiers():
    content = _read_text(RESULTS_FILE)
    lines = [l.strip() for l in content.splitlines() if l.strip()]
    matched = [l for l in lines if _RESULT_LINE_RE.match(l)]
    assert len(matched) >= 3, (
        f"Expected at least 3 classifier result lines, found {len(matched)}.\n"
        f"Lines: {lines}"
    )


def test_results_format_valid():
    """Every non-blank line must match the required format."""
    content = _read_text(RESULTS_FILE)
    lines = [l.strip() for l in content.splitlines() if l.strip()]
    for line in lines:
        m = _RESULT_LINE_RE.match(line)
        assert m is not None, f"Line does not match format: '{line}'"


def test_results_values_in_range():
    """Mean and std values should be valid probabilities / scores."""
    content = _read_text(RESULTS_FILE)
    lines = [l.strip() for l in content.splitlines() if l.strip()]
    for line in lines:
        m = _RESULT_LINE_RE.match(line)
        if m:
            mean_val = float(m.group(2))
            std_val = float(m.group(3))
            assert 0.0 <= mean_val <= 1.0, (
                f"Mean {mean_val} out of [0,1] range in: '{line}'"
            )
            assert 0.0 <= std_val <= 1.0, (
                f"Std {std_val} out of [0,1] range in: '{line}'"
            )


def test_results_mean_above_random():
    """At least one classifier should beat random chance (>0.50)."""
    content = _read_text(RESULTS_FILE)
    lines = [l.strip() for l in content.splitlines() if l.strip()]
    means = []
    for line in lines:
        m = _RESULT_LINE_RE.match(line)
        if m:
            means.append(float(m.group(2)))
    assert any(v > 0.50 for v in means), (
        f"No classifier beat random chance. Means: {means}"
    )


# ===================================================================
# 3. test_accuracy.txt – FORMAT AND THRESHOLD
# ===================================================================

_ACCURACY_RE = re.compile(
    r"^Test\s+accuracy\s*:\s*(\d+\.\d{4})\s*$"
)


def test_accuracy_format():
    content = _read_text(ACCURACY_FILE)
    # Take the first non-blank line
    line = content.splitlines()[0].strip()
    m = _ACCURACY_RE.match(line)
    assert m is not None, (
        f"test_accuracy.txt first line does not match 'Test accuracy: X.XXXX'. Got: '{line}'"
    )


def test_accuracy_above_threshold():
    content = _read_text(ACCURACY_FILE)
    line = content.splitlines()[0].strip()
    m = _ACCURACY_RE.match(line)
    assert m is not None, f"Cannot parse accuracy from: '{line}'"
    acc = float(m.group(1))
    assert acc > 0.55, f"Test accuracy {acc} is not above 0.55"


def test_accuracy_is_plausible():
    """Accuracy should be a valid probability."""
    content = _read_text(ACCURACY_FILE)
    line = content.splitlines()[0].strip()
    m = _ACCURACY_RE.match(line)
    assert m is not None
    acc = float(m.group(1))
    assert 0.0 <= acc <= 1.0, f"Accuracy {acc} is outside [0, 1]"


# ===================================================================
# 4. sentiment_model.joblib – LOADABLE SKLEARN PIPELINE
# ===================================================================

def test_model_loadable():
    """Model file must be loadable via joblib."""
    import joblib
    model = joblib.load(MODEL_FILE)
    assert model is not None, "joblib.load returned None"


def test_model_is_pipeline():
    """Loaded model should be a scikit-learn Pipeline."""
    import joblib
    from sklearn.pipeline import Pipeline
    model = joblib.load(MODEL_FILE)
    assert isinstance(model, Pipeline), (
        f"Expected sklearn Pipeline, got {type(model).__name__}"
    )


def test_model_has_tfidf_step():
    """Pipeline must contain a TfidfVectorizer step."""
    import joblib
    from sklearn.feature_extraction.text import TfidfVectorizer
    model = joblib.load(MODEL_FILE)
    found = False
    for name, step in model.named_steps.items():
        if isinstance(step, TfidfVectorizer):
            found = True
            break
    assert found, "Pipeline does not contain a TfidfVectorizer step"


def test_model_tfidf_max_features():
    """TfidfVectorizer should have max_features=10000."""
    import joblib
    from sklearn.feature_extraction.text import TfidfVectorizer
    model = joblib.load(MODEL_FILE)
    for name, step in model.named_steps.items():
        if isinstance(step, TfidfVectorizer):
            assert step.max_features == 10000, (
                f"TfidfVectorizer max_features={step.max_features}, expected 10000"
            )
            break


def test_model_tfidf_stop_words():
    """TfidfVectorizer should use English stop words."""
    import joblib
    from sklearn.feature_extraction.text import TfidfVectorizer
    model = joblib.load(MODEL_FILE)
    for name, step in model.named_steps.items():
        if isinstance(step, TfidfVectorizer):
            assert step.stop_words == "english", (
                f"TfidfVectorizer stop_words='{step.stop_words}', expected 'english'"
            )
            break


def test_model_can_predict():
    """Model should be able to predict on raw text input."""
    import joblib
    model = joblib.load(MODEL_FILE)
    preds = model.predict(["This is a test review"])
    assert len(preds) == 1
    assert preds[0] in ("positive", "negative"), (
        f"Prediction '{preds[0]}' is not 'positive' or 'negative'"
    )


# ===================================================================
# 5. predict.py – CLI BEHAVIOR
# ===================================================================

def test_predict_positive_review():
    """A clearly positive review should return 'positive'."""
    output = _run_predict("This movie was absolutely wonderful and I loved every minute of it")
    assert output == "positive", (
        f"Expected 'positive' for a clearly positive review, got '{output}'"
    )


def test_predict_negative_review():
    """A clearly negative review should return 'negative'."""
    output = _run_predict("This movie was a complete waste of time and I regret watching it")
    assert output == "negative", (
        f"Expected 'negative' for a clearly negative review, got '{output}'"
    )


def test_predict_output_is_single_word():
    """predict.py must output exactly one line: 'positive' or 'negative'."""
    output = _run_predict("A decent film overall")
    lines = [l for l in output.splitlines() if l.strip()]
    assert len(lines) == 1, (
        f"Expected exactly 1 output line, got {len(lines)}: {lines}"
    )
    assert lines[0] in ("positive", "negative"), (
        f"Output '{lines[0]}' is not 'positive' or 'negative'"
    )


def test_predict_no_extra_whitespace():
    """Output should have no leading/trailing whitespace beyond newline."""
    result = subprocess.run(
        [sys.executable, PREDICT_SCRIPT, "Great movie"],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=APP_DIR,
    )
    raw = result.stdout.rstrip("\n")
    # Should be exactly "positive" or "negative" with no extra spaces
    assert raw in ("positive", "negative"), (
        f"Raw output has extra whitespace or wrong content: repr={repr(raw)}"
    )


def test_predict_another_positive():
    """Second positive review to prevent hardcoded single-answer."""
    output = _run_predict("An incredible movie with stunning visuals and a heartwarming story")
    assert output == "positive", (
        f"Expected 'positive', got '{output}'"
    )


def test_predict_another_negative():
    """Second negative review to prevent hardcoded single-answer."""
    output = _run_predict("A terrible film with awful acting and a nonsensical plot throughout")
    assert output == "negative", (
        f"Expected 'negative', got '{output}'"
    )


# ===================================================================
# 6. requirements.txt – ESSENTIAL DEPENDENCIES
# ===================================================================

def test_requirements_contains_sklearn():
    content = _read_text(REQUIREMENTS_FILE).lower()
    assert "scikit-learn" in content or "sklearn" in content, (
        "requirements.txt does not mention scikit-learn"
    )


def test_requirements_contains_pandas():
    content = _read_text(REQUIREMENTS_FILE).lower()
    assert "pandas" in content, "requirements.txt does not mention pandas"


def test_requirements_contains_joblib():
    content = _read_text(REQUIREMENTS_FILE).lower()
    assert "joblib" in content, "requirements.txt does not mention joblib"


# ===================================================================
# 7. MODEL QUALITY – CROSS-CHECK WITH DATA
# ===================================================================

def test_model_accuracy_on_test_split():
    """
    Load the model and the test data independently, compute accuracy,
    and verify it matches the reported accuracy (within tolerance)
    and exceeds the 0.55 threshold.
    """
    import joblib
    import pandas as pd
    import numpy as np

    model = joblib.load(MODEL_FILE)
    df = pd.read_csv(DATA_FILE)
    test_df = df[df["split"] == "test"]
    assert len(test_df) > 0, "No test rows found in reviews.csv"

    X_test = test_df["review"].values
    y_test = test_df["sentiment"].values
    preds = model.predict(X_test)
    computed_acc = (preds == y_test).mean()

    # Must beat random
    assert computed_acc > 0.55, (
        f"Computed test accuracy {computed_acc:.4f} is not above 0.55"
    )

    # Cross-check with reported accuracy
    content = _read_text(ACCURACY_FILE)
    m = _ACCURACY_RE.match(content.splitlines()[0].strip())
    if m:
        reported_acc = float(m.group(1))
        assert np.isclose(computed_acc, reported_acc, atol=0.02), (
            f"Computed accuracy {computed_acc:.4f} differs from reported "
            f"{reported_acc:.4f} by more than 0.02"
        )
