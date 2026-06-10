"""
Tests for the CPU-Only Optimized Scikit-Learn Pipeline task.

Validates:
1. Required files exist at /app/
2. credit-g.csv has correct structure (1000 rows, 21 cols, target column)
3. prepare_data.py is a valid, runnable Python script
4. credit_pipeline_final.py runs successfully with exit code 0
5. Output format: last line = "Test Accuracy: 0.XXX", second-to-last = "Wall Time: X.XXXs"
6. Accuracy >= 0.700
7. Wall time <= 20 seconds
8. CLI arguments --timeout and --data-path work
"""

import os
import re
import subprocess
import sys
import time

import pandas as pd
import numpy as np


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
APP_DIR = "/app"
CSV_PATH = os.path.join(APP_DIR, "credit-g.csv")
PREPARE_SCRIPT = os.path.join(APP_DIR, "prepare_data.py")
PIPELINE_SCRIPT = os.path.join(APP_DIR, "credit_pipeline_final.py")

# Regex patterns for output lines
ACCURACY_PATTERN = re.compile(r"^Test Accuracy:\s*([\d]+\.[\d]{3})\s*$")
WALLTIME_PATTERN = re.compile(r"^Wall Time:\s*([\d]+\.[\d]{3})s\s*$")


# ---------------------------------------------------------------------------
# Helper: run the pipeline script and return (stdout, stderr, returncode, elapsed)
# ---------------------------------------------------------------------------
def _run_pipeline(extra_args=None, timeout=60):
    """Run credit_pipeline_final.py and capture outputs."""
    cmd = [sys.executable, PIPELINE_SCRIPT]
    if extra_args:
        cmd.extend(extra_args)
    start = time.time()
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=APP_DIR,
    )
    elapsed = time.time() - start
    return result.stdout, result.stderr, result.returncode, elapsed


# ===========================================================================
# TEST 1: Required files exist
# ===========================================================================
class TestFileExistence:
    def test_prepare_data_exists(self):
        assert os.path.isfile(PREPARE_SCRIPT), (
            f"prepare_data.py not found at {PREPARE_SCRIPT}"
        )

    def test_csv_exists(self):
        assert os.path.isfile(CSV_PATH), (
            f"credit-g.csv not found at {CSV_PATH}"
        )

    def test_pipeline_script_exists(self):
        assert os.path.isfile(PIPELINE_SCRIPT), (
            f"credit_pipeline_final.py not found at {PIPELINE_SCRIPT}"
        )


# ===========================================================================
# TEST 2: CSV structure validation
# ===========================================================================
class TestCSVStructure:
    def test_csv_readable(self):
        """CSV must be readable by pandas."""
        df = pd.read_csv(CSV_PATH)
        assert df is not None

    def test_csv_row_count(self):
        """Dataset must have 1000 samples."""
        df = pd.read_csv(CSV_PATH)
        assert len(df) == 1000, (
            f"Expected 1000 rows, got {len(df)}"
        )

    def test_csv_column_count(self):
        """Dataset must have 21 columns (20 features + target)."""
        df = pd.read_csv(CSV_PATH)
        assert len(df.columns) == 21, (
            f"Expected 21 columns, got {len(df.columns)}"
        )

    def test_csv_has_target_column(self):
        """Last column must be named 'target'."""
        df = pd.read_csv(CSV_PATH)
        assert "target" in df.columns, (
            f"'target' column not found. Columns: {list(df.columns)}"
        )

    def test_csv_target_values(self):
        """Target column must contain 'good' and 'bad' values."""
        df = pd.read_csv(CSV_PATH)
        unique_vals = set(df["target"].unique())
        assert "good" in unique_vals, "Target column missing 'good' value"
        assert "bad" in unique_vals, "Target column missing 'bad' value"
        assert unique_vals == {"good", "bad"}, (
            f"Target column has unexpected values: {unique_vals}"
        )

    def test_csv_not_trivially_small(self):
        """CSV file must have meaningful content (not empty/stub)."""
        file_size = os.path.getsize(CSV_PATH)
        # 1000 rows of tabular data should be at least a few KB
        assert file_size > 5000, (
            f"CSV file suspiciously small: {file_size} bytes"
        )


# ===========================================================================
# TEST 3: prepare_data.py is valid Python
# ===========================================================================
class TestPrepareDataScript:
    def test_prepare_data_is_valid_python(self):
        """prepare_data.py must be syntactically valid Python."""
        result = subprocess.run(
            [sys.executable, "-c", f"import py_compile; py_compile.compile('{PREPARE_SCRIPT}', doraise=True)"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, (
            f"prepare_data.py has syntax errors: {result.stderr}"
        )

    def test_prepare_data_runs(self):
        """prepare_data.py must run without error (CSV already exists)."""
        result = subprocess.run(
            [sys.executable, PREPARE_SCRIPT],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=APP_DIR,
        )
        assert result.returncode == 0, (
            f"prepare_data.py failed with exit code {result.returncode}. "
            f"stderr: {result.stderr}"
        )


# ===========================================================================
# TEST 4: Pipeline script execution and exit code
# ===========================================================================
class TestPipelineExecution:
    def test_pipeline_exit_code_zero(self):
        """Pipeline script must exit with code 0."""
        stdout, stderr, rc, _ = _run_pipeline()
        assert rc == 0, (
            f"Pipeline exited with code {rc}. stderr: {stderr}"
        )

    def test_pipeline_produces_output(self):
        """Pipeline must produce non-empty stdout."""
        stdout, stderr, rc, _ = _run_pipeline()
        assert len(stdout.strip()) > 0, (
            "Pipeline produced no stdout output"
        )


# ===========================================================================
# TEST 5: Output format validation
# ===========================================================================
class TestOutputFormat:
    def test_last_line_accuracy_format(self):
        """Last line of stdout must match 'Test Accuracy: 0.XXX'."""
        stdout, _, rc, _ = _run_pipeline()
        assert rc == 0, f"Pipeline failed with exit code {rc}"
        lines = stdout.strip().splitlines()
        assert len(lines) >= 2, (
            f"Expected at least 2 output lines, got {len(lines)}"
        )
        last_line = lines[-1].strip()
        match = ACCURACY_PATTERN.match(last_line)
        assert match is not None, (
            f"Last line does not match 'Test Accuracy: 0.XXX' format. "
            f"Got: '{last_line}'"
        )

    def test_second_to_last_line_walltime_format(self):
        """Second-to-last line must match 'Wall Time: X.XXXs'."""
        stdout, _, rc, _ = _run_pipeline()
        assert rc == 0, f"Pipeline failed with exit code {rc}"
        lines = stdout.strip().splitlines()
        assert len(lines) >= 2, (
            f"Expected at least 2 output lines, got {len(lines)}"
        )
        second_last = lines[-2].strip()
        match = WALLTIME_PATTERN.match(second_last)
        assert match is not None, (
            f"Second-to-last line does not match 'Wall Time: X.XXXs' format. "
            f"Got: '{second_last}'"
        )


# ===========================================================================
# TEST 6: Accuracy threshold
# ===========================================================================
class TestAccuracy:
    def test_accuracy_at_least_0700(self):
        """Test accuracy must be >= 0.700."""
        stdout, _, rc, _ = _run_pipeline()
        assert rc == 0, f"Pipeline failed with exit code {rc}"
        lines = stdout.strip().splitlines()
        last_line = lines[-1].strip()
        match = ACCURACY_PATTERN.match(last_line)
        assert match is not None, (
            f"Cannot parse accuracy from last line: '{last_line}'"
        )
        accuracy = float(match.group(1))
        assert accuracy >= 0.700, (
            f"Accuracy {accuracy:.3f} is below minimum threshold 0.700"
        )

    def test_accuracy_is_plausible(self):
        """Accuracy must be in a plausible range (0.5 to 1.0) — catches hardcoded values > 1."""
        stdout, _, rc, _ = _run_pipeline()
        assert rc == 0
        lines = stdout.strip().splitlines()
        last_line = lines[-1].strip()
        match = ACCURACY_PATTERN.match(last_line)
        assert match is not None
        accuracy = float(match.group(1))
        assert 0.5 <= accuracy <= 1.0, (
            f"Accuracy {accuracy:.3f} is outside plausible range [0.5, 1.0]"
        )


# ===========================================================================
# TEST 7: Wall time constraint
# ===========================================================================
class TestWallTime:
    def test_reported_walltime_under_20s(self):
        """Reported wall time must be <= 20 seconds."""
        stdout, _, rc, _ = _run_pipeline()
        assert rc == 0, f"Pipeline failed with exit code {rc}"
        lines = stdout.strip().splitlines()
        second_last = lines[-2].strip()
        match = WALLTIME_PATTERN.match(second_last)
        assert match is not None, (
            f"Cannot parse wall time from: '{second_last}'"
        )
        wall_time = float(match.group(1))
        assert wall_time <= 20.0, (
            f"Reported wall time {wall_time:.3f}s exceeds 20s limit"
        )

    def test_actual_walltime_under_25s(self):
        """Actual measured wall time should be reasonable (<=25s with margin)."""
        _, _, rc, elapsed = _run_pipeline()
        assert rc == 0
        # Allow 5s margin over the 20s limit for system overhead
        assert elapsed <= 25.0, (
            f"Actual elapsed time {elapsed:.1f}s is too high (limit 25s with margin)"
        )

    def test_reported_walltime_is_positive(self):
        """Wall time must be a positive number (catches hardcoded 0)."""
        stdout, _, rc, _ = _run_pipeline()
        assert rc == 0
        lines = stdout.strip().splitlines()
        second_last = lines[-2].strip()
        match = WALLTIME_PATTERN.match(second_last)
        assert match is not None
        wall_time = float(match.group(1))
        assert wall_time > 0.0, (
            f"Wall time {wall_time}s is not positive — likely hardcoded"
        )


# ===========================================================================
# TEST 8: CLI arguments
# ===========================================================================
class TestCLIArguments:
    def test_data_path_argument(self):
        """Pipeline must accept --data-path argument."""
        stdout, stderr, rc, _ = _run_pipeline(
            extra_args=["--data-path", APP_DIR]
        )
        assert rc == 0, (
            f"Pipeline failed with --data-path {APP_DIR}. "
            f"stderr: {stderr}"
        )
        lines = stdout.strip().splitlines()
        assert len(lines) >= 2, "Not enough output lines with --data-path"
        last_line = lines[-1].strip()
        match = ACCURACY_PATTERN.match(last_line)
        assert match is not None, (
            f"Output format wrong with --data-path. Last line: '{last_line}'"
        )

    def test_timeout_argument(self):
        """Pipeline must accept --timeout argument."""
        stdout, stderr, rc, _ = _run_pipeline(
            extra_args=["--timeout", "30"]
        )
        assert rc == 0, (
            f"Pipeline failed with --timeout 30. stderr: {stderr}"
        )


# ===========================================================================
# TEST 9: Reproducibility — accuracy should be deterministic
# ===========================================================================
class TestReproducibility:
    def test_deterministic_accuracy(self):
        """Two runs should produce the same accuracy (random_state=42)."""
        stdout1, _, rc1, _ = _run_pipeline()
        assert rc1 == 0, "First run failed"
        stdout2, _, rc2, _ = _run_pipeline()
        assert rc2 == 0, "Second run failed"

        lines1 = stdout1.strip().splitlines()
        lines2 = stdout2.strip().splitlines()

        match1 = ACCURACY_PATTERN.match(lines1[-1].strip())
        match2 = ACCURACY_PATTERN.match(lines2[-1].strip())
        assert match1 and match2, "Could not parse accuracy from one of the runs"

        acc1 = float(match1.group(1))
        acc2 = float(match2.group(1))
        assert np.isclose(acc1, acc2, atol=1e-3), (
            f"Accuracy not deterministic: run1={acc1:.3f}, run2={acc2:.3f}"
        )
