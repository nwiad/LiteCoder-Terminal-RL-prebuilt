"""
Tests for Fraud Detection Pipeline outputs.
Validates all artifacts produced by the pipeline against instruction.md requirements.
"""
import os
import json
import csv
import re
import pickle

# All paths are relative to /app/ as specified in instruction.md
APP_DIR = "/app"

# ============================================================================
# Helper utilities
# ============================================================================

def _read_csv_header_and_rows(path):
    """Read a CSV file and return (header_list, list_of_row_dicts)."""
    assert os.path.isfile(path), f"File not found: {path}"
    with open(path, "r", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    assert len(rows) > 0, f"CSV file is empty: {path}"
    return list(rows[0].keys()), rows


# ============================================================================
# 1. File existence tests
# ============================================================================

class TestFileExistence:
    """Every required artifact must exist and be non-empty."""

    REQUIRED_FILES = [
        "data/raw/transactions.csv",
        "data/raw/demographics.csv",
        "data/raw/network_features.csv",
        "data/processed/train_data.csv",
        "models/model.pkl",
        "results/metrics.json",
        "predict.py",
        "dashboard.html",
    ]

    def test_all_required_files_exist(self):
        for rel in self.REQUIRED_FILES:
            full = os.path.join(APP_DIR, rel)
            assert os.path.isfile(full), f"Missing required file: {full}"

    def test_all_required_files_non_empty(self):
        for rel in self.REQUIRED_FILES:
            full = os.path.join(APP_DIR, rel)
            if os.path.isfile(full):
                size = os.path.getsize(full)
                assert size > 0, f"File is empty (0 bytes): {full}"

    def test_run_sh_exists_and_executable(self):
        run_sh = os.path.join(APP_DIR, "run.sh")
        assert os.path.isfile(run_sh), "run.sh not found"
        # Check it's a valid shell script (starts with shebang or has bash content)
        with open(run_sh, "r") as f:
            content = f.read()
        assert len(content.strip()) > 0, "run.sh is empty"


# ============================================================================
# 2. Raw data — transactions.csv
# ============================================================================

class TestTransactionsCsv:
    PATH = os.path.join(APP_DIR, "data/raw/transactions.csv")

    def test_minimum_row_count(self):
        _, rows = _read_csv_header_and_rows(self.PATH)
        assert len(rows) >= 10000, f"transactions.csv has {len(rows)} rows, need >= 10000"

    def test_required_columns(self):
        header, _ = _read_csv_header_and_rows(self.PATH)
        required = {"txn_id", "user_id", "amount", "merchant_category", "timestamp", "is_fraud"}
        assert required.issubset(set(header)), f"Missing columns: {required - set(header)}"

    def test_txn_id_unique(self):
        _, rows = _read_csv_header_and_rows(self.PATH)
        txn_ids = [r["txn_id"] for r in rows]
        assert len(txn_ids) == len(set(txn_ids)), "txn_id values are not unique"

    def test_amount_non_negative(self):
        _, rows = _read_csv_header_and_rows(self.PATH)
        for r in rows[:500]:  # spot check
            assert float(r["amount"]) >= 0, f"Negative amount found: {r['amount']}"

    def test_is_fraud_binary(self):
        _, rows = _read_csv_header_and_rows(self.PATH)
        fraud_vals = set(r["is_fraud"].strip() for r in rows)
        assert fraud_vals.issubset({"0", "1"}), f"is_fraud has non-binary values: {fraud_vals}"

    def test_fraud_rate_between_1_and_5_percent(self):
        _, rows = _read_csv_header_and_rows(self.PATH)
        fraud_count = sum(1 for r in rows if r["is_fraud"].strip() == "1")
        rate = fraud_count / len(rows)
        assert 0.01 <= rate <= 0.05, f"Fraud rate {rate:.4f} not in [0.01, 0.05]"

    def test_merchant_category_at_least_5_distinct(self):
        _, rows = _read_csv_header_and_rows(self.PATH)
        categories = set(r["merchant_category"].strip() for r in rows)
        assert len(categories) >= 5, f"Only {len(categories)} merchant categories, need >= 5"

    def test_timestamp_iso8601_format(self):
        """Spot-check that timestamps look like ISO-8601."""
        _, rows = _read_csv_header_and_rows(self.PATH)
        for r in rows[:20]:
            ts = r["timestamp"].strip()
            # Should match YYYY-MM-DDTHH:MM:SS or similar ISO pattern
            assert re.match(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}", ts), \
                f"Timestamp not ISO-8601: {ts}"


# ============================================================================
# 3. Raw data — demographics.csv
# ============================================================================

class TestDemographicsCsv:
    PATH = os.path.join(APP_DIR, "data/raw/demographics.csv")

    def test_required_columns(self):
        header, _ = _read_csv_header_and_rows(self.PATH)
        required = {"user_id", "age", "gender", "account_age_days", "credit_score"}
        assert required.issubset(set(header)), f"Missing columns: {required - set(header)}"

    def test_one_row_per_user(self):
        _, rows = _read_csv_header_and_rows(self.PATH)
        user_ids = [r["user_id"] for r in rows]
        assert len(user_ids) == len(set(user_ids)), "demographics.csv has duplicate user_ids"

    def test_user_ids_match_transactions(self):
        _, txn_rows = _read_csv_header_and_rows(
            os.path.join(APP_DIR, "data/raw/transactions.csv"))
        _, demo_rows = _read_csv_header_and_rows(self.PATH)
        txn_users = set(r["user_id"] for r in txn_rows)
        demo_users = set(r["user_id"] for r in demo_rows)
        assert txn_users.issubset(demo_users), \
            f"{len(txn_users - demo_users)} transaction user_ids missing from demographics"

    def test_age_range(self):
        _, rows = _read_csv_header_and_rows(self.PATH)
        for r in rows[:200]:
            age = int(r["age"])
            assert 18 <= age <= 80, f"Age {age} out of range [18, 80]"

    def test_credit_score_range(self):
        _, rows = _read_csv_header_and_rows(self.PATH)
        for r in rows[:200]:
            cs = int(r["credit_score"])
            assert 300 <= cs <= 850, f"Credit score {cs} out of range [300, 850]"

    def test_account_age_days_non_negative(self):
        _, rows = _read_csv_header_and_rows(self.PATH)
        for r in rows[:200]:
            val = int(r["account_age_days"])
            assert val >= 0, f"Negative account_age_days: {val}"


# ============================================================================
# 4. Raw data — network_features.csv
# ============================================================================

class TestNetworkFeaturesCsv:
    PATH = os.path.join(APP_DIR, "data/raw/network_features.csv")

    def test_required_columns(self):
        header, _ = _read_csv_header_and_rows(self.PATH)
        required = {"txn_id", "num_txns_last_1h", "num_txns_last_24h",
                     "avg_amount_last_24h", "is_foreign"}
        assert required.issubset(set(header)), f"Missing columns: {required - set(header)}"

    def test_txn_ids_match_transactions(self):
        _, txn_rows = _read_csv_header_and_rows(
            os.path.join(APP_DIR, "data/raw/transactions.csv"))
        _, net_rows = _read_csv_header_and_rows(self.PATH)
        txn_ids = set(r["txn_id"] for r in txn_rows)
        net_ids = set(r["txn_id"] for r in net_rows)
        assert txn_ids == net_ids, \
            f"txn_id mismatch: {len(txn_ids - net_ids)} in txn not in net, " \
            f"{len(net_ids - txn_ids)} in net not in txn"

    def test_non_negative_counts(self):
        _, rows = _read_csv_header_and_rows(self.PATH)
        for r in rows[:300]:
            assert int(r["num_txns_last_1h"]) >= 0
            assert int(r["num_txns_last_24h"]) >= 0
            assert float(r["avg_amount_last_24h"]) >= 0

    def test_is_foreign_binary(self):
        _, rows = _read_csv_header_and_rows(self.PATH)
        vals = set(r["is_foreign"].strip() for r in rows)
        assert vals.issubset({"0", "1"}), f"is_foreign has non-binary values: {vals}"


# ============================================================================
# 5. Processed data — train_data.csv
# ============================================================================

class TestTrainDataCsv:
    PATH = os.path.join(APP_DIR, "data/processed/train_data.csv")

    def test_has_is_fraud_column(self):
        header, _ = _read_csv_header_and_rows(self.PATH)
        assert "is_fraud" in header, "train_data.csv missing 'is_fraud' column"

    def test_all_columns_numeric(self):
        """All columns in the processed data must be numeric."""
        _, rows = _read_csv_header_and_rows(self.PATH)
        header = list(rows[0].keys())
        for r in rows[:100]:
            for col in header:
                val = r[col].strip()
                try:
                    float(val)
                except ValueError:
                    assert False, f"Non-numeric value '{val}' in column '{col}'"

    def test_no_nan_values(self):
        """Processed data should have no NaN/missing values."""
        _, rows = _read_csv_header_and_rows(self.PATH)
        header = list(rows[0].keys())
        for r in rows[:200]:
            for col in header:
                val = r[col].strip().lower()
                assert val not in ("", "nan", "none", "null", "na", "n/a"), \
                    f"Missing/NaN value in column '{col}': '{r[col]}'"

    def test_reasonable_row_count(self):
        """Should have a substantial number of rows (from 10k+ transactions)."""
        _, rows = _read_csv_header_and_rows(self.PATH)
        assert len(rows) >= 5000, \
            f"train_data.csv has only {len(rows)} rows, expected >= 5000"

    def test_is_fraud_binary_in_processed(self):
        _, rows = _read_csv_header_and_rows(self.PATH)
        fraud_vals = set(r["is_fraud"].strip() for r in rows)
        # Allow both int-like "0"/"1" and float-like "0.0"/"1.0"
        for v in fraud_vals:
            fv = float(v)
            assert fv in (0.0, 1.0), f"is_fraud has unexpected value: {v}"


# ============================================================================
# 6. Model — model.pkl
# ============================================================================

class TestModelPkl:
    PATH = os.path.join(APP_DIR, "models/model.pkl")

    def test_model_loadable(self):
        """Model file must be loadable with pickle or joblib."""
        assert os.path.isfile(self.PATH), "model.pkl not found"
        # Try joblib first, fall back to pickle
        model = None
        try:
            import joblib
            model = joblib.load(self.PATH)
        except Exception:
            with open(self.PATH, "rb") as f:
                model = pickle.load(f)
        assert model is not None, "Could not load model.pkl"

    def test_model_has_predict_methods(self):
        """Model must have predict and predict_proba methods."""
        model = None
        try:
            import joblib
            model = joblib.load(self.PATH)
        except Exception:
            with open(self.PATH, "rb") as f:
                model = pickle.load(f)
        assert hasattr(model, "predict"), "Model missing 'predict' method"
        assert hasattr(model, "predict_proba"), "Model missing 'predict_proba' method"

    def test_model_file_not_trivially_small(self):
        """A real trained model should be more than a few KB."""
        size = os.path.getsize(self.PATH)
        assert size > 10000, f"model.pkl is only {size} bytes — suspiciously small"


# ============================================================================
# 7. Metrics — metrics.json
# ============================================================================

class TestMetricsJson:
    PATH = os.path.join(APP_DIR, "results/metrics.json")

    def _load(self):
        with open(self.PATH, "r") as f:
            return json.load(f)

    def test_valid_json(self):
        assert os.path.isfile(self.PATH), "metrics.json not found"
        data = self._load()
        assert isinstance(data, dict), "metrics.json root must be a JSON object"

    def test_has_cv_scores_key(self):
        data = self._load()
        assert "cv_scores" in data, "Missing top-level key 'cv_scores'"

    def test_has_holdout_scores_key(self):
        data = self._load()
        assert "holdout_scores" in data, "Missing top-level key 'holdout_scores'"

    def test_cv_scores_structure(self):
        data = self._load()
        cv = data["cv_scores"]
        for key in ("roc_auc", "pr_auc", "f1"):
            assert key in cv, f"cv_scores missing '{key}'"
            val = cv[key]
            assert isinstance(val, (int, float)), f"cv_scores.{key} is not numeric: {val}"
            assert 0.0 <= float(val) <= 1.0, \
                f"cv_scores.{key} = {val} not in [0.0, 1.0]"

    def test_holdout_scores_structure(self):
        data = self._load()
        hs = data["holdout_scores"]
        for key in ("roc_auc", "pr_auc", "f1"):
            assert key in hs, f"holdout_scores missing '{key}'"
            val = hs[key]
            assert isinstance(val, (int, float)), f"holdout_scores.{key} is not numeric: {val}"
            assert 0.0 <= float(val) <= 1.0, \
                f"holdout_scores.{key} = {val} not in [0.0, 1.0]"

    def test_metrics_not_all_zero(self):
        """A trained model should have non-trivial metrics."""
        data = self._load()
        all_vals = []
        for section in ("cv_scores", "holdout_scores"):
            for key in ("roc_auc", "pr_auc", "f1"):
                all_vals.append(float(data[section][key]))
        assert any(v > 0.1 for v in all_vals), \
            f"All metrics are near zero — model likely not trained: {all_vals}"

    def test_roc_auc_reasonable(self):
        """ROC-AUC should be above random (0.5) for a properly trained model."""
        data = self._load()
        for section in ("cv_scores", "holdout_scores"):
            roc = float(data[section]["roc_auc"])
            assert roc > 0.5, \
                f"{section}.roc_auc = {roc}, worse than random — model not trained properly"


# ============================================================================
# 8. Prediction CLI — output.json
# ============================================================================

class TestOutputJson:
    PATH = os.path.join(APP_DIR, "output.json")

    def _load(self):
        with open(self.PATH, "r") as f:
            return json.load(f)

    def test_output_json_exists(self):
        assert os.path.isfile(self.PATH), \
            "output.json not found — predict.py may not have been run"

    def test_valid_json_structure(self):
        data = self._load()
        assert isinstance(data, dict), "output.json root must be a JSON object"

    def test_has_fraud_probability(self):
        data = self._load()
        assert "fraud_probability" in data, "output.json missing 'fraud_probability'"
        prob = data["fraud_probability"]
        assert isinstance(prob, (int, float)), \
            f"fraud_probability is not numeric: {type(prob)}"
        assert 0.0 <= float(prob) <= 1.0, \
            f"fraud_probability = {prob} not in [0.0, 1.0]"

    def test_has_prediction(self):
        data = self._load()
        assert "prediction" in data, "output.json missing 'prediction'"
        pred = data["prediction"]
        assert pred in (0, 1, 0.0, 1.0), \
            f"prediction must be 0 or 1, got: {pred}"

    def test_prediction_consistent_with_probability(self):
        """If probability > 0.5, prediction should be 1; if < 0.5, should be 0."""
        data = self._load()
        prob = float(data["fraud_probability"])
        pred = int(data["prediction"])
        # Only check clear-cut cases (not near 0.5 threshold)
        if prob > 0.7:
            assert pred == 1, \
                f"probability={prob} but prediction={pred}, expected 1"
        elif prob < 0.3:
            assert pred == 0, \
                f"probability={prob} but prediction={pred}, expected 0"


# ============================================================================
# 9. Dashboard — dashboard.html
# ============================================================================

class TestDashboardHtml:
    PATH = os.path.join(APP_DIR, "dashboard.html")

    def _read(self):
        with open(self.PATH, "r", encoding="utf-8", errors="replace") as f:
            return f.read()

    def test_is_valid_html_document(self):
        content = self._read()
        lower = content.lower()
        assert "<html" in lower, "dashboard.html missing <html> tag"
        assert "</html>" in lower, "dashboard.html missing </html> closing tag"

    def test_has_doctype_or_html5(self):
        content = self._read()
        lower = content.lower().strip()
        assert lower.startswith("<!doctype html>") or "<html" in lower, \
            "dashboard.html is not a valid HTML document"

    def test_contains_class_distribution_section(self):
        """Must show fraud vs non-fraud counts."""
        content = self._read()
        lower = content.lower()
        # Should mention fraud/non-fraud or legitimate and have numbers
        has_fraud_mention = "fraud" in lower
        has_numbers = bool(re.search(r"\d{2,}", content))
        assert has_fraud_mention and has_numbers, \
            "Dashboard missing class distribution section (fraud counts)"

    def test_contains_metrics_section(self):
        """Must show ROC-AUC, PR-AUC, F1 metrics."""
        content = self._read()
        lower = content.lower()
        # Check for at least two of the three metric names
        metric_hits = sum(1 for m in ["roc", "auc", "f1", "pr"] if m in lower)
        assert metric_hits >= 2, \
            "Dashboard missing model performance metrics section"

    def test_contains_base64_embedded_chart(self):
        """Must have at least one base64-encoded PNG image."""
        content = self._read()
        # Look for base64 image pattern in src attribute
        b64_pattern = re.compile(
            r'(?:src\s*=\s*["\']data:image/png;base64,[A-Za-z0-9+/=]{100,})',
            re.IGNORECASE
        )
        matches = b64_pattern.findall(content)
        assert len(matches) >= 1, \
            "Dashboard must contain at least one base64-encoded PNG chart image"

    def test_html_not_trivially_small(self):
        """A real dashboard with embedded charts should be substantial."""
        size = os.path.getsize(self.PATH)
        # Base64 images alone should make this at least 10KB
        assert size > 5000, \
            f"dashboard.html is only {size} bytes — too small for embedded charts"


# ============================================================================
# 10. Predict.py script existence and basic structure
# ============================================================================

class TestPredictScript:
    PATH = os.path.join(APP_DIR, "predict.py")

    def test_predict_py_exists(self):
        assert os.path.isfile(self.PATH), "predict.py not found"

    def test_predict_py_is_python(self):
        with open(self.PATH, "r") as f:
            content = f.read()
        assert len(content) > 50, "predict.py is too short to be a real script"
        # Should contain import statements and basic Python constructs
        assert "import" in content, "predict.py doesn't contain any imports"

    def test_predict_py_reads_command_line_arg(self):
        """predict.py should accept a JSON file path as CLI argument."""
        with open(self.PATH, "r") as f:
            content = f.read()
        # Should reference sys.argv or argparse
        uses_cli = ("sys.argv" in content or "argparse" in content
                     or "ArgumentParser" in content)
        assert uses_cli, \
            "predict.py doesn't appear to accept command-line arguments"
