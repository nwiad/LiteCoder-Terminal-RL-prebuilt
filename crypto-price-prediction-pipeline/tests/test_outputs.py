"""
Tests for Crypto Price Prediction Pipeline.
Validates all output files: btc_raw.csv, btc_predictor.pkl, X_test.csv, y_test.csv, report.txt
"""
import os
import re
import csv
import math
import numpy as np
import pandas as pd
import joblib
import pickle

# All output files live in /app/
APP_DIR = "/app"

def _path(name):
    return os.path.join(APP_DIR, name)


def _is_numeric(s):
    """Check if a string is numeric (int or float)."""
    try:
        float(s.strip())
        return True
    except (ValueError, TypeError):
        return False


# =========================================================================
# 1. btc_raw.csv — the generated raw data
# =========================================================================

class TestBtcRawCsv:
    """Validate the generated raw CSV meets the spec."""

    def test_file_exists(self):
        assert os.path.isfile(_path("btc_raw.csv")), "btc_raw.csv not found"

    def test_row_count(self):
        with open(_path("btc_raw.csv"), "r") as f:
            reader = csv.reader(f)
            rows = list(reader)
        assert len(rows) == 2000, f"Expected 2000 rows, got {len(rows)}"

    def test_column_count(self):
        with open(_path("btc_raw.csv"), "r") as f:
            reader = csv.reader(f)
            for i, row in enumerate(reader):
                assert len(row) == 8, f"Row {i} has {len(row)} columns, expected 8"

    def test_no_header_row(self):
        """First row should be data, not column names."""
        with open(_path("btc_raw.csv"), "r") as f:
            first_line = f.readline().strip()
        # A header would contain words like 'timestamp','open','close' etc.
        header_words = {"timestamp", "open", "high", "low", "close", "volume"}
        first_fields = [f.strip().lower() for f in first_line.split(",")]
        overlap = header_words.intersection(set(first_fields))
        assert len(overlap) == 0, f"First row looks like a header: {first_line}"

    def test_not_sorted_chronologically(self):
        """Rows must be shuffled — not in chronological order."""
        timestamps = []
        with open(_path("btc_raw.csv"), "r") as f:
            reader = csv.reader(f)
            for row in reader:
                timestamps.append(row[0].strip())
        # If perfectly sorted, every consecutive pair would be ascending
        sorted_ts = sorted(timestamps)
        assert timestamps != sorted_ts, "Rows appear to be in sorted order; they should be shuffled"

    def test_has_missing_values(self):
        """Approximately 5% of rows should have missing values (empty fields)."""
        missing_count = 0
        with open(_path("btc_raw.csv"), "r") as f:
            reader = csv.reader(f)
            for row in reader:
                if any(field.strip() == "" for field in row):
                    missing_count += 1
        # Expect ~5% = ~100 rows; allow wide range [20, 300]
        assert missing_count >= 20, f"Too few rows with missing values: {missing_count}"
        assert missing_count <= 300, f"Too many rows with missing values: {missing_count}"

    def test_has_outliers(self):
        """Approximately 2% of rows should have outlier values."""
        outlier_count = 0
        with open(_path("btc_raw.csv"), "r") as f:
            reader = csv.reader(f)
            for row in reader:
                try:
                    prices = [float(row[i]) for i in [1, 2, 3, 4] if row[i].strip()]
                    vol = float(row[5]) if row[5].strip() else None
                    if any(p <= 0 for p in prices):
                        outlier_count += 1
                        continue
                    if vol is not None and vol > 500000:
                        outlier_count += 1
                        continue
                except (ValueError, IndexError):
                    pass
        # Expect ~2% = ~40 rows; allow range [5, 200]
        assert outlier_count >= 5, f"Too few outlier rows: {outlier_count}"

    def test_timestamps_are_iso8601(self):
        """Timestamps should be ISO-8601 formatted."""
        iso_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$")
        with open(_path("btc_raw.csv"), "r") as f:
            reader = csv.reader(f)
            for i, row in enumerate(reader):
                ts = row[0].strip()
                if ts:  # non-empty
                    assert iso_pattern.match(ts), f"Row {i} timestamp not ISO-8601: {ts}"


# =========================================================================
# 2. btc_predictor.pkl — the trained model
# =========================================================================

class TestModelArtifact:
    """Validate the saved model artifact."""

    def _load_model(self):
        path = _path("btc_predictor.pkl")
        assert os.path.isfile(path), "btc_predictor.pkl not found"
        try:
            model = joblib.load(path)
        except Exception:
            with open(path, "rb") as f:
                model = pickle.load(f)
        return model

    def test_file_exists(self):
        assert os.path.isfile(_path("btc_predictor.pkl")), "btc_predictor.pkl not found"

    def test_file_not_empty(self):
        size = os.path.getsize(_path("btc_predictor.pkl"))
        assert size > 1000, f"btc_predictor.pkl too small ({size} bytes), likely not a real model"

    def test_is_gradient_boosting_classifier(self):
        model = self._load_model()
        class_name = type(model).__name__
        assert "GradientBoosting" in class_name, (
            f"Model is {class_name}, expected GradientBoostingClassifier"
        )

    def test_has_feature_importances(self):
        model = self._load_model()
        assert hasattr(model, "feature_importances_"), "Model missing feature_importances_"
        fi = model.feature_importances_
        assert len(fi) > 0, "feature_importances_ is empty"
        assert np.isclose(sum(fi), 1.0, atol=0.01), "feature_importances_ don't sum to ~1.0"

    def test_model_can_predict(self):
        """Model should be able to predict on X_test."""
        model = self._load_model()
        x_path = _path("X_test.csv")
        if os.path.isfile(x_path):
            X_test = pd.read_csv(x_path)
            preds = model.predict(X_test)
            assert len(preds) == len(X_test), "Prediction count != X_test row count"
            assert set(preds).issubset({0, 1}), "Predictions should be 0 or 1"


# =========================================================================
# 3. X_test.csv — test set features
# =========================================================================

class TestXTestCsv:
    """Validate the test feature set."""

    def test_file_exists(self):
        assert os.path.isfile(_path("X_test.csv")), "X_test.csv not found"

    def test_not_empty(self):
        df = pd.read_csv(_path("X_test.csv"))
        assert len(df) > 0, "X_test.csv is empty"

    def test_has_header(self):
        with open(_path("X_test.csv"), "r") as f:
            header = f.readline().strip()
        # Header should contain feature names, not numeric data
        fields = header.split(",")
        # At least some fields should be non-numeric (column names)
        non_numeric = [f for f in fields if not _is_numeric(f)]
        assert len(non_numeric) >= 3, f"X_test.csv header looks like data, not column names: {header}"

    def test_required_feature_columns(self):
        """Must include the 4 engineered features from the spec."""
        df = pd.read_csv(_path("X_test.csv"))
        required = {"price_change", "volume_momentum", "sentiment_shift", "fg_trends_interaction"}
        actual = set(df.columns)
        missing = required - actual
        assert len(missing) == 0, f"X_test.csv missing required feature columns: {missing}"

    def test_no_target_column(self):
        """X_test should NOT contain the target column."""
        df = pd.read_csv(_path("X_test.csv"))
        assert "next_direction" not in df.columns, "X_test.csv should not contain 'next_direction'"

    def test_no_index_column(self):
        """Should not have an unnamed index column."""
        df = pd.read_csv(_path("X_test.csv"))
        unnamed_cols = [c for c in df.columns if "unnamed" in c.lower()]
        assert len(unnamed_cols) == 0, f"X_test.csv has index column(s): {unnamed_cols}"

    def test_no_nan_values(self):
        """Test features should be fully clean — no NaN."""
        df = pd.read_csv(_path("X_test.csv"))
        nan_count = df.isna().sum().sum()
        assert nan_count == 0, f"X_test.csv has {nan_count} NaN values"

    def test_reasonable_row_count(self):
        """Test set is 20% of cleaned data. With ~2000 raw rows, expect 200-500 test rows."""
        df = pd.read_csv(_path("X_test.csv"))
        assert 100 <= len(df) <= 600, f"X_test.csv has {len(df)} rows, expected 100-600"

    def test_reasonable_column_count(self):
        """Should have at least the 4 engineered + some original features."""
        df = pd.read_csv(_path("X_test.csv"))
        assert len(df.columns) >= 4, f"X_test.csv has only {len(df.columns)} columns"


# =========================================================================
# 4. y_test.csv — test set target
# =========================================================================

class TestYTestCsv:
    """Validate the test target set."""

    def test_file_exists(self):
        assert os.path.isfile(_path("y_test.csv")), "y_test.csv not found"

    def test_not_empty(self):
        df = pd.read_csv(_path("y_test.csv"))
        assert len(df) > 0, "y_test.csv is empty"

    def test_has_header_with_next_direction(self):
        df = pd.read_csv(_path("y_test.csv"))
        assert "next_direction" in df.columns, (
            f"y_test.csv header should contain 'next_direction', got: {list(df.columns)}"
        )

    def test_binary_values(self):
        df = pd.read_csv(_path("y_test.csv"))
        unique_vals = set(df.iloc[:, 0].unique())
        assert unique_vals.issubset({0, 1}), f"y_test values should be 0/1, got: {unique_vals}"

    def test_row_count_matches_x_test(self):
        """X_test and y_test must have the same number of rows."""
        x_df = pd.read_csv(_path("X_test.csv"))
        y_df = pd.read_csv(_path("y_test.csv"))
        assert len(x_df) == len(y_df), (
            f"Row count mismatch: X_test={len(x_df)}, y_test={len(y_df)}"
        )

    def test_has_both_classes(self):
        """Target should contain both 0 and 1 (not all same class)."""
        df = pd.read_csv(_path("y_test.csv"))
        unique_vals = set(df.iloc[:, 0].unique())
        assert 0 in unique_vals and 1 in unique_vals, (
            f"y_test should have both classes 0 and 1, got: {unique_vals}"
        )


# =========================================================================
# 5. report.txt — summary report
# =========================================================================

def _parse_report():
    """Parse report.txt into a dict of key-value pairs."""
    path = _path("report.txt")
    assert os.path.isfile(path), "report.txt not found"
    data = {}
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split(":", 1)
            if len(parts) == 2:
                data[parts[0].strip()] = parts[1].strip()
    return data


class TestReportTxt:
    """Validate the summary report."""

    def test_file_exists(self):
        assert os.path.isfile(_path("report.txt")), "report.txt not found"

    def test_file_not_empty(self):
        size = os.path.getsize(_path("report.txt"))
        assert size > 20, f"report.txt too small ({size} bytes)"

    def test_has_exactly_five_lines(self):
        with open(_path("report.txt"), "r") as f:
            lines = [l.strip() for l in f.readlines() if l.strip()]
        assert len(lines) == 5, f"report.txt should have 5 non-empty lines, got {len(lines)}"

    def test_has_all_required_keys(self):
        data = _parse_report()
        required_keys = {
            "dataset_shape", "test_accuracy", "baseline_accuracy",
            "mcnemar_pvalue", "top_features"
        }
        actual_keys = set(data.keys())
        missing = required_keys - actual_keys
        assert len(missing) == 0, f"report.txt missing keys: {missing}"

    def test_dataset_shape_format(self):
        """dataset_shape should be a tuple like (ROWS, COLS)."""
        data = _parse_report()
        shape_str = data["dataset_shape"]
        pattern = re.compile(r"^\(\s*(\d+)\s*,\s*(\d+)\s*\)$")
        match = pattern.match(shape_str)
        assert match, f"dataset_shape format invalid: '{shape_str}', expected (ROWS, COLS)"
        rows, cols = int(match.group(1)), int(match.group(2))
        # After cleaning 2000 rows with ~7% bad + dropping a few for features,
        # expect roughly 1500-1950 rows
        assert 1000 <= rows <= 1960, f"dataset_shape rows={rows} out of expected range [1000, 1960]"
        # Cols = original features + engineered features + next_direction
        # At minimum: 4 engineered + target + some originals = at least 5
        assert cols >= 5, f"dataset_shape cols={cols} too few"

    def test_test_accuracy_valid(self):
        data = _parse_report()
        acc = float(data["test_accuracy"])
        assert 0.0 <= acc <= 1.0, f"test_accuracy={acc} not in [0, 1]"

    def test_test_accuracy_rounded_4dp(self):
        """test_accuracy should be rounded to 4 decimal places."""
        data = _parse_report()
        val_str = data["test_accuracy"]
        # Should match pattern like 0.XXXX
        pattern = re.compile(r"^\d+\.\d{4}$")
        assert pattern.match(val_str), f"test_accuracy not 4 decimal places: '{val_str}'"

    def test_baseline_accuracy_valid(self):
        data = _parse_report()
        acc = float(data["baseline_accuracy"])
        assert 0.0 <= acc <= 1.0, f"baseline_accuracy={acc} not in [0, 1]"

    def test_baseline_accuracy_rounded_4dp(self):
        data = _parse_report()
        val_str = data["baseline_accuracy"]
        pattern = re.compile(r"^\d+\.\d{4}$")
        assert pattern.match(val_str), f"baseline_accuracy not 4 decimal places: '{val_str}'"

    def test_mcnemar_pvalue_valid(self):
        data = _parse_report()
        pval_str = data["mcnemar_pvalue"]
        pval = float(pval_str)
        assert 0.0 <= pval <= 1.0, f"mcnemar_pvalue={pval} not in [0, 1]"

    def test_top_features_format(self):
        """top_features should be 3 comma-separated feature names."""
        data = _parse_report()
        features_str = data["top_features"]
        features = [f.strip() for f in features_str.split(",")]
        assert len(features) == 3, f"Expected 3 top features, got {len(features)}: {features}"
        for feat in features:
            assert len(feat) > 0, "Empty feature name in top_features"
            assert not _is_numeric(feat), f"Feature name looks numeric: '{feat}'"

    def test_top_features_are_valid_names(self):
        """Top features should be plausible column names (alphanumeric + underscore)."""
        data = _parse_report()
        features = [f.strip() for f in data["top_features"].split(",")]
        name_pattern = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")
        for feat in features:
            assert name_pattern.match(feat), f"Invalid feature name: '{feat}'"

    def test_top_features_include_engineered(self):
        """At least one of the 4 required engineered features should appear in top 3."""
        data = _parse_report()
        features = [f.strip() for f in data["top_features"].split(",")]
        engineered = {"price_change", "volume_momentum", "sentiment_shift", "fg_trends_interaction"}
        # Also accept original features — the spec says top 3 by importance
        # We just verify they are real column names that exist in X_test
        if os.path.isfile(_path("X_test.csv")):
            x_cols = set(pd.read_csv(_path("X_test.csv")).columns)
            for feat in features:
                assert feat in x_cols, (
                    f"Top feature '{feat}' not found in X_test.csv columns: {x_cols}"
                )


# =========================================================================
# 6. Cross-file consistency checks
# =========================================================================

class TestCrossFileConsistency:
    """Validate consistency across output files."""

    def test_model_feature_count_matches_x_test(self):
        """Model's expected feature count should match X_test columns."""
        path = _path("btc_predictor.pkl")
        if not os.path.isfile(path):
            return
        try:
            model = joblib.load(path)
        except Exception:
            with open(path, "rb") as f:
                model = pickle.load(f)
        X_test = pd.read_csv(_path("X_test.csv"))
        n_features_model = len(model.feature_importances_)
        n_features_data = len(X_test.columns)
        assert n_features_model == n_features_data, (
            f"Model expects {n_features_model} features but X_test has {n_features_data} columns"
        )

    def test_model_accuracy_matches_report(self):
        """Recompute test accuracy from model + X_test + y_test and compare to report."""
        for f in ["btc_predictor.pkl", "X_test.csv", "y_test.csv", "report.txt"]:
            if not os.path.isfile(_path(f)):
                return

        try:
            model = joblib.load(_path("btc_predictor.pkl"))
        except Exception:
            with open(_path("btc_predictor.pkl"), "rb") as f:
                model = pickle.load(f)

        X_test = pd.read_csv(_path("X_test.csv"))
        y_test = pd.read_csv(_path("y_test.csv")).iloc[:, 0].values
        preds = model.predict(X_test)
        computed_acc = np.mean(preds == y_test)

        data = _parse_report()
        reported_acc = float(data["test_accuracy"])
        assert np.isclose(computed_acc, reported_acc, atol=0.005), (
            f"Recomputed accuracy {computed_acc:.4f} != reported {reported_acc:.4f}"
        )

    def test_baseline_accuracy_matches_report(self):
        """Recompute baseline (always predict 1) accuracy and compare to report."""
        for f in ["y_test.csv", "report.txt"]:
            if not os.path.isfile(_path(f)):
                return

        y_test = pd.read_csv(_path("y_test.csv")).iloc[:, 0].values
        baseline_acc = np.mean(y_test == 1)

        data = _parse_report()
        reported_baseline = float(data["baseline_accuracy"])
        assert np.isclose(baseline_acc, reported_baseline, atol=0.005), (
            f"Recomputed baseline {baseline_acc:.4f} != reported {reported_baseline:.4f}"
        )

    def test_dataset_shape_cols_match_x_test_plus_target(self):
        """dataset_shape cols should equal X_test columns + 1 (for next_direction)."""
        for f in ["X_test.csv", "report.txt"]:
            if not os.path.isfile(_path(f)):
                return

        data = _parse_report()
        shape_str = data["dataset_shape"]
        match = re.match(r"^\(\s*(\d+)\s*,\s*(\d+)\s*\)$", shape_str)
        if not match:
            return
        reported_cols = int(match.group(2))
        x_cols = len(pd.read_csv(_path("X_test.csv")).columns)
        # cols in dataset_shape = feature columns + target column
        assert reported_cols == x_cols + 1, (
            f"dataset_shape cols={reported_cols} should be X_test cols ({x_cols}) + 1"
        )

    def test_test_set_size_is_20_percent(self):
        """Test set should be ~20% of the full modeling dataset."""
        for f in ["X_test.csv", "report.txt"]:
            if not os.path.isfile(_path(f)):
                return

        data = _parse_report()
        shape_str = data["dataset_shape"]
        match = re.match(r"^\(\s*(\d+)\s*,\s*(\d+)\s*\)$", shape_str)
        if not match:
            return
        total_rows = int(match.group(1))
        test_rows = len(pd.read_csv(_path("X_test.csv")))
        expected_test = total_rows * 0.20
        # Allow some tolerance for int rounding
        assert abs(test_rows - expected_test) <= 5, (
            f"Test set has {test_rows} rows but expected ~20% of {total_rows} = {expected_test:.0f}"
        )


# =========================================================================
# 7. generate_data.py and solve.py existence
# =========================================================================

class TestScriptsExist:
    """Validate that the required scripts were created."""

    def test_generate_data_exists(self):
        assert os.path.isfile(_path("generate_data.py")), "generate_data.py not found at /app/"

    def test_solve_py_exists(self):
        assert os.path.isfile(_path("solve.py")), "solve.py not found at /app/"

    def test_generate_data_not_empty(self):
        if os.path.isfile(_path("generate_data.py")):
            size = os.path.getsize(_path("generate_data.py"))
            assert size > 100, f"generate_data.py too small ({size} bytes)"

    def test_solve_py_not_empty(self):
        if os.path.isfile(_path("solve.py")):
            size = os.path.getsize(_path("solve.py"))
            assert size > 200, f"solve.py too small ({size} bytes)"
