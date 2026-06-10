import os
import json
import pytest


def load_results():
    """Load and parse results.json"""
    results_path = "/app/results.json"

    if not os.path.exists(results_path):
        pytest.fail(f"Results file not found at {results_path}")

    if os.path.getsize(results_path) == 0:
        pytest.fail("Results file is empty")

    try:
        with open(results_path, 'r') as f:
            data = json.load(f)
        return data
    except json.JSONDecodeError as e:
        pytest.fail(f"Invalid JSON in results file: {e}")


def test_results_file_exists():
    """Test that results.json exists and is not empty"""
    results_path = "/app/results.json"
    assert os.path.exists(results_path), "results.json does not exist"
    assert os.path.getsize(results_path) > 0, "results.json is empty"


def test_json_structure():
    """Test that JSON has all required top-level keys"""
    data = load_results()

    required_keys = ['focal_loss_model', 'crossentropy_model', 'comparison']
    for key in required_keys:
        assert key in data, f"Missing required key: {key}"


def test_focal_loss_model_structure():
    """Test focal_loss_model has all required fields with correct types"""
    data = load_results()
    focal = data['focal_loss_model']

    # Check all required fields exist
    required_fields = ['test_accuracy', 'per_class_accuracy', 'final_loss', 'epochs_trained']
    for field in required_fields:
        assert field in focal, f"Missing field in focal_loss_model: {field}"

    # Check types
    assert isinstance(focal['test_accuracy'], (int, float)), "test_accuracy must be numeric"
    assert isinstance(focal['per_class_accuracy'], list), "per_class_accuracy must be a list"
    assert isinstance(focal['final_loss'], (int, float)), "final_loss must be numeric"
    assert isinstance(focal['epochs_trained'], int), "epochs_trained must be an integer"


def test_crossentropy_model_structure():
    """Test crossentropy_model has all required fields with correct types"""
    data = load_results()
    ce = data['crossentropy_model']

    # Check all required fields exist
    required_fields = ['test_accuracy', 'per_class_accuracy', 'final_loss', 'epochs_trained']
    for field in required_fields:
        assert field in ce, f"Missing field in crossentropy_model: {field}"

    # Check types
    assert isinstance(ce['test_accuracy'], (int, float)), "test_accuracy must be numeric"
    assert isinstance(ce['per_class_accuracy'], list), "per_class_accuracy must be a list"
    assert isinstance(ce['final_loss'], (int, float)), "final_loss must be numeric"
    assert isinstance(ce['epochs_trained'], int), "epochs_trained must be an integer"


def test_comparison_structure():
    """Test comparison section has required fields"""
    data = load_results()
    comparison = data['comparison']

    assert 'accuracy_improvement' in comparison, "Missing accuracy_improvement in comparison"
    assert 'better_model' in comparison, "Missing better_model in comparison"

    assert isinstance(comparison['accuracy_improvement'], (int, float)), "accuracy_improvement must be numeric"
    assert isinstance(comparison['better_model'], str), "better_model must be a string"


def test_per_class_accuracy_length():
    """Test that per_class_accuracy has exactly 10 elements (CIFAR-10 classes)"""
    data = load_results()

    focal_per_class = data['focal_loss_model']['per_class_accuracy']
    ce_per_class = data['crossentropy_model']['per_class_accuracy']

    assert len(focal_per_class) == 10, f"focal_loss_model per_class_accuracy must have 10 elements, got {len(focal_per_class)}"
    assert len(ce_per_class) == 10, f"crossentropy_model per_class_accuracy must have 10 elements, got {len(ce_per_class)}"


def test_per_class_accuracy_values():
    """Test that per_class_accuracy values are valid percentages"""
    data = load_results()

    focal_per_class = data['focal_loss_model']['per_class_accuracy']
    ce_per_class = data['crossentropy_model']['per_class_accuracy']

    # Check focal loss per-class accuracies
    for i, acc in enumerate(focal_per_class):
        assert isinstance(acc, (int, float)), f"focal_loss_model per_class_accuracy[{i}] must be numeric"
        assert 0 <= acc <= 100, f"focal_loss_model per_class_accuracy[{i}] must be between 0 and 100, got {acc}"

    # Check crossentropy per-class accuracies
    for i, acc in enumerate(ce_per_class):
        assert isinstance(acc, (int, float)), f"crossentropy_model per_class_accuracy[{i}] must be numeric"
        assert 0 <= acc <= 100, f"crossentropy_model per_class_accuracy[{i}] must be between 0 and 100, got {acc}"


def test_minimum_epochs_trained():
    """Test that both models trained for at least 10 epochs as required"""
    data = load_results()

    focal_epochs = data['focal_loss_model']['epochs_trained']
    ce_epochs = data['crossentropy_model']['epochs_trained']

    assert focal_epochs >= 10, f"focal_loss_model must train for at least 10 epochs, got {focal_epochs}"
    assert ce_epochs >= 10, f"crossentropy_model must train for at least 10 epochs, got {ce_epochs}"


def test_test_accuracy_range():
    """Test that test accuracy values are reasonable (not dummy zeros or impossible values)"""
    data = load_results()

    focal_acc = data['focal_loss_model']['test_accuracy']
    ce_acc = data['crossentropy_model']['test_accuracy']

    # Test accuracy should be between 0 and 100
    assert 0 <= focal_acc <= 100, f"focal_loss_model test_accuracy out of range: {focal_acc}"
    assert 0 <= ce_acc <= 100, f"crossentropy_model test_accuracy out of range: {ce_acc}"

    # For CIFAR-10 with EfficientNet-B0, even with limited training, accuracy should be > 10% (random is 10%)
    # This catches lazy agents that output dummy zeros
    assert focal_acc > 10, f"focal_loss_model test_accuracy too low (likely dummy data): {focal_acc}"
    assert ce_acc > 10, f"crossentropy_model test_accuracy too low (likely dummy data): {ce_acc}"


def test_final_loss_positive():
    """Test that final loss values are positive"""
    data = load_results()

    focal_loss = data['focal_loss_model']['final_loss']
    ce_loss = data['crossentropy_model']['final_loss']

    assert focal_loss > 0, f"focal_loss_model final_loss must be positive, got {focal_loss}"
    assert ce_loss > 0, f"crossentropy_model final_loss must be positive, got {ce_loss}"


def test_accuracy_improvement_calculation():
    """Test that accuracy_improvement is correctly calculated"""
    data = load_results()

    focal_acc = data['focal_loss_model']['test_accuracy']
    ce_acc = data['crossentropy_model']['test_accuracy']
    reported_improvement = data['comparison']['accuracy_improvement']

    # Calculate expected improvement
    expected_improvement = focal_acc - ce_acc

    # Allow small floating point tolerance
    assert abs(reported_improvement - expected_improvement) < 0.1, \
        f"accuracy_improvement mismatch: expected {expected_improvement}, got {reported_improvement}"


def test_better_model_logic():
    """Test that better_model is correctly determined"""
    data = load_results()

    focal_acc = data['focal_loss_model']['test_accuracy']
    ce_acc = data['crossentropy_model']['test_accuracy']
    better_model = data['comparison']['better_model']

    # Check valid values
    assert better_model in ['focal_loss', 'crossentropy'], \
        f"better_model must be 'focal_loss' or 'crossentropy', got '{better_model}'"

    # Check logic consistency
    if focal_acc > ce_acc:
        assert better_model == 'focal_loss', \
            f"focal_loss has higher accuracy ({focal_acc} > {ce_acc}) but better_model is '{better_model}'"
    elif ce_acc > focal_acc:
        assert better_model == 'crossentropy', \
            f"crossentropy has higher accuracy ({ce_acc} > {focal_acc}) but better_model is '{better_model}'"
    # If equal, either is acceptable


def test_per_class_accuracy_not_all_zeros():
    """Test that per-class accuracies are not all zeros (indicates actual training happened)"""
    data = load_results()

    focal_per_class = data['focal_loss_model']['per_class_accuracy']
    ce_per_class = data['crossentropy_model']['per_class_accuracy']

    # At least some classes should have non-zero accuracy
    focal_nonzero = sum(1 for acc in focal_per_class if acc > 0)
    ce_nonzero = sum(1 for acc in ce_per_class if acc > 0)

    assert focal_nonzero >= 8, \
        f"focal_loss_model should have accuracy for most classes, only {focal_nonzero}/10 have non-zero accuracy"
    assert ce_nonzero >= 8, \
        f"crossentropy_model should have accuracy for most classes, only {ce_nonzero}/10 have non-zero accuracy"


def test_imbalanced_classes_present():
    """Test that minority classes (0-4) have some accuracy, indicating they were included in training"""
    data = load_results()

    focal_per_class = data['focal_loss_model']['per_class_accuracy']
    ce_per_class = data['crossentropy_model']['per_class_accuracy']

    # Check that minority classes (0-4) have some representation
    # Even with 20% of samples, models should learn something about these classes
    focal_minority_nonzero = sum(1 for i in range(5) if focal_per_class[i] > 0)
    ce_minority_nonzero = sum(1 for i in range(5) if ce_per_class[i] > 0)

    assert focal_minority_nonzero >= 4, \
        f"focal_loss_model should have accuracy for minority classes (0-4), only {focal_minority_nonzero}/5 have non-zero accuracy"
    assert ce_minority_nonzero >= 4, \
        f"crossentropy_model should have accuracy for minority classes (0-4), only {ce_minority_nonzero}/5 have non-zero accuracy"


def test_majority_classes_present():
    """Test that majority classes (5-9) have good accuracy"""
    data = load_results()

    focal_per_class = data['focal_loss_model']['per_class_accuracy']
    ce_per_class = data['crossentropy_model']['per_class_accuracy']

    # Majority classes should all have non-zero accuracy
    focal_majority_nonzero = sum(1 for i in range(5, 10) if focal_per_class[i] > 0)
    ce_majority_nonzero = sum(1 for i in range(5, 10) if ce_per_class[i] > 0)

    assert focal_majority_nonzero == 5, \
        f"focal_loss_model should have accuracy for all majority classes (5-9), only {focal_majority_nonzero}/5 have non-zero accuracy"
    assert ce_majority_nonzero == 5, \
        f"crossentropy_model should have accuracy for all majority classes (5-9), only {ce_majority_nonzero}/5 have non-zero accuracy"


def test_no_extra_keys():
    """Test that there are no unexpected extra keys in the JSON structure"""
    data = load_results()

    # Top-level keys
    expected_top_keys = {'focal_loss_model', 'crossentropy_model', 'comparison'}
    actual_top_keys = set(data.keys())
    extra_keys = actual_top_keys - expected_top_keys

    assert len(extra_keys) == 0, f"Unexpected extra top-level keys: {extra_keys}"

    # Model keys
    expected_model_keys = {'test_accuracy', 'per_class_accuracy', 'final_loss', 'epochs_trained'}

    focal_keys = set(data['focal_loss_model'].keys())
    extra_focal = focal_keys - expected_model_keys
    assert len(extra_focal) == 0, f"Unexpected extra keys in focal_loss_model: {extra_focal}"

    ce_keys = set(data['crossentropy_model'].keys())
    extra_ce = ce_keys - expected_model_keys
    assert len(extra_ce) == 0, f"Unexpected extra keys in crossentropy_model: {extra_ce}"

    # Comparison keys
    expected_comparison_keys = {'accuracy_improvement', 'better_model'}
    comparison_keys = set(data['comparison'].keys())
    extra_comparison = comparison_keys - expected_comparison_keys
    assert len(extra_comparison) == 0, f"Unexpected extra keys in comparison: {extra_comparison}"
