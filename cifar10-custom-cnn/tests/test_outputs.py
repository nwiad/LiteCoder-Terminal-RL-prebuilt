import os
import json
import numpy as np
from PIL import Image

# Expected output directory
OUTPUT_DIR = "/app"

def test_all_files_exist():
    """Test that all required output files exist"""
    required_files = [
        "metrics.json",
        "training_curves.png",
        "confusion_matrix.png",
        "model_weights.pth"
    ]

    for filename in required_files:
        filepath = os.path.join(OUTPUT_DIR, filename)
        assert os.path.exists(filepath), f"Missing required file: {filename}"
        assert os.path.getsize(filepath) > 0, f"File is empty: {filename}"


def test_metrics_json_structure():
    """Test that metrics.json has correct structure and valid data"""
    filepath = os.path.join(OUTPUT_DIR, "metrics.json")

    # Load JSON
    with open(filepath, 'r') as f:
        metrics = json.load(f)

    # Check required keys
    required_keys = [
        "train_loss", "train_accuracy",
        "val_loss", "val_accuracy",
        "test_accuracy", "total_parameters", "confusion_matrix"
    ]
    for key in required_keys:
        assert key in metrics, f"Missing key in metrics.json: {key}"

    # Validate train_loss
    assert isinstance(metrics["train_loss"], list), "train_loss must be a list"
    assert len(metrics["train_loss"]) > 0, "train_loss cannot be empty"
    for val in metrics["train_loss"]:
        assert isinstance(val, (int, float)), "train_loss values must be numeric"
        assert val >= 0, "train_loss values must be non-negative"

    # Validate train_accuracy
    assert isinstance(metrics["train_accuracy"], list), "train_accuracy must be a list"
    assert len(metrics["train_accuracy"]) == len(metrics["train_loss"]), \
        "train_accuracy and train_loss must have same length"
    for val in metrics["train_accuracy"]:
        assert isinstance(val, (int, float)), "train_accuracy values must be numeric"
        assert 0 <= val <= 1, "train_accuracy values must be between 0 and 1"

    # Validate val_loss
    assert isinstance(metrics["val_loss"], list), "val_loss must be a list"
    assert len(metrics["val_loss"]) == len(metrics["train_loss"]), \
        "val_loss and train_loss must have same length"
    for val in metrics["val_loss"]:
        assert isinstance(val, (int, float)), "val_loss values must be numeric"
        assert val >= 0, "val_loss values must be non-negative"

    # Validate val_accuracy
    assert isinstance(metrics["val_accuracy"], list), "val_accuracy must be a list"
    assert len(metrics["val_accuracy"]) == len(metrics["train_loss"]), \
        "val_accuracy and train_loss must have same length"
    for val in metrics["val_accuracy"]:
        assert isinstance(val, (int, float)), "val_accuracy values must be numeric"
        assert 0 <= val <= 1, "val_accuracy values must be between 0 and 1"

    # Validate test_accuracy
    assert isinstance(metrics["test_accuracy"], (int, float)), \
        "test_accuracy must be numeric"
    assert 0 <= metrics["test_accuracy"] <= 1, \
        "test_accuracy must be between 0 and 1"
    assert metrics["test_accuracy"] > 0.4, \
        f"test_accuracy must be > 0.4, got {metrics['test_accuracy']}"

    # Validate total_parameters
    assert isinstance(metrics["total_parameters"], int), \
        "total_parameters must be an integer"
    assert metrics["total_parameters"] > 0, \
        "total_parameters must be positive"

    # Validate confusion_matrix
    assert isinstance(metrics["confusion_matrix"], list), \
        "confusion_matrix must be a list"
    assert len(metrics["confusion_matrix"]) == 10, \
        "confusion_matrix must be 10x10 (10 rows)"

    for row in metrics["confusion_matrix"]:
        assert isinstance(row, list), "confusion_matrix rows must be lists"
        assert len(row) == 10, "confusion_matrix must be 10x10 (10 columns)"
        for val in row:
            assert isinstance(val, int), "confusion_matrix values must be integers"
            assert val >= 0, "confusion_matrix values must be non-negative"

    # Check that confusion matrix sums to test set size (10000 for CIFAR-10)
    total_predictions = sum(sum(row) for row in metrics["confusion_matrix"])
    assert total_predictions == 10000, \
        f"confusion_matrix should sum to 10000 (CIFAR-10 test set size), got {total_predictions}"


def test_training_curves_png():
    """Test that training_curves.png is a valid image"""
    filepath = os.path.join(OUTPUT_DIR, "training_curves.png")

    # Try to open as image
    try:
        img = Image.open(filepath)
        img.verify()
    except Exception as e:
        assert False, f"training_curves.png is not a valid image: {e}"

    # Reopen to check dimensions (verify() closes the file)
    img = Image.open(filepath)
    width, height = img.size
    assert width > 0 and height > 0, "Image has invalid dimensions"
    assert img.format == "PNG", "Image must be PNG format"


def test_confusion_matrix_png():
    """Test that confusion_matrix.png is a valid image"""
    filepath = os.path.join(OUTPUT_DIR, "confusion_matrix.png")

    # Try to open as image
    try:
        img = Image.open(filepath)
        img.verify()
    except Exception as e:
        assert False, f"confusion_matrix.png is not a valid image: {e}"

    # Reopen to check dimensions
    img = Image.open(filepath)
    width, height = img.size
    assert width > 0 and height > 0, "Image has invalid dimensions"
    assert img.format == "PNG", "Image must be PNG format"


def test_model_weights_pth():
    """Test that model_weights.pth is a valid file with reasonable size"""
    filepath = os.path.join(OUTPUT_DIR, "model_weights.pth")

    # Check file size is reasonable (should be at least a few KB for a CNN)
    file_size = os.path.getsize(filepath)
    assert file_size > 1000, \
        f"model_weights.pth seems too small ({file_size} bytes), likely invalid"


def test_training_progression():
    """Test that training shows learning (not just random outputs)"""
    filepath = os.path.join(OUTPUT_DIR, "metrics.json")

    with open(filepath, 'r') as f:
        metrics = json.load(f)

    train_acc = metrics["train_accuracy"]
    val_acc = metrics["val_accuracy"]

    # Check that training accuracy improves over time
    # Compare first 20% of epochs to last 20%
    early_epochs = int(len(train_acc) * 0.2)
    if early_epochs == 0:
        early_epochs = 1

    early_train_acc = np.mean(train_acc[:early_epochs])
    late_train_acc = np.mean(train_acc[-early_epochs:])

    assert late_train_acc > early_train_acc, \
        f"Training accuracy should improve over time. Early: {early_train_acc:.4f}, Late: {late_train_acc:.4f}"

    # Check that validation accuracy is reasonable (not all zeros or ones)
    assert np.mean(val_acc) > 0.1, "Validation accuracy too low, model not learning"
    assert np.mean(val_acc) < 0.99, "Validation accuracy suspiciously high"


def test_confusion_matrix_diagonal_dominance():
    """Test that confusion matrix shows reasonable predictions (diagonal should be strong)"""
    filepath = os.path.join(OUTPUT_DIR, "metrics.json")

    with open(filepath, 'r') as f:
        metrics = json.load(f)

    conf_matrix = np.array(metrics["confusion_matrix"])

    # Calculate diagonal sum vs total sum
    diagonal_sum = np.trace(conf_matrix)
    total_sum = np.sum(conf_matrix)

    diagonal_ratio = diagonal_sum / total_sum

    # With >40% accuracy, diagonal should dominate
    assert diagonal_ratio > 0.4, \
        f"Confusion matrix diagonal ratio too low ({diagonal_ratio:.4f}), suggests poor predictions"


def test_no_hardcoded_dummy_data():
    """Test that metrics are not hardcoded dummy values"""
    filepath = os.path.join(OUTPUT_DIR, "metrics.json")

    with open(filepath, 'r') as f:
        metrics = json.load(f)

    # Check that arrays don't have all identical values
    train_loss = metrics["train_loss"]
    assert len(set(train_loss)) > 1, "train_loss has all identical values (likely hardcoded)"

    train_acc = metrics["train_accuracy"]
    assert len(set(train_acc)) > 1, "train_accuracy has all identical values (likely hardcoded)"

    # Check confusion matrix is not all zeros or uniform
    conf_matrix = np.array(metrics["confusion_matrix"])
    assert np.sum(conf_matrix) > 0, "confusion_matrix is all zeros"
    assert np.std(conf_matrix) > 0, "confusion_matrix has no variance (likely dummy data)"


def test_metrics_consistency():
    """Test that test_accuracy is consistent with confusion matrix"""
    filepath = os.path.join(OUTPUT_DIR, "metrics.json")

    with open(filepath, 'r') as f:
        metrics = json.load(f)

    # Calculate accuracy from confusion matrix
    conf_matrix = np.array(metrics["confusion_matrix"])
    correct_predictions = np.trace(conf_matrix)
    total_predictions = np.sum(conf_matrix)
    calculated_accuracy = correct_predictions / total_predictions

    reported_accuracy = metrics["test_accuracy"]

    # Allow small floating point differences
    assert np.isclose(calculated_accuracy, reported_accuracy, atol=0.001), \
        f"test_accuracy ({reported_accuracy:.4f}) doesn't match confusion matrix accuracy ({calculated_accuracy:.4f})"
