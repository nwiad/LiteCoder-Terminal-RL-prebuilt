"""
Tests for Build CPU-only PyTorch 2.4 from Source with MKL Backend.

Validates:
1. Wheel file exists in /app/dist/ with correct naming pattern
2. Wheel file is a valid, non-trivial archive (not a dummy)
3. validation_report.json exists with correct schema
4. All report fields have correct types and expected values
5. wheel_path in report matches an actual file on disk
6. blas_info contains MKL-related content
7. Wheel file is large enough to be a real PyTorch build
"""

import os
import json
import glob
import zipfile

# ── Paths ──────────────────────────────────────────────────────────────
DIST_DIR = "/app/dist"
REPORT_PATH = "/app/validation_report.json"
WHEEL_PATTERN = os.path.join(DIST_DIR, "torch-2.4*.whl")

# Minimum wheel size: a real CPU PyTorch 2.4 wheel is typically 150+ MB.
# We use a conservative 50 MB threshold to avoid false negatives from
# different build configs while still catching empty/dummy files.
MIN_WHEEL_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB

REQUIRED_REPORT_FIELDS = [
    "wheel_path",
    "torch_version",
    "mkl_enabled",
    "cuda_available",
    "blas_info",
    "tensor_test_passed",
    "matrix_mul_test_passed",
]


# ── Helpers ────────────────────────────────────────────────────────────
def _find_wheel_files():
    """Return list of wheel files matching the expected pattern."""
    return glob.glob(WHEEL_PATTERN)


def _load_report():
    """Load and return the validation report as a dict."""
    assert os.path.isfile(REPORT_PATH), (
        f"Validation report not found at {REPORT_PATH}"
    )
    with open(REPORT_PATH, "r") as f:
        content = f.read().strip()
    assert len(content) > 0, "validation_report.json is empty"
    return json.loads(content)


# ══════════════════════════════════════════════════════════════════════
# WHEEL FILE TESTS
# ══════════════════════════════════════════════════════════════════════

class TestWheelFile:
    """Tests for the built .whl artifact."""

    def test_dist_directory_exists(self):
        """The /app/dist/ directory must exist."""
        assert os.path.isdir(DIST_DIR), f"Directory {DIST_DIR} does not exist"

    def test_wheel_file_exists(self):
        """At least one torch-2.4*.whl file must be present in /app/dist/."""
        wheels = _find_wheel_files()
        assert len(wheels) >= 1, (
            f"No wheel file matching 'torch-2.4*.whl' found in {DIST_DIR}. "
            f"Contents: {os.listdir(DIST_DIR) if os.path.isdir(DIST_DIR) else 'N/A'}"
        )

    def test_wheel_filename_format(self):
        """Wheel filename must start with 'torch-2.4' and end with '.whl'."""
        wheels = _find_wheel_files()
        assert len(wheels) >= 1, "No wheel file found"
        for whl in wheels:
            basename = os.path.basename(whl)
            assert basename.startswith("torch-2.4"), (
                f"Wheel filename '{basename}' does not start with 'torch-2.4'"
            )
            assert basename.endswith(".whl"), (
                f"Wheel filename '{basename}' does not end with '.whl'"
            )

    def test_wheel_is_valid_zip(self):
        """A .whl file is a zip archive; it must be a valid one."""
        wheels = _find_wheel_files()
        assert len(wheels) >= 1, "No wheel file found"
        whl = wheels[0]
        assert zipfile.is_zipfile(whl), (
            f"Wheel file {whl} is not a valid zip archive"
        )

    def test_wheel_contains_torch_package(self):
        """The wheel archive must contain torch package files."""
        wheels = _find_wheel_files()
        assert len(wheels) >= 1, "No wheel file found"
        whl = wheels[0]
        with zipfile.ZipFile(whl, "r") as zf:
            names = zf.namelist()
            # A real torch wheel contains torch/__init__.py or similar
            torch_files = [n for n in names if n.startswith("torch/")]
            assert len(torch_files) > 0, (
                f"Wheel does not contain any 'torch/' entries. "
                f"Found {len(names)} entries total."
            )

    def test_wheel_minimum_size(self):
        """A real PyTorch wheel is large (100s of MB). Reject tiny dummies."""
        wheels = _find_wheel_files()
        assert len(wheels) >= 1, "No wheel file found"
        whl = wheels[0]
        size = os.path.getsize(whl)
        assert size >= MIN_WHEEL_SIZE_BYTES, (
            f"Wheel file is only {size / (1024*1024):.1f} MB, expected at least "
            f"{MIN_WHEEL_SIZE_BYTES / (1024*1024):.0f} MB for a real PyTorch build"
        )


# ══════════════════════════════════════════════════════════════════════
# VALIDATION REPORT TESTS
# ══════════════════════════════════════════════════════════════════════

class TestValidationReportStructure:
    """Tests for the structure and schema of validation_report.json."""

    def test_report_file_exists(self):
        """validation_report.json must exist at /app/."""
        assert os.path.isfile(REPORT_PATH), (
            f"Validation report not found at {REPORT_PATH}"
        )

    def test_report_is_valid_json(self):
        """The report must be parseable JSON."""
        with open(REPORT_PATH, "r") as f:
            content = f.read().strip()
        assert len(content) > 0, "validation_report.json is empty"
        try:
            json.loads(content)
        except json.JSONDecodeError as e:
            raise AssertionError(f"validation_report.json is not valid JSON: {e}")

    def test_report_has_all_required_fields(self):
        """The report must contain all 7 required fields."""
        report = _load_report()
        for field in REQUIRED_REPORT_FIELDS:
            assert field in report, (
                f"Required field '{field}' missing from validation report. "
                f"Found fields: {list(report.keys())}"
            )

    def test_report_field_types(self):
        """Each field must have the correct type."""
        report = _load_report()
        # String fields
        for field in ["wheel_path", "torch_version", "blas_info"]:
            if field in report:
                assert isinstance(report[field], str), (
                    f"Field '{field}' should be a string, got {type(report[field]).__name__}"
                )
        # Boolean fields
        for field in ["mkl_enabled", "cuda_available", "tensor_test_passed", "matrix_mul_test_passed"]:
            if field in report:
                assert isinstance(report[field], bool), (
                    f"Field '{field}' should be a boolean, got {type(report[field]).__name__}"
                )


# ══════════════════════════════════════════════════════════════════════
# VALIDATION REPORT VALUE TESTS
# ══════════════════════════════════════════════════════════════════════

class TestValidationReportValues:
    """Tests for the correctness of values in validation_report.json."""

    def test_torch_version_starts_with_2_4(self):
        """torch_version must start with '2.4'."""
        report = _load_report()
        version = report.get("torch_version", "")
        assert isinstance(version, str) and len(version) > 0, (
            "torch_version is empty or missing"
        )
        assert version.startswith("2.4"), (
            f"torch_version '{version}' does not start with '2.4'"
        )

    def test_mkl_enabled_is_true(self):
        """MKL must be enabled (the whole point of this task)."""
        report = _load_report()
        assert report.get("mkl_enabled") is True, (
            f"mkl_enabled should be True, got {report.get('mkl_enabled')}"
        )

    def test_cuda_available_is_false(self):
        """CUDA must be disabled for a CPU-only build."""
        report = _load_report()
        assert report.get("cuda_available") is False, (
            f"cuda_available should be False, got {report.get('cuda_available')}"
        )

    def test_tensor_test_passed(self):
        """Basic tensor operations must have passed."""
        report = _load_report()
        assert report.get("tensor_test_passed") is True, (
            f"tensor_test_passed should be True, got {report.get('tensor_test_passed')}"
        )

    def test_matrix_mul_test_passed(self):
        """Matrix multiplication test must have passed."""
        report = _load_report()
        assert report.get("matrix_mul_test_passed") is True, (
            f"matrix_mul_test_passed should be True, got {report.get('matrix_mul_test_passed')}"
        )

    def test_blas_info_is_nonempty(self):
        """blas_info must be a non-empty string."""
        report = _load_report()
        blas = report.get("blas_info", "")
        assert isinstance(blas, str) and len(blas.strip()) > 0, (
            "blas_info is empty or missing"
        )

    def test_blas_info_mentions_mkl(self):
        """blas_info should reference MKL since that's the configured backend."""
        report = _load_report()
        blas = report.get("blas_info", "").lower()
        assert "mkl" in blas, (
            f"blas_info does not mention 'mkl'. Got: '{report.get('blas_info', '')}'"
        )


# ══════════════════════════════════════════════════════════════════════
# CROSS-VALIDATION TESTS
# ══════════════════════════════════════════════════════════════════════

class TestCrossValidation:
    """Tests that verify consistency between the wheel and the report."""

    def test_wheel_path_matches_actual_file(self):
        """The wheel_path in the report must correspond to a real file in /app/dist/."""
        report = _load_report()
        wheel_path_field = report.get("wheel_path", "")
        assert isinstance(wheel_path_field, str) and len(wheel_path_field) > 0, (
            "wheel_path is empty or missing in report"
        )
        # wheel_path should be just the filename (basename)
        basename = os.path.basename(wheel_path_field)
        full_path = os.path.join(DIST_DIR, basename)
        assert os.path.isfile(full_path), (
            f"wheel_path '{wheel_path_field}' in report does not match any file. "
            f"Expected file at {full_path}. "
            f"Dist contents: {os.listdir(DIST_DIR) if os.path.isdir(DIST_DIR) else 'N/A'}"
        )

    def test_wheel_path_matches_pattern(self):
        """The wheel_path field must match the torch-2.4*.whl pattern."""
        report = _load_report()
        wheel_path_field = report.get("wheel_path", "")
        basename = os.path.basename(wheel_path_field)
        assert basename.startswith("torch-2.4"), (
            f"wheel_path basename '{basename}' does not start with 'torch-2.4'"
        )
        assert basename.endswith(".whl"), (
            f"wheel_path basename '{basename}' does not end with '.whl'"
        )

    def test_all_boolean_tests_passed(self):
        """Comprehensive check: all test booleans must be True, cuda must be False."""
        report = _load_report()
        assert report.get("mkl_enabled") is True, "mkl_enabled must be True"
        assert report.get("cuda_available") is False, "cuda_available must be False"
        assert report.get("tensor_test_passed") is True, "tensor_test_passed must be True"
        assert report.get("matrix_mul_test_passed") is True, "matrix_mul_test_passed must be True"
