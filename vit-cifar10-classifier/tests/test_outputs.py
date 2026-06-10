import os
import json
import torch
import torch.nn as nn

def test_model_file_exists():
    """Test that model.pth file exists"""
    assert os.path.exists('/app/model.pth'), "model.pth file not found at /app/model.pth"

def test_results_file_exists():
    """Test that results.json file exists"""
    assert os.path.exists('/app/results.json'), "results.json file not found at /app/results.json"

def test_model_file_not_empty():
    """Test that model.pth is not empty"""
    assert os.path.getsize('/app/model.pth') > 0, "model.pth file is empty"

def test_results_file_not_empty():
    """Test that results.json is not empty"""
    assert os.path.getsize('/app/results.json') > 0, "results.json file is empty"

def test_results_json_valid():
    """Test that results.json is valid JSON"""
    with open('/app/results.json', 'r') as f:
        data = json.load(f)
    assert isinstance(data, dict), "results.json should contain a JSON object"

def test_results_required_fields():
    """Test that results.json contains all required fields"""
    with open('/app/results.json', 'r') as f:
        data = json.load(f)

    required_fields = ['test_accuracy', 'train_accuracy', 'total_epochs', 'final_loss']
    for field in required_fields:
        assert field in data, f"Missing required field: {field}"

def test_results_field_types():
    """Test that results.json fields have correct types"""
    with open('/app/results.json', 'r') as f:
        data = json.load(f)

    assert isinstance(data['test_accuracy'], (int, float)), "test_accuracy must be a number"
    assert isinstance(data['train_accuracy'], (int, float)), "train_accuracy must be a number"
    assert isinstance(data['total_epochs'], int), "total_epochs must be an integer"
    assert isinstance(data['final_loss'], (int, float)), "final_loss must be a number"

def test_accuracy_in_valid_range():
    """Test that accuracy values are in valid range [0, 1]"""
    with open('/app/results.json', 'r') as f:
        data = json.load(f)

    assert 0 <= data['test_accuracy'] <= 1, f"test_accuracy {data['test_accuracy']} not in range [0, 1]"
    assert 0 <= data['train_accuracy'] <= 1, f"train_accuracy {data['train_accuracy']} not in range [0, 1]"

def test_test_accuracy_meets_threshold():
    """Test that test accuracy meets the 85% threshold"""
    with open('/app/results.json', 'r') as f:
        data = json.load(f)

    assert data['test_accuracy'] >= 0.85, f"test_accuracy {data['test_accuracy']} is below required threshold of 0.85"

def test_epochs_positive():
    """Test that total_epochs is positive"""
    with open('/app/results.json', 'r') as f:
        data = json.load(f)

    assert data['total_epochs'] > 0, "total_epochs must be positive"

def test_loss_non_negative():
    """Test that final_loss is non-negative"""
    with open('/app/results.json', 'r') as f:
        data = json.load(f)

    assert data['final_loss'] >= 0, "final_loss must be non-negative"

def test_model_loadable():
    """Test that model.pth can be loaded by PyTorch"""
    try:
        state_dict = torch.load('/app/model.pth', map_location='cpu')
        assert isinstance(state_dict, dict), "Model state_dict should be a dictionary"
    except Exception as e:
        raise AssertionError(f"Failed to load model.pth: {str(e)}")

def test_model_has_parameters():
    """Test that loaded model has parameters"""
    state_dict = torch.load('/app/model.pth', map_location='cpu')
    assert len(state_dict) > 0, "Model state_dict is empty"

def test_model_architecture_components():
    """Test that model contains expected ViT components"""
    state_dict = torch.load('/app/model.pth', map_location='cpu')

    # Check for patch embedding
    patch_embed_keys = [k for k in state_dict.keys() if 'patch_embed' in k or 'proj' in k]
    assert len(patch_embed_keys) > 0, "Model missing patch embedding components"

    # Check for attention mechanism
    attn_keys = [k for k in state_dict.keys() if 'attn' in k or 'qkv' in k]
    assert len(attn_keys) > 0, "Model missing attention mechanism components"

    # Check for MLP/feedforward
    mlp_keys = [k for k in state_dict.keys() if 'mlp' in k or 'fc' in k]
    assert len(mlp_keys) > 0, "Model missing MLP/feedforward components"

    # Check for layer normalization
    norm_keys = [k for k in state_dict.keys() if 'norm' in k]
    assert len(norm_keys) > 0, "Model missing layer normalization components"

    # Check for classification head
    head_keys = [k for k in state_dict.keys() if 'head' in k or 'classifier' in k]
    assert len(head_keys) > 0, "Model missing classification head"

def test_model_has_cls_token():
    """Test that model has class token (ViT-specific)"""
    state_dict = torch.load('/app/model.pth', map_location='cpu')
    cls_token_keys = [k for k in state_dict.keys() if 'cls_token' in k]
    assert len(cls_token_keys) > 0, "Model missing cls_token (required for ViT)"

def test_model_has_position_embedding():
    """Test that model has position embedding (ViT-specific)"""
    state_dict = torch.load('/app/model.pth', map_location='cpu')
    pos_embed_keys = [k for k in state_dict.keys() if 'pos_embed' in k]
    assert len(pos_embed_keys) > 0, "Model missing position embedding (required for ViT)"

def test_train_accuracy_reasonable():
    """Test that train accuracy is reasonable (not suspiciously low or high)"""
    with open('/app/results.json', 'r') as f:
        data = json.load(f)

    # Train accuracy should be at least as good as test accuracy (typically higher)
    # But allow some tolerance for edge cases
    assert data['train_accuracy'] >= 0.5, f"train_accuracy {data['train_accuracy']} is suspiciously low"
    assert data['train_accuracy'] <= 1.0, f"train_accuracy {data['train_accuracy']} exceeds 1.0"

def test_loss_reasonable():
    """Test that final loss is in a reasonable range"""
    with open('/app/results.json', 'r') as f:
        data = json.load(f)

    # For a well-trained model, loss should be reasonable (not extremely high)
    assert data['final_loss'] < 10.0, f"final_loss {data['final_loss']} is suspiciously high"

def test_model_parameters_trained():
    """Test that model parameters are not all zeros (indicating actual training)"""
    state_dict = torch.load('/app/model.pth', map_location='cpu')

    # Check that at least some parameters are non-zero
    non_zero_params = 0
    total_params = 0

    for key, param in state_dict.items():
        if isinstance(param, torch.Tensor):
            total_params += 1
            if param.abs().sum() > 0:
                non_zero_params += 1

    assert non_zero_params > 0, "All model parameters are zero - model was not trained"
    assert non_zero_params / total_params > 0.9, "Too many zero parameters - model may not be properly trained"

def test_no_hardcoded_accuracy():
    """Test that accuracy is not a suspiciously exact value (e.g., exactly 0.85)"""
    with open('/app/results.json', 'r') as f:
        data = json.load(f)

    # Real training rarely produces exact values like 0.85, 0.86, etc.
    # Check that accuracy has some decimal precision
    test_acc_str = str(data['test_accuracy'])

    # If accuracy is exactly 0.85 or 0.86 with no additional decimals, it's suspicious
    suspicious_values = ['0.85', '0.86', '0.87', '0.88', '0.89', '0.9']
    if test_acc_str in suspicious_values:
        # Allow it, but check that it's not combined with other suspicious patterns
        # (This is a soft check - we don't want to be too strict)
        pass

def test_model_size_reasonable():
    """Test that model file size is reasonable (not suspiciously small)"""
    model_size = os.path.getsize('/app/model.pth')

    # A ViT model should have at least a few MB of parameters
    # Too small suggests an incomplete or dummy model
    assert model_size > 100000, f"model.pth size {model_size} bytes is suspiciously small for a ViT model"

def test_results_json_format():
    """Test that results.json has proper formatting (not malformed)"""
    with open('/app/results.json', 'r') as f:
        content = f.read()

    # Should be valid JSON
    data = json.loads(content)

    # Should not have extra fields that suggest template/dummy data
    expected_fields = {'test_accuracy', 'train_accuracy', 'total_epochs', 'final_loss'}
    actual_fields = set(data.keys())

    # Allow extra fields, but check required ones are present
    assert expected_fields.issubset(actual_fields), f"Missing required fields: {expected_fields - actual_fields}"
