"""
Tests for TFLite int8 optimization task.

Validates:
- Output file existence and non-emptiness
- report.json schema (exact 9 keys, correct types)
- Value constraints from instruction.md
- Internal consistency of computed metrics
- TFLite model validity (loadable FlatBuffer)
"""

import os
import json
import struct
import math

# ---------------------------------------------------------------------------
# Paths — the task runs in /app, outputs land there
# ---------------------------------------------------------------------------
REPORT_PATH = "/app/report.json"
TFLITE_MODEL_PATH = "/app/model_int8.tflite"
SAVED_MODEL_DIR = "/app/saved_model"

REQUIRED_KEYS = {
    "fp32_accuracy",
    "int8_accuracy",
    "accuracy_retention",
    "fp32_latency_ms",
    "int8_latency_ms",
    "fp32_size_bytes",
    "int8_size_bytes",
    "compression_ratio",
    "meets_accuracy_requirement",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_report():
    """Load and return the report dict; raises on missing/invalid file."""
    assert os.path.isfile(REPORT_PATH), f"report.json not found at {REPORT_PATH}"
    size = os.path.getsize(REPORT_PATH)
    assert size > 2, "report.json is empty or trivially small"
    with open(REPORT_PATH, "r") as f:
        data = json.load(f)
    assert isinstance(data, dict), "report.json root must be a JSON object"
    return data


def _decimal_places(value):
    """Return the number of decimal places in a float's string representation."""
    s = f"{value}"
    if "." not in s:
        return 0
    return len(s.split(".")[1])


# ===========================================================================
# 1. FILE EXISTENCE & BASIC VALIDITY
# ===========================================================================

class TestFileExistence:
    """Verify all required output artifacts exist and are non-trivial."""

    def test_report_json_exists(self):
        assert os.path.isfile(REPORT_PATH), "report.json not found"

    def test_report_json_not_empty(self):
        assert os.path.getsize(REPORT_PATH) > 10, "report.json is empty or trivially small"

    def test_tflite_model_exists(self):
        assert os.path.isfile(TFLITE_MODEL_PATH), "model_int8.tflite not found"

    def test_tflite_model_not_empty(self):
        size = os.path.getsize(TFLITE_MODEL_PATH)
        # A real quantized model for IMDB should be at least a few KB
        assert size > 1000, f"model_int8.tflite is suspiciously small ({size} bytes)"

    def test_saved_model_dir_exists(self):
        assert os.path.isdir(SAVED_MODEL_DIR), "saved_model/ directory not found"

    def test_saved_model_dir_not_empty(self):
        files = []
        for dirpath, _, filenames in os.walk(SAVED_MODEL_DIR):
            files.extend(filenames)
        assert len(files) > 0, "saved_model/ directory is empty"


# ===========================================================================
# 2. TFLITE MODEL VALIDITY
# ===========================================================================

class TestTFLiteModelValidity:
    """Verify the .tflite file is a valid FlatBuffer without importing TF."""

    def test_tflite_flatbuffer_magic(self):
        """TFLite FlatBuffers have identifiable structure."""
        with open(TFLITE_MODEL_PATH, "rb") as f:
            data = f.read()
        # FlatBuffer files start with a 4-byte offset to the root table
        assert len(data) >= 8, "TFLite file too small to be a valid FlatBuffer"
        # Read the root table offset (little-endian uint32)
        root_offset = struct.unpack("<I", data[:4])[0]
        assert root_offset < len(data), "Invalid FlatBuffer root offset"

    def test_tflite_contains_tfl3_identifier(self):
        """TFLite FlatBuffers contain the 'TFL3' file identifier at bytes 4-7."""
        with open(TFLITE_MODEL_PATH, "rb") as f:
            data = f.read(8)
        identifier = data[4:8]
        assert identifier == b"TFL3", (
            f"Expected TFLite FlatBuffer identifier 'TFL3', got {identifier!r}"
        )


# ===========================================================================
# 3. REPORT JSON SCHEMA
# ===========================================================================

class TestReportSchema:
    """Verify report.json has exactly the required keys with correct types."""

    def test_report_is_valid_json(self):
        _load_report()  # will raise on invalid JSON

    def test_report_has_all_required_keys(self):
        report = _load_report()
        missing = REQUIRED_KEYS - set(report.keys())
        assert not missing, f"Missing keys in report.json: {missing}"

    def test_report_has_no_extra_keys(self):
        report = _load_report()
        extra = set(report.keys()) - REQUIRED_KEYS
        assert not extra, f"Extra keys in report.json (not allowed): {extra}"

    def test_fp32_accuracy_is_float(self):
        report = _load_report()
        assert isinstance(report["fp32_accuracy"], float), "fp32_accuracy must be float"

    def test_int8_accuracy_is_float(self):
        report = _load_report()
        assert isinstance(report["int8_accuracy"], float), "int8_accuracy must be float"

    def test_accuracy_retention_is_float(self):
        report = _load_report()
        assert isinstance(report["accuracy_retention"], float), "accuracy_retention must be float"

    def test_fp32_latency_ms_is_float(self):
        report = _load_report()
        assert isinstance(report["fp32_latency_ms"], (int, float)), "fp32_latency_ms must be numeric"

    def test_int8_latency_ms_is_float(self):
        report = _load_report()
        assert isinstance(report["int8_latency_ms"], (int, float)), "int8_latency_ms must be numeric"

    def test_fp32_size_bytes_is_int(self):
        report = _load_report()
        assert isinstance(report["fp32_size_bytes"], int), "fp32_size_bytes must be int"

    def test_int8_size_bytes_is_int(self):
        report = _load_report()
        assert isinstance(report["int8_size_bytes"], int), "int8_size_bytes must be int"

    def test_compression_ratio_is_float(self):
        report = _load_report()
        assert isinstance(report["compression_ratio"], (int, float)), "compression_ratio must be numeric"

    def test_meets_accuracy_requirement_is_bool(self):
        report = _load_report()
        assert isinstance(report["meets_accuracy_requirement"], bool), (
            "meets_accuracy_requirement must be a boolean (true/false), not a string or int"
        )


# ===========================================================================
# 4. VALUE CONSTRAINTS (from instruction.md)
# ===========================================================================

class TestValueConstraints:
    """Verify the numeric constraints specified in the instructions."""

    def test_fp32_accuracy_above_random(self):
        """fp32_accuracy must be > 0.5 (better than random guessing)."""
        report = _load_report()
        assert report["fp32_accuracy"] > 0.5, (
            f"fp32_accuracy={report['fp32_accuracy']} is not > 0.5"
        )

    def test_fp32_accuracy_in_valid_range(self):
        report = _load_report()
        assert 0.0 <= report["fp32_accuracy"] <= 1.0, (
            f"fp32_accuracy={report['fp32_accuracy']} out of [0, 1] range"
        )

    def test_int8_accuracy_in_valid_range(self):
        report = _load_report()
        assert 0.0 <= report["int8_accuracy"] <= 1.0, (
            f"int8_accuracy={report['int8_accuracy']} out of [0, 1] range"
        )

    def test_compression_ratio_above_one(self):
        """compression_ratio must be > 1.0 (int8 model smaller than FP32)."""
        report = _load_report()
        assert report["compression_ratio"] > 1.0, (
            f"compression_ratio={report['compression_ratio']} is not > 1.0"
        )

    def test_accuracy_retention_positive(self):
        report = _load_report()
        assert report["accuracy_retention"] > 0.0, (
            f"accuracy_retention={report['accuracy_retention']} must be positive"
        )

    def test_latencies_positive(self):
        report = _load_report()
        assert report["fp32_latency_ms"] > 0.0, "fp32_latency_ms must be positive"
        assert report["int8_latency_ms"] > 0.0, "int8_latency_ms must be positive"

    def test_sizes_positive(self):
        report = _load_report()
        assert report["fp32_size_bytes"] > 0, "fp32_size_bytes must be positive"
        assert report["int8_size_bytes"] > 0, "int8_size_bytes must be positive"

    def test_meets_accuracy_requirement_consistency(self):
        """meets_accuracy_requirement must be True iff accuracy_retention >= 0.9."""
        report = _load_report()
        expected = report["accuracy_retention"] >= 0.9
        assert report["meets_accuracy_requirement"] == expected, (
            f"meets_accuracy_requirement={report['meets_accuracy_requirement']} "
            f"but accuracy_retention={report['accuracy_retention']} "
            f"(expected {'True' if expected else 'False'})"
        )


# ===========================================================================
# 5. INTERNAL CONSISTENCY
# ===========================================================================

class TestInternalConsistency:
    """Cross-check that derived metrics are consistent with base values."""

    def test_accuracy_retention_matches_ratio(self):
        """accuracy_retention ≈ int8_accuracy / fp32_accuracy."""
        report = _load_report()
        fp32_acc = report["fp32_accuracy"]
        int8_acc = report["int8_accuracy"]
        reported_retention = report["accuracy_retention"]
        if fp32_acc > 0:
            expected = int8_acc / fp32_acc
            # Allow tolerance for rounding: both numerator and result are rounded to 4dp
            assert abs(reported_retention - expected) < 0.01, (
                f"accuracy_retention={reported_retention} doesn't match "
                f"int8_accuracy/fp32_accuracy={int8_acc}/{fp32_acc}={expected:.6f}"
            )

    def test_compression_ratio_matches_sizes(self):
        """compression_ratio ≈ fp32_size_bytes / int8_size_bytes."""
        report = _load_report()
        fp32_size = report["fp32_size_bytes"]
        int8_size = report["int8_size_bytes"]
        reported_ratio = report["compression_ratio"]
        if int8_size > 0:
            expected = fp32_size / int8_size
            # Allow tolerance for rounding
            assert abs(reported_ratio - expected) < 0.01, (
                f"compression_ratio={reported_ratio} doesn't match "
                f"fp32_size/int8_size={fp32_size}/{int8_size}={expected:.6f}"
            )

    def test_int8_size_matches_tflite_file(self):
        """int8_size_bytes should match the actual .tflite file size on disk."""
        report = _load_report()
        actual_size = os.path.getsize(TFLITE_MODEL_PATH)
        assert report["int8_size_bytes"] == actual_size, (
            f"int8_size_bytes={report['int8_size_bytes']} but actual "
            f"model_int8.tflite is {actual_size} bytes"
        )

    def test_fp32_size_matches_saved_model_dir(self):
        """fp32_size_bytes should match the total size of saved_model/ directory."""
        report = _load_report()
        total = 0
        for dirpath, _, filenames in os.walk(SAVED_MODEL_DIR):
            for fname in filenames:
                fpath = os.path.join(dirpath, fname)
                if os.path.isfile(fpath):
                    total += os.path.getsize(fpath)
        # Allow some tolerance — different implementations may measure slightly differently
        # but should be within 5% or exact
        if total > 0:
            ratio = report["fp32_size_bytes"] / total
            assert 0.95 <= ratio <= 1.05, (
                f"fp32_size_bytes={report['fp32_size_bytes']} but saved_model/ "
                f"directory total is {total} bytes (ratio={ratio:.4f})"
            )

    def test_int8_smaller_than_fp32(self):
        """The int8 model must actually be smaller than the FP32 model."""
        report = _load_report()
        assert report["int8_size_bytes"] < report["fp32_size_bytes"], (
            f"int8_size_bytes={report['int8_size_bytes']} should be < "
            f"fp32_size_bytes={report['fp32_size_bytes']}"
        )


# ===========================================================================
# 6. ROUNDING & PRECISION
# ===========================================================================

class TestRounding:
    """All float values must be rounded to 4 decimal places."""

    def _check_decimal_places(self, value, key_name):
        """Verify a float has at most 4 decimal places."""
        # Round-trip check: round(value, 4) should equal value exactly
        rounded = round(value, 4)
        assert rounded == value, (
            f"{key_name}={value} is not rounded to 4 decimal places "
            f"(round(value,4)={rounded})"
        )

    def test_fp32_accuracy_rounding(self):
        report = _load_report()
        self._check_decimal_places(report["fp32_accuracy"], "fp32_accuracy")

    def test_int8_accuracy_rounding(self):
        report = _load_report()
        self._check_decimal_places(report["int8_accuracy"], "int8_accuracy")

    def test_accuracy_retention_rounding(self):
        report = _load_report()
        self._check_decimal_places(report["accuracy_retention"], "accuracy_retention")

    def test_fp32_latency_ms_rounding(self):
        report = _load_report()
        self._check_decimal_places(report["fp32_latency_ms"], "fp32_latency_ms")

    def test_int8_latency_ms_rounding(self):
        report = _load_report()
        self._check_decimal_places(report["int8_latency_ms"], "int8_latency_ms")

    def test_compression_ratio_rounding(self):
        report = _load_report()
        self._check_decimal_places(report["compression_ratio"], "compression_ratio")


# ===========================================================================
# 7. ANTI-CHEAT: PLAUSIBILITY CHECKS
# ===========================================================================

class TestPlausibility:
    """Catch hardcoded or fabricated outputs with plausibility checks."""

    def test_fp32_accuracy_plausible_for_imdb(self):
        """A trained IMDB model should achieve 0.6-0.95 accuracy typically."""
        report = _load_report()
        acc = report["fp32_accuracy"]
        assert 0.55 <= acc <= 0.98, (
            f"fp32_accuracy={acc} is outside plausible range [0.55, 0.98] for IMDB"
        )

    def test_int8_accuracy_plausible_for_imdb(self):
        """int8 accuracy should be close to fp32 for a well-quantized model."""
        report = _load_report()
        acc = report["int8_accuracy"]
        assert 0.50 <= acc <= 0.98, (
            f"int8_accuracy={acc} is outside plausible range [0.50, 0.98] for IMDB"
        )

    def test_latency_plausible(self):
        """Latencies should be in a reasonable range (0.01ms to 5000ms per sample)."""
        report = _load_report()
        for key in ["fp32_latency_ms", "int8_latency_ms"]:
            lat = report[key]
            assert 0.01 <= lat <= 5000.0, (
                f"{key}={lat} is outside plausible range [0.01, 5000] ms"
            )

    def test_model_sizes_plausible(self):
        """Model sizes should be in a reasonable range for an IMDB embedding model."""
        report = _load_report()
        # FP32 SavedModel for a small embedding model: typically 500KB - 50MB
        fp32 = report["fp32_size_bytes"]
        assert 100_000 < fp32 < 100_000_000, (
            f"fp32_size_bytes={fp32} is outside plausible range"
        )
        # Int8 TFLite: typically smaller, 50KB - 20MB
        int8 = report["int8_size_bytes"]
        assert 10_000 < int8 < 50_000_000, (
            f"int8_size_bytes={int8} is outside plausible range"
        )

    def test_optimize_script_exists(self):
        """The task requires /app/optimize.py to exist."""
        assert os.path.isfile("/app/optimize.py"), "optimize.py not found at /app/optimize.py"

