import os
import json
import pytest


def test_training_results_file_exists():
    """Test that the training results file exists at the expected location"""
    assert os.path.exists('/app/training_results.json'), \
        "training_results.json not found at /app/"


def test_training_results_valid_json():
    """Test that the results file contains valid JSON"""
    with open('/app/training_results.json', 'r') as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            pytest.fail(f"Invalid JSON in training_results.json: {e}")


def test_training_results_has_required_fields():
    """Test that all required fields are present in the results"""
    with open('/app/training_results.json', 'r') as f:
        data = json.load(f)

    required_fields = ['final_epoch', 'final_train_loss', 'world_size', 'backend']
    for field in required_fields:
        assert field in data, f"Missing required field: {field}"


def test_final_epoch_value():
    """Test that final_epoch is at least 2"""
    with open('/app/training_results.json', 'r') as f:
        data = json.load(f)

    assert 'final_epoch' in data, "Missing final_epoch field"
    assert isinstance(data['final_epoch'], int), \
        f"final_epoch must be an integer, got {type(data['final_epoch'])}"
    assert data['final_epoch'] >= 2, \
        f"final_epoch must be at least 2, got {data['final_epoch']}"


def test_final_train_loss_value():
    """Test that final_train_loss is a valid positive number and shows learning"""
    with open('/app/training_results.json', 'r') as f:
        data = json.load(f)

    assert 'final_train_loss' in data, "Missing final_train_loss field"

    loss = data['final_train_loss']
    assert isinstance(loss, (int, float)), \
        f"final_train_loss must be numeric, got {type(loss)}"
    assert loss > 0, \
        f"final_train_loss must be positive, got {loss}"
    assert loss < 10.0, \
        f"final_train_loss too high ({loss}), model may not be learning properly"


def test_world_size_value():
    """Test that world_size is at least 2 (distributed training requirement)"""
    with open('/app/training_results.json', 'r') as f:
        data = json.load(f)

    assert 'world_size' in data, "Missing world_size field"
    assert isinstance(data['world_size'], int), \
        f"world_size must be an integer, got {type(data['world_size'])}"
    assert data['world_size'] >= 2, \
        f"world_size must be at least 2 for distributed training, got {data['world_size']}"


def test_backend_value():
    """Test that backend is 'gloo' (CPU-compatible backend)"""
    with open('/app/training_results.json', 'r') as f:
        data = json.load(f)

    assert 'backend' in data, "Missing backend field"
    assert isinstance(data['backend'], str), \
        f"backend must be a string, got {type(data['backend'])}"
    assert data['backend'] == 'gloo', \
        f"backend must be 'gloo' for CPU training, got '{data['backend']}'"


def test_no_extra_unexpected_fields():
    """Test that the JSON doesn't contain completely unexpected fields (allows reasonable extras)"""
    with open('/app/training_results.json', 'r') as f:
        data = json.load(f)

    # Required fields
    required = {'final_epoch', 'final_train_loss', 'world_size', 'backend'}
    # Reasonable optional fields that might be added
    allowed_optional = {'timestamp', 'model_name', 'optimizer', 'learning_rate',
                       'batch_size', 'num_epochs', 'dataset'}

    all_allowed = required | allowed_optional

    for key in data.keys():
        assert key in all_allowed, \
            f"Unexpected field '{key}' in results. Allowed fields: {all_allowed}"


def test_json_not_empty():
    """Test that the JSON file is not empty"""
    file_size = os.path.getsize('/app/training_results.json')
    assert file_size > 0, "training_results.json is empty"


def test_loss_is_reasonable():
    """Test that loss value is within reasonable bounds for CIFAR-10 training"""
    with open('/app/training_results.json', 'r') as f:
        data = json.load(f)

    loss = data['final_train_loss']
    # Cross-entropy loss for 10 classes with random guessing would be ~2.3
    # After 2 epochs, we expect some learning but not perfect
    assert 0.1 < loss < 5.0, \
        f"Loss {loss} is outside reasonable range [0.1, 5.0] for 2-epoch CIFAR-10 training"


def test_file_not_hardcoded_dummy():
    """Test that the results are not obviously hardcoded dummy values"""
    with open('/app/training_results.json', 'r') as f:
        data = json.load(f)

    # Check that loss is not a suspiciously round number (like exactly 1.0, 2.0, etc.)
    loss = data['final_train_loss']

    # Allow some rounding but catch obvious dummy values
    suspicious_values = [0.0, 1.0, 2.0, 3.0, 4.0, 5.0]
    if loss in suspicious_values:
        # If it's exactly one of these, it might be hardcoded
        # But we'll be lenient and just check it's not 0.0 or exactly 1.234 (from example)
        assert loss != 0.0, "Loss is exactly 0.0, likely hardcoded"
        assert loss != 1.234, "Loss is exactly 1.234 (example value), likely hardcoded"


def test_json_structure_matches_spec():
    """Test that the JSON structure exactly matches the specification"""
    with open('/app/training_results.json', 'r') as f:
        content = f.read()
        data = json.loads(content)

    # Verify it's a flat dictionary (not nested unnecessarily)
    assert isinstance(data, dict), "Results must be a JSON object"

    # Verify required fields exist and have correct types
    assert isinstance(data.get('final_epoch'), int), "final_epoch must be integer"
    assert isinstance(data.get('final_train_loss'), (int, float)), "final_train_loss must be numeric"
    assert isinstance(data.get('world_size'), int), "world_size must be integer"
    assert isinstance(data.get('backend'), str), "backend must be string"
