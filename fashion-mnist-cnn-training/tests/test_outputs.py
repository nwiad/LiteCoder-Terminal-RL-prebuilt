"""
Tests for Fashion-MNIST CNN Training Task.

Validates that all required output artifacts exist under /app/,
that output.json conforms to the required schema with correct metrics,
that model files are valid, and that the training curves image is real.
"""

import os
import json

# ── Constants ────────────────────────────────────────────────────────────────

APP_DIR = "/app"
OUTPUT_JSON = os.path.join(APP_DIR, "output.json")
FINAL_MODEL_H5 = os.path.join(APP_DIR, "fashion_mnist_cnn.h5")
BEST_MODEL_H5 = os.path.join(APP_DIR, "best_model.h5")
SAVED_MODEL_DIR = os.path.join(APP_DIR, "saved_model")
TRAINING_CURVES = os.path.join(APP_DIR, "training_curves.png")
LOGS_DIR = os.path.join(APP_DIR, "logs")

EXPECTED_CLASSES = [
    "T-shirt/top", "Trouser", "Pullover", "Dress", "Coat",
    "Sandal", "Shirt", "Sneaker", "Bag", "Ankle boot",
]

PER_CLASS_METRICS = ["precision", "recall", "f1"]

# Minimum file sizes to reject empty/dummy files
MIN_MODEL_SIZE_BYTES = 10_000       # Real Keras H5 model > 10KB
MIN_PNG_SIZE_BYTES = 1_000          # Real plot PNG > 1KB


# ── Helpers ──────────────────────────────────────────────────────────────────

def load_output_json():
    """Load and return the output.json contents."""
    assert os.path.isfile(OUTPUT_JSON), f"output.json not found at {OUTPUT_JSON}"
    with open(OUTPUT_JSON, "r") as f:
        data = json.load(f)
    return data


def _is_valid_hdf5(path):
    """Check if file starts with the HDF5 magic number (\\x89HDF\\r\\n)."""
    try:
        with open(path, "rb") as f:
            magic = f.read(8)
        return magic[:4] == b"\x89HDF"
    except Exception:
        return False


def _is_valid_png(path):
    """Check if file starts with the PNG magic number."""
    try:
        with open(path, "rb") as f:
            magic = f.read(8)
        return magic[:4] == b"\x89PNG"
    except Exception:
        return False


# ══════════════════════════════════════════════════════════════════════════════
# 1. FILE EXISTENCE TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestFileExistence:
    """All six required output artifacts must exist."""

    def test_output_json_exists(self):
        assert os.path.isfile(OUTPUT_JSON), "output.json missing"

    def test_final_model_h5_exists(self):
        assert os.path.isfile(FINAL_MODEL_H5), "fashion_mnist_cnn.h5 missing"

    def test_best_model_h5_exists(self):
        assert os.path.isfile(BEST_MODEL_H5), "best_model.h5 missing"

    def test_saved_model_dir_exists(self):
        assert os.path.isdir(SAVED_MODEL_DIR), "saved_model/ directory missing"

    def test_training_curves_exists(self):
        assert os.path.isfile(TRAINING_CURVES), "training_curves.png missing"

    def test_logs_dir_exists(self):
        assert os.path.isdir(LOGS_DIR), "logs/ directory missing"


# ══════════════════════════════════════════════════════════════════════════════
# 2. OUTPUT.JSON SCHEMA & CONTENT TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestOutputJsonSchema:
    """Validate the structure and content of output.json."""

    def test_has_test_accuracy(self):
        data = load_output_json()
        assert "test_accuracy" in data, "Missing 'test_accuracy' key"
        assert isinstance(data["test_accuracy"], (int, float)), \
            "test_accuracy must be a number"

    def test_has_test_loss(self):
        data = load_output_json()
        assert "test_loss" in data, "Missing 'test_loss' key"
        assert isinstance(data["test_loss"], (int, float)), \
            "test_loss must be a number"

    def test_has_per_class(self):
        data = load_output_json()
        assert "per_class" in data, "Missing 'per_class' key"
        assert isinstance(data["per_class"], dict), \
            "per_class must be a dictionary"

    def test_all_ten_classes_present(self):
        data = load_output_json()
        per_class = data["per_class"]
        for cls_name in EXPECTED_CLASSES:
            assert cls_name in per_class, \
                f"Missing class '{cls_name}' in per_class"

    def test_no_extra_classes(self):
        data = load_output_json()
        per_class = data["per_class"]
        extra = set(per_class.keys()) - set(EXPECTED_CLASSES)
        assert len(extra) == 0, f"Unexpected extra classes: {extra}"

    def test_per_class_has_required_metrics(self):
        data = load_output_json()
        per_class = data["per_class"]
        for cls_name in EXPECTED_CLASSES:
            if cls_name not in per_class:
                continue
            for metric in PER_CLASS_METRICS:
                assert metric in per_class[cls_name], \
                    f"Class '{cls_name}' missing metric '{metric}'"

    def test_per_class_metrics_are_floats(self):
        data = load_output_json()
        per_class = data["per_class"]
        for cls_name in EXPECTED_CLASSES:
            if cls_name not in per_class:
                continue
            for metric in PER_CLASS_METRICS:
                val = per_class[cls_name].get(metric)
                if val is not None:
                    assert isinstance(val, (int, float)), \
                        f"{cls_name}.{metric} must be numeric, got {type(val)}"


# ══════════════════════════════════════════════════════════════════════════════
# 3. METRIC VALUE RANGE & QUALITY TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestMetricValues:
    """Validate that metric values are in valid ranges and meet thresholds."""

    def test_accuracy_at_least_085(self):
        """Core success criterion: test_accuracy >= 0.85."""
        data = load_output_json()
        acc = data["test_accuracy"]
        assert acc >= 0.85, \
            f"test_accuracy {acc} is below the required threshold of 0.85"

    def test_accuracy_at_most_1(self):
        """Accuracy cannot exceed 1.0."""
        data = load_output_json()
        acc = data["test_accuracy"]
        assert acc <= 1.0, f"test_accuracy {acc} exceeds 1.0 — invalid"

    def test_loss_positive(self):
        """Cross-entropy loss must be positive."""
        data = load_output_json()
        loss = data["test_loss"]
        assert loss > 0, f"test_loss {loss} should be positive"

    def test_loss_reasonable(self):
        """Loss should be reasonable (< 2.5 for a 10-class problem)."""
        data = load_output_json()
        loss = data["test_loss"]
        assert loss < 2.5, \
            f"test_loss {loss} is unreasonably high for Fashion-MNIST"

    def test_per_class_precision_in_range(self):
        data = load_output_json()
        for cls_name in EXPECTED_CLASSES:
            val = data["per_class"][cls_name]["precision"]
            assert 0.0 <= val <= 1.0, \
                f"{cls_name} precision {val} out of [0, 1]"

    def test_per_class_recall_in_range(self):
        data = load_output_json()
        for cls_name in EXPECTED_CLASSES:
            val = data["per_class"][cls_name]["recall"]
            assert 0.0 <= val <= 1.0, \
                f"{cls_name} recall {val} out of [0, 1]"

    def test_per_class_f1_in_range(self):
        data = load_output_json()
        for cls_name in EXPECTED_CLASSES:
            val = data["per_class"][cls_name]["f1"]
            assert 0.0 <= val <= 1.0, \
                f"{cls_name} f1 {val} out of [0, 1]"

    def test_per_class_metrics_not_all_identical(self):
        """Catch hardcoded dummy outputs where every class has the same values."""
        data = load_output_json()
        precisions = [data["per_class"][c]["precision"] for c in EXPECTED_CLASSES]
        recalls = [data["per_class"][c]["recall"] for c in EXPECTED_CLASSES]
        f1s = [data["per_class"][c]["f1"] for c in EXPECTED_CLASSES]
        # At least one of the three metric lists should have variation
        assert len(set(precisions)) > 1 or len(set(recalls)) > 1 or len(set(f1s)) > 1, \
            "All per-class metrics are identical — likely hardcoded dummy output"

    def test_per_class_f1_minimum(self):
        """Each class should have f1 > 0.5 for a model with >= 85% accuracy."""
        data = load_output_json()
        for cls_name in EXPECTED_CLASSES:
            val = data["per_class"][cls_name]["f1"]
            assert val > 0.50, \
                f"{cls_name} f1={val} is too low for a model with >=85% accuracy"

    def test_values_rounded_to_4_decimals(self):
        """All floats should be rounded to at most 4 decimal places."""
        data = load_output_json()
        # Check test_accuracy
        acc_str = str(data["test_accuracy"])
        if "." in acc_str:
            decimals = len(acc_str.split(".")[1])
            assert decimals <= 4, \
                f"test_accuracy has {decimals} decimal places, expected <= 4"
        # Check a sample of per-class metrics
        for cls_name in EXPECTED_CLASSES:
            for metric in PER_CLASS_METRICS:
                val_str = str(data["per_class"][cls_name][metric])
                if "." in val_str:
                    decimals = len(val_str.split(".")[1])
                    assert decimals <= 4, \
                        f"{cls_name}.{metric} has {decimals} decimals, expected <= 4"


# ══════════════════════════════════════════════════════════════════════════════
# 4. MODEL FILE VALIDITY TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestModelFiles:
    """Verify model files are real (not empty or dummy)."""

    def test_final_model_h5_is_valid_hdf5(self):
        """fashion_mnist_cnn.h5 must be a real HDF5 file."""
        assert os.path.isfile(FINAL_MODEL_H5), "fashion_mnist_cnn.h5 missing"
        size = os.path.getsize(FINAL_MODEL_H5)
        assert size > MIN_MODEL_SIZE_BYTES, \
            f"fashion_mnist_cnn.h5 is only {size} bytes — too small for a real model"
        assert _is_valid_hdf5(FINAL_MODEL_H5), \
            "fashion_mnist_cnn.h5 does not have valid HDF5 magic bytes"

    def test_best_model_h5_is_valid_hdf5(self):
        """best_model.h5 must be a real HDF5 file."""
        assert os.path.isfile(BEST_MODEL_H5), "best_model.h5 missing"
        size = os.path.getsize(BEST_MODEL_H5)
        assert size > MIN_MODEL_SIZE_BYTES, \
            f"best_model.h5 is only {size} bytes — too small for a real model"
        assert _is_valid_hdf5(BEST_MODEL_H5), \
            "best_model.h5 does not have valid HDF5 magic bytes"

    def test_saved_model_has_pb_file(self):
        """saved_model/ must contain a saved_model.pb file."""
        assert os.path.isdir(SAVED_MODEL_DIR), "saved_model/ directory missing"
        pb_path = os.path.join(SAVED_MODEL_DIR, "saved_model.pb")
        assert os.path.isfile(pb_path), \
            "saved_model/saved_model.pb not found — not a valid SavedModel"
        size = os.path.getsize(pb_path)
        assert size > 1000, \
            f"saved_model.pb is only {size} bytes — too small"

    def test_saved_model_has_variables(self):
        """saved_model/ must contain a variables/ subdirectory."""
        variables_dir = os.path.join(SAVED_MODEL_DIR, "variables")
        assert os.path.isdir(variables_dir), \
            "saved_model/variables/ directory missing"
        # Should contain at least one file
        files = os.listdir(variables_dir)
        assert len(files) > 0, "saved_model/variables/ is empty"


# ══════════════════════════════════════════════════════════════════════════════
# 5. TRAINING CURVES IMAGE TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestTrainingCurves:
    """Verify training_curves.png is a real plot image."""

    def test_is_valid_png(self):
        assert os.path.isfile(TRAINING_CURVES), "training_curves.png missing"
        assert _is_valid_png(TRAINING_CURVES), \
            "training_curves.png does not have valid PNG magic bytes"

    def test_png_not_trivially_small(self):
        """A real matplotlib plot with 2 subplots should be well over 1KB."""
        size = os.path.getsize(TRAINING_CURVES)
        assert size > MIN_PNG_SIZE_BYTES, \
            f"training_curves.png is only {size} bytes — too small for a real plot"

    def test_png_has_reasonable_dimensions(self):
        """Check the image has reasonable width/height via PIL."""
        try:
            from PIL import Image
            img = Image.open(TRAINING_CURVES)
            w, h = img.size
            # A 14x5 inch figure at 100 dpi = 1400x500 pixels
            assert w >= 200 and h >= 100, \
                f"Image dimensions {w}x{h} are too small for a training curves plot"
        except ImportError:
            # PIL not available — skip dimension check, PNG validity already tested
            pass


# ══════════════════════════════════════════════════════════════════════════════
# 6. TENSORBOARD LOGS TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestTensorBoardLogs:
    """Verify TensorBoard log directory is non-empty."""

    def test_logs_dir_not_empty(self):
        assert os.path.isdir(LOGS_DIR), "logs/ directory missing"
        contents = []
        for root, dirs, files in os.walk(LOGS_DIR):
            contents.extend(files)
        assert len(contents) > 0, \
            "logs/ directory tree contains no files — TensorBoard logging likely not configured"

    def test_logs_contain_event_files(self):
        """TensorBoard writes files starting with 'events.out.tfevents'."""
        found_event = False
        for root, dirs, files in os.walk(LOGS_DIR):
            for f in files:
                if "tfevents" in f:
                    found_event = True
                    break
            if found_event:
                break
        assert found_event, \
            "No TensorBoard event files found in logs/ — expected files containing 'tfevents'"
