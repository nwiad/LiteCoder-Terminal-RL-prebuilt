"""
Tests for Titanic Survivability Analysis & Prediction Engine.
Validates all 13 output files for existence, format, and content correctness.
"""

import os
import json
import csv
import subprocess

# All paths are relative to /app (the WORKDIR)
APP_DIR = "/app"
PLOTS_DIR = os.path.join(APP_DIR, "plots")


# ============================================================================
# Helper utilities
# ============================================================================

def is_valid_png(filepath):
    """Check if a file starts with the PNG magic bytes."""
    try:
        with open(filepath, "rb") as f:
            header = f.read(8)
        return header[:8] == b'\x89PNG\r\n\x1a\n'
    except Exception:
        return False


def file_exists_and_nonempty(filepath):
    """Check file exists and has non-trivial content."""
    return os.path.isfile(filepath) and os.path.getsize(filepath) > 0


# ============================================================================
# 1. Plot file existence and validity
# ============================================================================

EXPECTED_PLOTS = [
    "missing_values_heatmap.png",
    "correlation_heatmap.png",
    "survival_by_category.png",
    "age_distribution.png",
    "confusion_matrix.png",
    "feature_importance.png",
]


def test_plot_files_exist():
    """All 6 required plot PNGs must exist."""
    for name in EXPECTED_PLOTS:
        path = os.path.join(PLOTS_DIR, name)
        assert os.path.isfile(path), f"Missing plot file: {path}"


def test_plot_files_are_valid_png():
    """Each plot must be a valid PNG (magic bytes check)."""
    for name in EXPECTED_PLOTS:
        path = os.path.join(PLOTS_DIR, name)
        assert is_valid_png(path), f"Not a valid PNG: {path}"


def test_plot_files_nontrivial_size():
    """Each plot must be at least 1 KB (not an empty/stub image)."""
    min_size = 1024  # 1 KB
    for name in EXPECTED_PLOTS:
        path = os.path.join(PLOTS_DIR, name)
        size = os.path.getsize(path)
        assert size >= min_size, (
            f"Plot {name} is too small ({size} bytes), likely a stub"
        )


# ============================================================================
# 2. model_comparison.csv
# ============================================================================

def test_model_comparison_exists():
    """model_comparison.csv must exist and be non-empty."""
    path = os.path.join(APP_DIR, "model_comparison.csv")
    assert file_exists_and_nonempty(path), "model_comparison.csv missing or empty"


def test_model_comparison_columns():
    """CSV must have exactly the required columns."""
    path = os.path.join(APP_DIR, "model_comparison.csv")
    with open(path, "r") as f:
        reader = csv.DictReader(f)
        fieldnames = [fn.strip() for fn in reader.fieldnames]
    required = {"model_name", "mean_cv_score", "std_cv_score"}
    assert required.issubset(set(fieldnames)), (
        f"Missing columns. Expected {required}, got {set(fieldnames)}"
    )


def test_model_comparison_at_least_3_models():
    """At least 3 candidate models must be compared."""
    path = os.path.join(APP_DIR, "model_comparison.csv")
    with open(path, "r") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    assert len(rows) >= 3, f"Expected >= 3 models, got {len(rows)}"


def test_model_comparison_sorted_descending():
    """Rows must be sorted by mean_cv_score descending."""
    path = os.path.join(APP_DIR, "model_comparison.csv")
    with open(path, "r") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    scores = [float(r["mean_cv_score"]) for r in rows]
    for i in range(len(scores) - 1):
        assert scores[i] >= scores[i + 1], (
            f"model_comparison.csv not sorted descending: "
            f"{scores[i]} < {scores[i+1]} at row {i}"
        )


def test_model_comparison_score_ranges():
    """CV scores must be valid accuracy values in (0, 1]."""
    path = os.path.join(APP_DIR, "model_comparison.csv")
    with open(path, "r") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    for r in rows:
        mean_s = float(r["mean_cv_score"])
        std_s = float(r["std_cv_score"])
        assert 0.0 < mean_s <= 1.0, (
            f"mean_cv_score {mean_s} out of range for {r['model_name']}"
        )
        assert 0.0 <= std_s < 1.0, (
            f"std_cv_score {std_s} out of range for {r['model_name']}"
        )


def test_model_comparison_reasonable_accuracy():
    """Best model CV accuracy should be better than random (> 0.5)."""
    path = os.path.join(APP_DIR, "model_comparison.csv")
    with open(path, "r") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    best_score = max(float(r["mean_cv_score"]) for r in rows)
    assert best_score > 0.5, (
        f"Best CV accuracy {best_score} is not better than random"
    )


def test_model_comparison_decimal_precision():
    """Scores should be rounded to 4 decimal places."""
    path = os.path.join(APP_DIR, "model_comparison.csv")
    with open(path, "r") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    for r in rows:
        for col in ["mean_cv_score", "std_cv_score"]:
            val_str = r[col].strip()
            # After rounding to 4 decimals, should have at most 4 decimal digits
            if "." in val_str:
                decimals = len(val_str.split(".")[1])
                assert decimals <= 4, (
                    f"{col}={val_str} has {decimals} decimals, expected <= 4"
                )


# ============================================================================
# 3. evaluation_metrics.json
# ============================================================================

REQUIRED_METRIC_KEYS = {"best_model", "accuracy", "precision", "recall", "f1_score", "roc_auc"}
NUMERIC_METRIC_KEYS = {"accuracy", "precision", "recall", "f1_score", "roc_auc"}


def _load_metrics():
    path = os.path.join(APP_DIR, "evaluation_metrics.json")
    assert file_exists_and_nonempty(path), "evaluation_metrics.json missing or empty"
    with open(path, "r") as f:
        return json.load(f)


def test_evaluation_metrics_exists():
    """evaluation_metrics.json must exist and be valid JSON."""
    _load_metrics()


def test_evaluation_metrics_required_keys():
    """JSON must contain all required keys."""
    metrics = _load_metrics()
    missing = REQUIRED_METRIC_KEYS - set(metrics.keys())
    assert not missing, f"Missing keys in evaluation_metrics.json: {missing}"


def test_evaluation_metrics_best_model_is_string():
    """best_model must be a non-empty string."""
    metrics = _load_metrics()
    assert isinstance(metrics["best_model"], str), "best_model must be a string"
    assert len(metrics["best_model"].strip()) > 0, "best_model must not be empty"


def test_evaluation_metrics_values_in_range():
    """All numeric metrics must be floats/ints in [0, 1]."""
    metrics = _load_metrics()
    for key in NUMERIC_METRIC_KEYS:
        val = metrics[key]
        assert isinstance(val, (int, float)), f"{key} must be numeric, got {type(val)}"
        assert 0.0 <= val <= 1.0, f"{key}={val} out of [0, 1] range"


def test_evaluation_metrics_reasonable_performance():
    """Accuracy and ROC AUC should be better than random guessing (> 0.5)."""
    metrics = _load_metrics()
    assert metrics["accuracy"] > 0.5, (
        f"Test accuracy {metrics['accuracy']} is not better than random"
    )
    assert metrics["roc_auc"] > 0.5, (
        f"ROC AUC {metrics['roc_auc']} is not better than random"
    )


def test_evaluation_metrics_decimal_precision():
    """Numeric metrics should have at most 4 decimal places."""
    metrics = _load_metrics()
    for key in NUMERIC_METRIC_KEYS:
        val_str = str(metrics[key])
        if "." in val_str:
            decimals = len(val_str.rstrip("0").split(".")[1])
            assert decimals <= 4, (
                f"{key}={val_str} has more than 4 significant decimals"
            )


def test_evaluation_metrics_best_model_in_comparison():
    """The best_model in metrics should appear in model_comparison.csv."""
    metrics = _load_metrics()
    csv_path = os.path.join(APP_DIR, "model_comparison.csv")
    if not os.path.isfile(csv_path):
        return  # Skip if CSV doesn't exist (tested separately)
    with open(csv_path, "r") as f:
        reader = csv.DictReader(f)
        model_names = [r["model_name"].strip() for r in reader]
    assert metrics["best_model"].strip() in model_names, (
        f"best_model '{metrics['best_model']}' not found in model_comparison.csv models: {model_names}"
    )


# ============================================================================
# 4. titanic_pipeline.joblib
# ============================================================================

def test_pipeline_joblib_exists():
    """titanic_pipeline.joblib must exist and be non-empty."""
    path = os.path.join(APP_DIR, "titanic_pipeline.joblib")
    assert file_exists_and_nonempty(path), "titanic_pipeline.joblib missing or empty"


def test_pipeline_joblib_loadable():
    """The joblib file must be loadable and have predict/predict_proba methods."""
    import joblib
    path = os.path.join(APP_DIR, "titanic_pipeline.joblib")
    pipeline = joblib.load(path)
    assert hasattr(pipeline, "predict"), "Loaded pipeline has no predict method"
    assert hasattr(pipeline, "predict_proba"), "Loaded pipeline has no predict_proba method"


# ============================================================================
# 5. predict.py — CLI contract
# ============================================================================

def test_predict_py_exists():
    """predict.py must exist and be non-empty."""
    path = os.path.join(APP_DIR, "predict.py")
    assert file_exists_and_nonempty(path), "predict.py missing or empty"


def test_predict_py_valid_python():
    """predict.py must be valid Python (compiles without syntax errors)."""
    path = os.path.join(APP_DIR, "predict.py")
    with open(path, "r") as f:
        source = f.read()
    compile(source, path, "exec")


def test_predict_py_cli_contract():
    """predict.py must accept JSON stdin and return valid JSON stdout."""
    predict_path = os.path.join(APP_DIR, "predict.py")
    if not os.path.isfile(predict_path):
        assert False, "predict.py does not exist"

    test_input = json.dumps({
        "pclass": 1,
        "name": "Smith, Mr. John",
        "sex": "male",
        "age": 30,
        "sibsp": 0,
        "parch": 0,
        "fare": 50.0,
        "embarked": "S"
    })

    result = subprocess.run(
        ["python3", predict_path],
        input=test_input,
        capture_output=True,
        text=True,
        timeout=60,
        cwd=APP_DIR,
    )
    assert result.returncode == 0, (
        f"predict.py failed with code {result.returncode}. "
        f"stderr: {result.stderr[:500]}"
    )

    output = result.stdout.strip()
    assert len(output) > 0, "predict.py produced no output"

    data = json.loads(output)
    assert "survived" in data, "Output missing 'survived' key"
    assert "survival_probability" in data, "Output missing 'survival_probability' key"
    assert data["survived"] in (0, 1), f"survived must be 0 or 1, got {data['survived']}"
    prob = data["survival_probability"]
    assert isinstance(prob, (int, float)), f"survival_probability must be numeric, got {type(prob)}"
    assert 0.0 <= prob <= 1.0, f"survival_probability={prob} out of [0, 1]"


def test_predict_py_female_higher_survival():
    """A first-class female should have higher survival probability than a third-class male."""
    predict_path = os.path.join(APP_DIR, "predict.py")
    if not os.path.isfile(predict_path):
        assert False, "predict.py does not exist"

    female_input = json.dumps({
        "pclass": 1, "name": "Jones, Mrs. Mary", "sex": "female",
        "age": 25, "sibsp": 0, "parch": 0, "fare": 100.0, "embarked": "C"
    })
    male_input = json.dumps({
        "pclass": 3, "name": "Brown, Mr. Bob", "sex": "male",
        "age": 30, "sibsp": 0, "parch": 0, "fare": 8.0, "embarked": "S"
    })

    def run_predict(input_json):
        r = subprocess.run(
            ["python3", predict_path],
            input=input_json, capture_output=True, text=True,
            timeout=60, cwd=APP_DIR,
        )
        assert r.returncode == 0, f"predict.py failed: {r.stderr[:300]}"
        return json.loads(r.stdout.strip())

    female_result = run_predict(female_input)
    male_result = run_predict(male_input)

    assert female_result["survival_probability"] > male_result["survival_probability"], (
        f"First-class female prob ({female_result['survival_probability']}) "
        f"should exceed third-class male prob ({male_result['survival_probability']})"
    )


# ============================================================================
# 6. Documentation files
# ============================================================================

def test_requirements_txt_exists():
    """requirements.txt must exist with meaningful content."""
    path = os.path.join(APP_DIR, "requirements.txt")
    assert file_exists_and_nonempty(path), "requirements.txt missing or empty"
    with open(path, "r") as f:
        content = f.read().strip()
    lines = [l.strip() for l in content.splitlines() if l.strip()]
    assert len(lines) >= 2, (
        f"requirements.txt should list multiple packages, got {len(lines)} lines"
    )
    # Should contain at least scikit-learn and pandas
    content_lower = content.lower()
    assert "scikit-learn" in content_lower or "sklearn" in content_lower, (
        "requirements.txt should list scikit-learn"
    )
    assert "pandas" in content_lower, "requirements.txt should list pandas"


def test_readme_md_exists():
    """README.md must exist with meaningful content."""
    path = os.path.join(APP_DIR, "README.md")
    assert file_exists_and_nonempty(path), "README.md missing or empty"
    with open(path, "r") as f:
        content = f.read()
    # Should have at least 100 chars of real documentation
    assert len(content.strip()) >= 100, (
        "README.md is too short to be meaningful documentation"
    )
    # Should mention key topics
    content_lower = content.lower()
    assert "titanic" in content_lower, "README.md should mention Titanic"


def test_report_md_exists():
    """report.md must exist with meaningful non-technical content."""
    path = os.path.join(APP_DIR, "report.md")
    assert file_exists_and_nonempty(path), "report.md missing or empty"
    with open(path, "r") as f:
        content = f.read()
    assert len(content.strip()) >= 100, (
        "report.md is too short to be a meaningful report"
    )
    content_lower = content.lower()
    # Should discuss findings or results
    has_findings = any(
        kw in content_lower
        for kw in ["finding", "result", "survival", "model", "accuracy", "prediction"]
    )
    assert has_findings, "report.md should discuss findings, results, or model performance"


# ============================================================================
# 7. Cross-file consistency checks
# ============================================================================

def test_best_model_is_top_of_csv():
    """The best_model in evaluation_metrics.json should be the top row in model_comparison.csv."""
    metrics_path = os.path.join(APP_DIR, "evaluation_metrics.json")
    csv_path = os.path.join(APP_DIR, "model_comparison.csv")
    if not (os.path.isfile(metrics_path) and os.path.isfile(csv_path)):
        return  # Skip if files missing (tested separately)

    with open(metrics_path, "r") as f:
        metrics = json.load(f)
    with open(csv_path, "r") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if len(rows) == 0:
        return

    top_model = rows[0]["model_name"].strip()
    best_model = metrics["best_model"].strip()
    assert best_model == top_model, (
        f"best_model '{best_model}' should match top CSV row '{top_model}'"
    )


def test_all_output_files_present():
    """Comprehensive check: all 13 required output files must exist."""
    required_files = [
        "plots/missing_values_heatmap.png",
        "plots/correlation_heatmap.png",
        "plots/survival_by_category.png",
        "plots/age_distribution.png",
        "plots/confusion_matrix.png",
        "plots/feature_importance.png",
        "model_comparison.csv",
        "evaluation_metrics.json",
        "titanic_pipeline.joblib",
        "predict.py",
        "requirements.txt",
        "README.md",
        "report.md",
    ]
    missing = []
    for rel in required_files:
        full = os.path.join(APP_DIR, rel)
        if not os.path.isfile(full):
            missing.append(rel)
    assert not missing, f"Missing output files: {missing}"

