"""
Tests for Student Performance Dashboard task.
Validates all output files, data quality, model performance, and app structure.
"""
import os
import re
import tarfile
import numpy as np
import pandas as pd

# All paths are absolute as specified in instruction.md
BASE = "/app"
DATA_DIR = os.path.join(BASE, "data")
OUTPUT_DIR = os.path.join(BASE, "outputs")

STUDENTS_CSV = os.path.join(DATA_DIR, "students.csv")
DESC_STATS_CSV = os.path.join(OUTPUT_DIR, "descriptive_stats.csv")
PLOT1_PNG = os.path.join(OUTPUT_DIR, "plot1.png")
PLOT2_PNG = os.path.join(OUTPUT_DIR, "plot2.png")
MODEL_METRICS_TXT = os.path.join(OUTPUT_DIR, "model_metrics.txt")
PREDICTIONS_CSV = os.path.join(OUTPUT_DIR, "predictions.csv")
APP_PY = os.path.join(BASE, "app.py")
ARCHIVE = os.path.join(BASE, "student_dashboard.tar.gz")
README = os.path.join(BASE, "README.md")

REQUIRED_COLUMNS = [
    "student_id",
    "study_hours_per_week",
    "attendance_rate",
    "assignments_completed",
    "previous_grade",
    "extracurricular_hours",
    "final_grade",
]


# ============================================================
# Helper utilities
# ============================================================

def _is_valid_png(path):
    """Check PNG magic bytes."""
    try:
        with open(path, "rb") as f:
            header = f.read(8)
        return header[:8] == b"\x89PNG\r\n\x1a\n"
    except Exception:
        return False


def _read_text(path):
    with open(path, "r") as f:
        return f.read()


# ============================================================
# 1. File existence and non-emptiness
# ============================================================

class TestFileExistence:
    """Every required output file must exist and be non-empty."""

    def _check(self, path):
        assert os.path.isfile(path), f"Missing file: {path}"
        assert os.path.getsize(path) > 0, f"Empty file: {path}"

    def test_students_csv_exists(self):
        self._check(STUDENTS_CSV)

    def test_descriptive_stats_exists(self):
        self._check(DESC_STATS_CSV)

    def test_plot1_exists(self):
        self._check(PLOT1_PNG)

    def test_plot2_exists(self):
        self._check(PLOT2_PNG)

    def test_model_metrics_exists(self):
        self._check(MODEL_METRICS_TXT)

    def test_predictions_exists(self):
        self._check(PREDICTIONS_CSV)

    def test_app_py_exists(self):
        self._check(APP_PY)

    def test_archive_exists(self):
        self._check(ARCHIVE)

    def test_readme_exists(self):
        self._check(README)


# ============================================================
# 2. Dataset validation (students.csv)
# ============================================================

class TestStudentsDataset:

    def _load(self):
        return pd.read_csv(STUDENTS_CSV)

    def test_minimum_rows(self):
        df = self._load()
        assert len(df) >= 200, f"Expected >=200 rows, got {len(df)}"

    def test_required_columns_present(self):
        df = self._load()
        for col in REQUIRED_COLUMNS:
            assert col in df.columns, f"Missing column: {col}"

    def test_student_id_unique(self):
        df = self._load()
        assert df["student_id"].is_unique, "student_id values are not unique"

    def test_student_id_starts_from_1(self):
        df = self._load()
        assert df["student_id"].min() == 1, "student_id should start from 1"

    def test_study_hours_range(self):
        df = self._load()
        col = df["study_hours_per_week"]
        assert col.min() >= 0, "study_hours_per_week has negative values"
        assert col.max() <= 45, "study_hours_per_week exceeds reasonable range"

    def test_attendance_rate_range(self):
        df = self._load()
        col = df["attendance_rate"]
        assert col.min() >= 0.0, "attendance_rate below 0"
        assert col.max() <= 1.0, "attendance_rate above 1"

    def test_assignments_completed_range(self):
        df = self._load()
        col = df["assignments_completed"]
        assert col.min() >= 0, "assignments_completed negative"
        assert col.max() <= 50, "assignments_completed exceeds 50"
        # Should be integers
        assert all(col == col.astype(int)), "assignments_completed should be integers"

    def test_previous_grade_range(self):
        df = self._load()
        col = df["previous_grade"]
        assert col.min() >= 0, "previous_grade below 0"
        assert col.max() <= 100, "previous_grade above 100"

    def test_extracurricular_hours_range(self):
        df = self._load()
        col = df["extracurricular_hours"]
        assert col.min() >= 0, "extracurricular_hours negative"
        assert col.max() <= 25, "extracurricular_hours exceeds reasonable range"

    def test_final_grade_range(self):
        df = self._load()
        col = df["final_grade"]
        assert col.min() >= 0, "final_grade below 0"
        assert col.max() <= 100, "final_grade above 100"

    def test_positive_correlation_study_hours_final_grade(self):
        """Core requirement: study_hours_per_week must positively correlate with final_grade."""
        df = self._load()
        corr = df["study_hours_per_week"].corr(df["final_grade"])
        assert corr > 0, (
            f"study_hours_per_week should positively correlate with final_grade, got r={corr:.4f}"
        )

    def test_final_grade_has_variance(self):
        """Guard against constant final_grade (trivial dataset)."""
        df = self._load()
        assert df["final_grade"].std() > 1.0, "final_grade has almost no variance"


# ============================================================
# 3. Descriptive statistics validation
# ============================================================

class TestDescriptiveStats:

    def _load(self):
        return pd.read_csv(DESC_STATS_CSV, index_col=0)

    def test_has_standard_stats(self):
        """Must contain mean, std, min, max rows (from df.describe() or equivalent)."""
        df = self._load()
        index_lower = [str(i).strip().lower() for i in df.index]
        for stat in ["mean", "std", "min", "max"]:
            assert stat in index_lower, f"Missing statistic row: {stat}"

    def test_covers_numeric_columns(self):
        """Stats should cover the key numeric columns from the dataset."""
        df = self._load()
        cols_lower = [c.strip().lower() for c in df.columns]
        for key_col in ["study_hours_per_week", "final_grade", "attendance_rate"]:
            assert key_col in cols_lower, (
                f"Descriptive stats missing column: {key_col}"
            )

    def test_values_are_numeric(self):
        df = self._load()
        # At least the mean row should be all numeric
        index_lower = [str(i).strip().lower() for i in df.index]
        if "mean" in index_lower:
            mean_idx = index_lower.index("mean")
            mean_row = df.iloc[mean_idx]
            for col in df.columns:
                val = mean_row[col]
                assert pd.notna(val), f"NaN in mean row for column {col}"


# ============================================================
# 4. Plot validation
# ============================================================

class TestPlots:

    def test_plot1_is_valid_png(self):
        assert _is_valid_png(PLOT1_PNG), "plot1.png is not a valid PNG file"

    def test_plot2_is_valid_png(self):
        assert _is_valid_png(PLOT2_PNG), "plot2.png is not a valid PNG file"

    def test_plot1_reasonable_size(self):
        """A real heatmap should be at least a few KB."""
        size = os.path.getsize(PLOT1_PNG)
        assert size > 5000, f"plot1.png too small ({size} bytes) — likely not a real plot"

    def test_plot2_reasonable_size(self):
        size = os.path.getsize(PLOT2_PNG)
        assert size > 5000, f"plot2.png too small ({size} bytes) — likely not a real plot"


# ============================================================
# 5. Model metrics validation
# ============================================================

class TestModelMetrics:

    def _parse_metrics(self):
        text = _read_text(MODEL_METRICS_TXT)
        metrics = {}
        for line in text.strip().splitlines():
            line = line.strip()
            if ":" in line:
                key, val = line.split(":", 1)
                key = key.strip().upper()
                try:
                    metrics[key] = float(val.strip())
                except ValueError:
                    pass
        return metrics

    def test_has_rmse_line(self):
        metrics = self._parse_metrics()
        assert "RMSE" in metrics, "model_metrics.txt missing RMSE line"

    def test_has_r2_line(self):
        metrics = self._parse_metrics()
        assert "R2" in metrics, "model_metrics.txt missing R2 line"

    def test_rmse_is_positive(self):
        metrics = self._parse_metrics()
        assert metrics.get("RMSE", -1) > 0, "RMSE should be positive"

    def test_rmse_is_reasonable(self):
        """RMSE should be less than 50 for a 0-100 scale grade prediction."""
        metrics = self._parse_metrics()
        rmse = metrics.get("RMSE", 999)
        assert rmse < 50, f"RMSE={rmse} is unreasonably high for grade prediction"

    def test_r2_above_threshold(self):
        """Instruction requires R² > 0.5."""
        metrics = self._parse_metrics()
        r2 = metrics.get("R2", -1)
        assert r2 > 0.5, f"R² must be > 0.5, got {r2}"

    def test_r2_at_most_1(self):
        metrics = self._parse_metrics()
        r2 = metrics.get("R2", 2)
        assert r2 <= 1.0, f"R² should be <= 1.0, got {r2}"

    def test_metrics_format(self):
        """Each metric line should match 'KEY: <float>' with 4 decimal places."""
        text = _read_text(MODEL_METRICS_TXT).strip()
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        assert len(lines) >= 2, f"Expected at least 2 metric lines, got {len(lines)}"
        pattern = re.compile(r"^(RMSE|R2)\s*:\s*-?\d+\.\d{4}$")
        for line in lines:
            assert pattern.match(line), (
                f"Metric line does not match required format 'KEY: X.XXXX': '{line}'"
            )


# ============================================================
# 6. Predictions CSV validation
# ============================================================

class TestPredictions:

    def _load(self):
        return pd.read_csv(PREDICTIONS_CSV)

    def test_has_required_columns(self):
        df = self._load()
        assert "actual" in df.columns, "predictions.csv missing 'actual' column"
        assert "predicted" in df.columns, "predictions.csv missing 'predicted' column"

    def test_has_rows(self):
        """Should have roughly 20% of the dataset rows (test set)."""
        df = self._load()
        assert len(df) >= 20, f"predictions.csv has too few rows: {len(df)}"

    def test_actual_values_in_grade_range(self):
        df = self._load()
        assert df["actual"].min() >= 0, "actual grades below 0"
        assert df["actual"].max() <= 100, "actual grades above 100"

    def test_predicted_values_in_reasonable_range(self):
        df = self._load()
        # Predictions might slightly exceed 0-100 but should be close
        assert df["predicted"].min() >= -10, "predicted grades unreasonably low"
        assert df["predicted"].max() <= 110, "predicted grades unreasonably high"

    def test_predictions_not_constant(self):
        """Guard against a model that always predicts the same value."""
        df = self._load()
        assert df["predicted"].std() > 0.5, "Predicted values have no variance (constant predictions)"

    def test_predictions_correlate_with_actual(self):
        """A valid model's predictions should correlate with actual values."""
        df = self._load()
        corr = df["actual"].corr(df["predicted"])
        assert corr > 0.3, f"Predictions poorly correlated with actual (r={corr:.4f})"


# ============================================================
# 7. Dash app validation (static analysis of app.py)
# ============================================================

class TestDashApp:

    def _read_app(self):
        return _read_text(APP_PY)

    def test_imports_dash(self):
        src = self._read_app()
        assert "dash" in src.lower(), "app.py does not import Dash"

    def test_has_slider_component_id(self):
        """Instruction requires slider with id='study-hours-slider'."""
        src = self._read_app()
        assert "study-hours-slider" in src, (
            "app.py missing required component id 'study-hours-slider'"
        )

    def test_has_predicted_grade_output_id(self):
        """Instruction requires output div with id='predicted-grade-output'."""
        src = self._read_app()
        assert "predicted-grade-output" in src, (
            "app.py missing required component id 'predicted-grade-output'"
        )

    def test_has_callback(self):
        """App must have a callback that updates predicted grade."""
        src = self._read_app()
        assert "callback" in src.lower() or "@app.callback" in src, (
            "app.py does not appear to have a Dash callback"
        )

    def test_runs_on_correct_host_port(self):
        """App must run on 0.0.0.0:8050."""
        src = self._read_app()
        assert "0.0.0.0" in src, "app.py should bind to host 0.0.0.0"
        assert "8050" in src, "app.py should use port 8050"

    def test_slider_range(self):
        """Slider should cover 0-40 range for study hours."""
        src = self._read_app()
        # Check that min=0 and max=40 appear near the slider definition
        assert "min" in src and "max" in src, "Slider should have min/max defined"
        # Look for max=40 pattern
        assert re.search(r"max\s*=\s*40", src), "Slider max should be 40"


# ============================================================
# 8. Archive validation
# ============================================================

class TestArchive:

    def test_is_valid_tarball(self):
        assert tarfile.is_tarfile(ARCHIVE), "student_dashboard.tar.gz is not a valid tar file"

    def test_contains_key_files(self):
        """Archive should contain the main project files."""
        with tarfile.open(ARCHIVE, "r:gz") as tf:
            names = tf.getnames()
        # Normalize: strip leading ./ or /
        names_clean = [n.lstrip("./") for n in names]
        # Must contain at least the dataset, app, and some outputs
        found_csv = any("students.csv" in n for n in names_clean)
        found_app = any("app.py" in n for n in names_clean)
        found_metrics = any("model_metrics" in n for n in names_clean)
        assert found_csv, "Archive missing students.csv"
        assert found_app, "Archive missing app.py"
        assert found_metrics, "Archive missing model_metrics.txt"


# ============================================================
# 9. README validation
# ============================================================

class TestReadme:

    def test_readme_has_content(self):
        text = _read_text(README)
        assert len(text.strip()) > 20, "README.md is too short"

    def test_readme_mentions_run_command(self):
        """README should document how to start the dashboard."""
        text = _read_text(README).lower()
        # Should mention running the app somehow
        has_run_info = (
            "python" in text
            or "app.py" in text
            or "dash" in text
            or "8050" in text
            or "run" in text
        )
        assert has_run_info, "README.md should document how to run the dashboard"
