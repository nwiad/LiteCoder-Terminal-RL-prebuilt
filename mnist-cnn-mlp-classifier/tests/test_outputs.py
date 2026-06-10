import os
import json
import pytest


def test_results_json_exists():
    """Test that results.json file exists"""
    assert os.path.exists('/app/results.json'), "results.json file not found at /app/results.json"


def test_results_json_valid():
    """Test that results.json is valid JSON"""
    try:
        with open('/app/results.json', 'r') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        pytest.fail(f"results.json is not valid JSON: {e}")
    except Exception as e:
        pytest.fail(f"Error reading results.json: {e}")


def test_results_json_structure():
    """Test that results.json contains all required fields"""
    with open('/app/results.json', 'r') as f:
        data = json.load(f)

    required_fields = ['test_accuracy', 'best_val_accuracy', 'final_epoch', 'model_path']

    for field in required_fields:
        assert field in data, f"Missing required field: {field}"


def test_test_accuracy_type():
    """Test that test_accuracy is a number"""
    with open('/app/results.json', 'r') as f:
        data = json.load(f)

    assert isinstance(data['test_accuracy'], (int, float)), \
        f"test_accuracy must be a number, got {type(data['test_accuracy'])}"


def test_test_accuracy_threshold():
    """Test that test_accuracy meets the minimum threshold of 99.2%"""
    with open('/app/results.json', 'r') as f:
        data = json.load(f)

    test_acc = data['test_accuracy']
    assert test_acc >= 99.2, \
        f"test_accuracy {test_acc}% is below the required threshold of 99.2%"


def test_test_accuracy_range():
    """Test that test_accuracy is within valid range (0-100)"""
    with open('/app/results.json', 'r') as f:
        data = json.load(f)

    test_acc = data['test_accuracy']
    assert 0 <= test_acc <= 100, \
        f"test_accuracy {test_acc}% is outside valid range [0, 100]"


def test_best_val_accuracy_type():
    """Test that best_val_accuracy is a number"""
    with open('/app/results.json', 'r') as f:
        data = json.load(f)

    assert isinstance(data['best_val_accuracy'], (int, float)), \
        f"best_val_accuracy must be a number, got {type(data['best_val_accuracy'])}"


def test_best_val_accuracy_range():
    """Test that best_val_accuracy is within valid range (0-100)"""
    with open('/app/results.json', 'r') as f:
        data = json.load(f)

    val_acc = data['best_val_accuracy']
    assert 0 <= val_acc <= 100, \
        f"best_val_accuracy {val_acc}% is outside valid range [0, 100]"


def test_final_epoch_type():
    """Test that final_epoch is an integer"""
    with open('/app/results.json', 'r') as f:
        data = json.load(f)

    assert isinstance(data['final_epoch'], int), \
        f"final_epoch must be an integer, got {type(data['final_epoch'])}"


def test_final_epoch_value():
    """Test that final_epoch is 20 as specified"""
    with open('/app/results.json', 'r') as f:
        data = json.load(f)

    assert data['final_epoch'] == 20, \
        f"final_epoch must be 20 as specified in requirements, got {data['final_epoch']}"


def test_model_path_type():
    """Test that model_path is a string"""
    with open('/app/results.json', 'r') as f:
        data = json.load(f)

    assert isinstance(data['model_path'], str), \
        f"model_path must be a string, got {type(data['model_path'])}"


def test_model_path_not_empty():
    """Test that model_path is not empty"""
    with open('/app/results.json', 'r') as f:
        data = json.load(f)

    assert len(data['model_path'].strip()) > 0, \
        "model_path cannot be empty"


def test_model_checkpoint_exists():
    """Test that the model checkpoint file exists"""
    with open('/app/results.json', 'r') as f:
        data = json.load(f)

    model_path = data['model_path']
    assert os.path.exists(model_path), \
        f"Model checkpoint file not found at {model_path}"


def test_model_checkpoint_not_empty():
    """Test that the model checkpoint file is not empty"""
    with open('/app/results.json', 'r') as f:
        data = json.load(f)

    model_path = data['model_path']
    file_size = os.path.getsize(model_path)
    assert file_size > 0, \
        f"Model checkpoint file at {model_path} is empty"


def test_model_checkpoint_reasonable_size():
    """Test that the model checkpoint has a reasonable size (at least 100KB)"""
    with open('/app/results.json', 'r') as f:
        data = json.load(f)

    model_path = data['model_path']
    file_size = os.path.getsize(model_path)
    min_size = 100 * 1024  # 100KB
    assert file_size >= min_size, \
        f"Model checkpoint at {model_path} is suspiciously small ({file_size} bytes). Expected at least {min_size} bytes."


def test_no_extra_fields():
    """Test that results.json doesn't have unexpected extra fields (optional check)"""
    with open('/app/results.json', 'r') as f:
        data = json.load(f)

    expected_fields = {'test_accuracy', 'best_val_accuracy', 'final_epoch', 'model_path'}
    actual_fields = set(data.keys())

    # This is a soft check - extra fields are allowed but we warn about them
    extra_fields = actual_fields - expected_fields
    if extra_fields:
        print(f"Warning: Found extra fields in results.json: {extra_fields}")


def test_accuracy_consistency():
    """Test that test_accuracy and best_val_accuracy are reasonably close"""
    with open('/app/results.json', 'r') as f:
        data = json.load(f)

    test_acc = data['test_accuracy']
    val_acc = data['best_val_accuracy']

    # They should be within 5% of each other (reasonable for well-trained models)
    diff = abs(test_acc - val_acc)
    assert diff <= 5.0, \
        f"test_accuracy ({test_acc}%) and best_val_accuracy ({val_acc}%) differ by {diff}%, which seems unreasonable"
