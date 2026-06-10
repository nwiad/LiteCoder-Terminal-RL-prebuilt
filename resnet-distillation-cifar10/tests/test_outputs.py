import os
import json
import torch
import pytest


def test_model_file_exists():
    """Test that the student model file exists"""
    model_path = "/app/resnet18_cifar10_distilled.pt"
    assert os.path.exists(model_path), f"Model file not found at {model_path}"


def test_model_file_not_empty():
    """Test that the model file is not empty"""
    model_path = "/app/resnet18_cifar10_distilled.pt"
    assert os.path.getsize(model_path) > 0, "Model file is empty"


def test_model_file_size_constraint():
    """Test that the student model file size is less than 35 MB"""
    model_path = "/app/resnet18_cifar10_distilled.pt"
    size_mb = os.path.getsize(model_path) / (1024 * 1024)
    assert size_mb < 35, f"Model file size {size_mb:.2f} MB exceeds 35 MB limit"


def test_model_is_valid_pytorch_checkpoint():
    """Test that the model file is a valid PyTorch checkpoint"""
    model_path = "/app/resnet18_cifar10_distilled.pt"
    try:
        state_dict = torch.load(model_path, map_location='cpu', weights_only=True)
        assert isinstance(state_dict, dict), "Model checkpoint is not a state_dict"
        assert len(state_dict) > 0, "Model state_dict is empty"
    except Exception as e:
        pytest.fail(f"Failed to load model checkpoint: {e}")


def test_model_has_resnet18_architecture():
    """Test that the model has ResNet18 architecture (approximate parameter count)"""
    model_path = "/app/resnet18_cifar10_distilled.pt"
    state_dict = torch.load(model_path, map_location='cpu', weights_only=True)

    # Count total parameters
    total_params = sum(p.numel() for p in state_dict.values())

    # ResNet18 for CIFAR-10 should have approximately 11M parameters
    # Allow range: 10M to 12M to account for slight variations
    assert 10_000_000 <= total_params <= 12_000_000, \
        f"Model has {total_params:,} parameters, expected ~11M for ResNet18"


def test_model_has_correct_output_layer():
    """Test that the model has correct output layer for CIFAR-10 (10 classes)"""
    model_path = "/app/resnet18_cifar10_distilled.pt"
    state_dict = torch.load(model_path, map_location='cpu', weights_only=True)

    # Check for final fully connected layer with 10 outputs
    fc_weight_key = None
    for key in state_dict.keys():
        if 'fc.weight' in key or key.endswith('.weight'):
            fc_weight_key = key

    assert fc_weight_key is not None, "Could not find final FC layer in model"

    fc_weight = state_dict[fc_weight_key]
    assert fc_weight.shape[0] == 10, \
        f"Final layer has {fc_weight.shape[0]} outputs, expected 10 for CIFAR-10"


def test_metrics_file_exists():
    """Test that the metrics.json file exists"""
    metrics_path = "/app/metrics.json"
    assert os.path.exists(metrics_path), f"Metrics file not found at {metrics_path}"


def test_metrics_file_not_empty():
    """Test that the metrics file is not empty"""
    metrics_path = "/app/metrics.json"
    assert os.path.getsize(metrics_path) > 0, "Metrics file is empty"


def test_metrics_file_valid_json():
    """Test that the metrics file is valid JSON"""
    metrics_path = "/app/metrics.json"
    try:
        with open(metrics_path, 'r') as f:
            metrics = json.load(f)
        assert isinstance(metrics, dict), "Metrics is not a JSON object"
    except json.JSONDecodeError as e:
        pytest.fail(f"Metrics file is not valid JSON: {e}")


def test_metrics_has_all_required_fields():
    """Test that metrics.json contains all required fields"""
    metrics_path = "/app/metrics.json"
    with open(metrics_path, 'r') as f:
        metrics = json.load(f)

    required_fields = [
        "teacher_accuracy",
        "student_accuracy",
        "teacher_params",
        "student_params",
        "teacher_size_mb",
        "student_size_mb",
        "training_time_seconds",
        "epochs_trained"
    ]

    for field in required_fields:
        assert field in metrics, f"Missing required field: {field}"


def test_metrics_field_types():
    """Test that metrics fields have correct data types"""
    metrics_path = "/app/metrics.json"
    with open(metrics_path, 'r') as f:
        metrics = json.load(f)

    # Float fields
    float_fields = [
        "teacher_accuracy",
        "student_accuracy",
        "teacher_size_mb",
        "student_size_mb",
        "training_time_seconds"
    ]
    for field in float_fields:
        assert isinstance(metrics[field], (int, float)), \
            f"{field} should be numeric, got {type(metrics[field])}"

    # Integer fields
    int_fields = ["teacher_params", "student_params", "epochs_trained"]
    for field in int_fields:
        assert isinstance(metrics[field], int), \
            f"{field} should be integer, got {type(metrics[field])}"


def test_student_accuracy_meets_requirement():
    """Test that student accuracy is >= 85%"""
    metrics_path = "/app/metrics.json"
    with open(metrics_path, 'r') as f:
        metrics = json.load(f)

    student_acc = metrics["student_accuracy"]
    assert student_acc >= 85.0, \
        f"Student accuracy {student_acc:.2f}% is below required 85%"


def test_student_accuracy_reasonable_range():
    """Test that student accuracy is in a reasonable range (0-100%)"""
    metrics_path = "/app/metrics.json"
    with open(metrics_path, 'r') as f:
        metrics = json.load(f)

    student_acc = metrics["student_accuracy"]
    assert 0 <= student_acc <= 100, \
        f"Student accuracy {student_acc:.2f}% is outside valid range [0, 100]"


def test_teacher_accuracy_reasonable():
    """Test that teacher accuracy is reasonable (should be > student or close)"""
    metrics_path = "/app/metrics.json"
    with open(metrics_path, 'r') as f:
        metrics = json.load(f)

    teacher_acc = metrics["teacher_accuracy"]
    student_acc = metrics["student_accuracy"]

    # Teacher should be at least 70% (reasonable for CIFAR-10)
    assert teacher_acc >= 70.0, \
        f"Teacher accuracy {teacher_acc:.2f}% seems too low"

    # Teacher should not be worse than student by more than 10%
    assert teacher_acc >= student_acc - 10.0, \
        f"Teacher accuracy {teacher_acc:.2f}% is suspiciously lower than student {student_acc:.2f}%"


def test_parameter_counts_reasonable():
    """Test that parameter counts are reasonable for ResNet models"""
    metrics_path = "/app/metrics.json"
    with open(metrics_path, 'r') as f:
        metrics = json.load(f)

    teacher_params = metrics["teacher_params"]
    student_params = metrics["student_params"]

    # ResNet34 should have ~21M parameters
    assert 20_000_000 <= teacher_params <= 23_000_000, \
        f"Teacher params {teacher_params:,} outside expected range for ResNet34"

    # ResNet18 should have ~11M parameters
    assert 10_000_000 <= student_params <= 12_000_000, \
        f"Student params {student_params:,} outside expected range for ResNet18"

    # Student should have fewer parameters than teacher
    assert student_params < teacher_params, \
        f"Student params {student_params:,} should be less than teacher {teacher_params:,}"


def test_model_sizes_reasonable():
    """Test that model file sizes are reasonable"""
    metrics_path = "/app/metrics.json"
    with open(metrics_path, 'r') as f:
        metrics = json.load(f)

    teacher_size = metrics["teacher_size_mb"]
    student_size = metrics["student_size_mb"]

    # Teacher should be larger than student
    assert teacher_size > student_size, \
        f"Teacher size {teacher_size:.2f} MB should be larger than student {student_size:.2f} MB"

    # Student size should meet constraint
    assert student_size < 35, \
        f"Student size {student_size:.2f} MB exceeds 35 MB limit"

    # Sizes should be positive
    assert teacher_size > 0 and student_size > 0, \
        "Model sizes must be positive"


def test_training_time_reasonable():
    """Test that training time is reasonable (positive and not suspiciously low)"""
    metrics_path = "/app/metrics.json"
    with open(metrics_path, 'r') as f:
        metrics = json.load(f)

    training_time = metrics["training_time_seconds"]

    # Training time should be positive
    assert training_time > 0, "Training time must be positive"

    # Training should take at least 10 seconds (sanity check - not instant)
    assert training_time >= 10, \
        f"Training time {training_time:.2f}s seems suspiciously low"


def test_epochs_trained_reasonable():
    """Test that epochs trained is reasonable"""
    metrics_path = "/app/metrics.json"
    with open(metrics_path, 'r') as f:
        metrics = json.load(f)

    epochs = metrics["epochs_trained"]

    # Should be between 1 and MAX_EPOCHS (100)
    assert 1 <= epochs <= 100, \
        f"Epochs trained {epochs} outside valid range [1, 100]"


def test_model_weights_not_all_zeros():
    """Test that model weights are not all zeros (indicating actual training)"""
    model_path = "/app/resnet18_cifar10_distilled.pt"
    state_dict = torch.load(model_path, map_location='cpu', weights_only=True)

    # Check that at least some weights are non-zero
    total_nonzero = 0
    total_params = 0

    for param in state_dict.values():
        if isinstance(param, torch.Tensor):
            total_nonzero += torch.count_nonzero(param).item()
            total_params += param.numel()

    # At least 50% of parameters should be non-zero
    nonzero_ratio = total_nonzero / total_params if total_params > 0 else 0
    assert nonzero_ratio > 0.5, \
        f"Only {nonzero_ratio*100:.2f}% of weights are non-zero, model may not be trained"


def test_model_weights_not_all_same():
    """Test that model weights are not all the same value (indicating actual training)"""
    model_path = "/app/resnet18_cifar10_distilled.pt"
    state_dict = torch.load(model_path, map_location='cpu', weights_only=True)

    # Check variance in weights
    for key, param in state_dict.items():
        if isinstance(param, torch.Tensor) and param.numel() > 1:
            # Check that there's variance in the weights
            variance = torch.var(param.float()).item()
            assert variance > 1e-10, \
                f"Layer {key} has suspiciously low variance {variance}, weights may be constant"


def test_metrics_consistency_with_actual_model_size():
    """Test that the reported student size matches the actual file size"""
    metrics_path = "/app/metrics.json"
    model_path = "/app/resnet18_cifar10_distilled.pt"

    with open(metrics_path, 'r') as f:
        metrics = json.load(f)

    reported_size = metrics["student_size_mb"]
    actual_size = os.path.getsize(model_path) / (1024 * 1024)

    # Allow 1% tolerance for rounding
    assert abs(reported_size - actual_size) / actual_size < 0.01, \
        f"Reported size {reported_size:.2f} MB doesn't match actual size {actual_size:.2f} MB"


def test_no_cuda_in_model():
    """Test that the model doesn't have CUDA-specific artifacts"""
    model_path = "/app/resnet18_cifar10_distilled.pt"

    # Load model and check it can be loaded on CPU
    try:
        state_dict = torch.load(model_path, map_location='cpu', weights_only=True)

        # Verify all tensors are on CPU
        for key, param in state_dict.items():
            if isinstance(param, torch.Tensor):
                assert param.device.type == 'cpu', \
                    f"Parameter {key} is on {param.device}, expected CPU"
    except Exception as e:
        pytest.fail(f"Model cannot be loaded on CPU: {e}")
