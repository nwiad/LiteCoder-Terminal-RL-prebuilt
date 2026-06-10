import os
import json
import subprocess
import torch
import torch.nn as nn
from PIL import Image
import numpy as np


def test_model_file_exists():
    """Test that model.pth exists and is not empty"""
    assert os.path.exists('/app/model.pth'), "model.pth does not exist"
    assert os.path.getsize('/app/model.pth') > 1000, "model.pth is too small or empty"


def test_model_loadable():
    """Test that model.pth can be loaded as a PyTorch state_dict"""
    try:
        state_dict = torch.load('/app/model.pth', map_location='cpu')
        assert isinstance(state_dict, dict), "model.pth does not contain a valid state_dict"
        assert len(state_dict) > 0, "state_dict is empty"

        # Check that it contains typical CNN layer parameters
        has_conv = any('conv' in key.lower() for key in state_dict.keys())
        has_fc = any('fc' in key.lower() or 'linear' in key.lower() for key in state_dict.keys())
        assert has_conv, "Model does not contain convolutional layers"
        assert has_fc, "Model does not contain fully connected layers"
    except Exception as e:
        raise AssertionError(f"Failed to load model.pth: {e}")


def test_metrics_file_exists():
    """Test that metrics.json exists and is valid JSON"""
    assert os.path.exists('/app/metrics.json'), "metrics.json does not exist"

    with open('/app/metrics.json', 'r') as f:
        try:
            metrics = json.load(f)
        except json.JSONDecodeError as e:
            raise AssertionError(f"metrics.json is not valid JSON: {e}")

    assert isinstance(metrics, dict), "metrics.json does not contain a dictionary"


def test_metrics_required_fields():
    """Test that metrics.json contains all required fields with correct types"""
    with open('/app/metrics.json', 'r') as f:
        metrics = json.load(f)

    required_fields = ['test_accuracy', 'parameter_count', 'architecture', 'training_epochs']
    for field in required_fields:
        assert field in metrics, f"metrics.json missing required field: {field}"

    # Type checks
    assert isinstance(metrics['test_accuracy'], (float, int)), "test_accuracy must be numeric"
    assert isinstance(metrics['parameter_count'], int), "parameter_count must be an integer"
    assert isinstance(metrics['architecture'], str), "architecture must be a string"
    assert isinstance(metrics['training_epochs'], int), "training_epochs must be an integer"


def test_metrics_accuracy_threshold():
    """Test that test_accuracy is greater than 75%"""
    with open('/app/metrics.json', 'r') as f:
        metrics = json.load(f)

    accuracy = metrics['test_accuracy']
    assert 0.0 <= accuracy <= 1.0, f"test_accuracy {accuracy} is out of valid range [0, 1]"
    assert accuracy > 0.75, f"test_accuracy {accuracy} does not meet the >75% requirement"


def test_metrics_parameter_constraint():
    """Test that parameter_count is less than 500K"""
    with open('/app/metrics.json', 'r') as f:
        metrics = json.load(f)

    param_count = metrics['parameter_count']
    assert param_count > 0, "parameter_count must be positive"
    assert param_count < 500000, f"parameter_count {param_count} exceeds 500K limit"


def test_metrics_architecture_not_empty():
    """Test that architecture field is not empty"""
    with open('/app/metrics.json', 'r') as f:
        metrics = json.load(f)

    architecture = metrics['architecture']
    assert len(architecture.strip()) > 0, "architecture field is empty"


def test_metrics_training_epochs_reasonable():
    """Test that training_epochs is a reasonable positive number"""
    with open('/app/metrics.json', 'r') as f:
        metrics = json.load(f)

    epochs = metrics['training_epochs']
    assert epochs > 0, "training_epochs must be positive"
    assert epochs <= 200, f"training_epochs {epochs} seems unreasonably high"


def test_visualizations_directory_exists():
    """Test that visualizations directory exists"""
    assert os.path.exists('/app/visualizations'), "visualizations directory does not exist"
    assert os.path.isdir('/app/visualizations'), "visualizations is not a directory"


def test_visualizations_not_empty():
    """Test that visualizations directory contains PNG files"""
    vis_files = [f for f in os.listdir('/app/visualizations') if f.endswith('.png')]
    assert len(vis_files) > 0, "visualizations directory contains no PNG files"


def test_visualizations_naming_convention():
    """Test that visualization files follow the naming convention"""
    vis_files = [f for f in os.listdir('/app/visualizations') if f.endswith('.png')]

    for filename in vis_files:
        # Expected format: image_{id}_layer_{layer_name}.png
        assert filename.startswith('image_'), f"File {filename} does not start with 'image_'"
        assert '_layer_' in filename, f"File {filename} does not contain '_layer_'"
        assert filename.endswith('.png'), f"File {filename} does not end with '.png'"


def test_visualizations_for_all_test_images():
    """Test that visualizations exist for all images in test_images.json"""
    with open('/app/test_images.json', 'r') as f:
        test_spec = json.load(f)

    vis_files = os.listdir('/app/visualizations')

    for img_spec in test_spec['images']:
        img_id = img_spec['id']
        # Check that at least one visualization exists for this image
        matching_files = [f for f in vis_files if f.startswith(f'image_{img_id}_layer_')]
        assert len(matching_files) > 0, f"No visualizations found for image ID {img_id}"


def test_visualizations_multiple_layers():
    """Test that visualizations exist for multiple convolutional layers"""
    vis_files = [f for f in os.listdir('/app/visualizations') if f.endswith('.png')]

    # Extract unique layer names
    layer_names = set()
    for filename in vis_files:
        # Parse: image_{id}_layer_{layer_name}.png
        parts = filename.replace('.png', '').split('_layer_')
        if len(parts) == 2:
            layer_names.add(parts[1])

    # Should have at least 2 convolutional layers (as per requirements)
    assert len(layer_names) >= 2, f"Only {len(layer_names)} layer(s) visualized, need at least 2"


def test_visualization_images_valid():
    """Test that visualization PNG files are valid and not empty"""
    vis_files = [f for f in os.listdir('/app/visualizations') if f.endswith('.png')]

    for filename in vis_files[:5]:  # Test first 5 to avoid excessive testing
        filepath = os.path.join('/app/visualizations', filename)

        # Check file size
        assert os.path.getsize(filepath) > 1000, f"{filename} is too small to be a valid image"

        # Try to open with PIL
        try:
            img = Image.open(filepath)
            img.verify()  # Verify it's a valid image

            # Re-open to check dimensions (verify() closes the file)
            img = Image.open(filepath)
            width, height = img.size
            assert width > 0 and height > 0, f"{filename} has invalid dimensions"
        except Exception as e:
            raise AssertionError(f"Failed to open/verify {filename}: {e}")


def test_inference_script_exists():
    """Test that inference.py exists"""
    assert os.path.exists('/app/inference.py'), "inference.py does not exist"
    assert os.path.getsize('/app/inference.py') > 100, "inference.py is too small or empty"


def test_inference_script_executable():
    """Test that inference.py is a valid Python script"""
    with open('/app/inference.py', 'r') as f:
        content = f.read()

    # Check for essential components
    assert 'import torch' in content, "inference.py does not import torch"
    assert 'load_state_dict' in content or 'torch.load' in content, "inference.py does not load model"
    assert '/app/model.pth' in content, "inference.py does not reference /app/model.pth"


def test_inference_script_runs():
    """Test that inference.py can be executed and produces output"""
    # Create a simple test image (32x32 RGB)
    test_img = Image.new('RGB', (32, 32), color='red')
    test_img_path = '/tmp/test_image.png'
    test_img.save(test_img_path)

    try:
        result = subprocess.run(
            ['python3', '/app/inference.py', test_img_path],
            capture_output=True,
            text=True,
            timeout=30
        )

        assert result.returncode == 0, f"inference.py failed with error: {result.stderr}"

        output = result.stdout.strip()
        assert len(output) > 0, "inference.py produced no output"

        # Check output format: "Predicted: {class_name}, Confidence: {probability:.4f}"
        assert 'Predicted:' in output, "Output does not contain 'Predicted:'"
        assert 'Confidence:' in output, "Output does not contain 'Confidence:'"

    except subprocess.TimeoutExpired:
        raise AssertionError("inference.py timed out after 30 seconds")
    except Exception as e:
        raise AssertionError(f"Failed to run inference.py: {e}")


def test_inference_output_format():
    """Test that inference.py output follows the specified format"""
    test_img = Image.new('RGB', (32, 32), color='blue')
    test_img_path = '/tmp/test_image2.png'
    test_img.save(test_img_path)

    result = subprocess.run(
        ['python3', '/app/inference.py', test_img_path],
        capture_output=True,
        text=True,
        timeout=30
    )

    output = result.stdout.strip()

    # Parse output
    parts = output.split(', ')
    assert len(parts) == 2, f"Output format incorrect: {output}"

    # Check predicted class
    pred_part = parts[0]
    assert pred_part.startswith('Predicted: '), f"First part should start with 'Predicted: '"
    class_name = pred_part.replace('Predicted: ', '').strip()
    assert len(class_name) > 0, "Class name is empty"

    # Check confidence score
    conf_part = parts[1]
    assert conf_part.startswith('Confidence: '), f"Second part should start with 'Confidence: '"
    conf_str = conf_part.replace('Confidence: ', '').strip()

    try:
        confidence = float(conf_str)
        assert 0.0 <= confidence <= 1.0, f"Confidence {confidence} is out of range [0, 1]"
    except ValueError:
        raise AssertionError(f"Confidence value '{conf_str}' is not a valid float")


def test_model_parameter_count_matches_metrics():
    """Test that actual model parameter count matches metrics.json"""
    # Load metrics
    with open('/app/metrics.json', 'r') as f:
        metrics = json.load(f)

    reported_params = metrics['parameter_count']

    # Load model state dict and count parameters
    state_dict = torch.load('/app/model.pth', map_location='cpu')

    actual_params = sum(p.numel() for p in state_dict.values())

    # Allow small discrepancy (some implementations may count differently)
    discrepancy = abs(actual_params - reported_params)
    tolerance = max(1000, reported_params * 0.01)  # 1% or 1000 params

    assert discrepancy <= tolerance, \
        f"Parameter count mismatch: metrics.json reports {reported_params}, " \
        f"but state_dict has {actual_params} parameters"


def test_no_hardcoded_dummy_outputs():
    """Test that outputs are not hardcoded dummy values"""
    # Test 1: Run inference on two different images, should get different results
    test_img1 = Image.new('RGB', (32, 32), color='red')
    test_img2 = Image.new('RGB', (32, 32), color='blue')

    test_img1.save('/tmp/red.png')
    test_img2.save('/tmp/blue.png')

    result1 = subprocess.run(
        ['python3', '/app/inference.py', '/tmp/red.png'],
        capture_output=True,
        text=True,
        timeout=30
    )

    result2 = subprocess.run(
        ['python3', '/app/inference.py', '/tmp/blue.png'],
        capture_output=True,
        text=True,
        timeout=30
    )

    # While outputs might be the same class, confidence should vary
    # This is a weak test but catches completely hardcoded outputs
    output1 = result1.stdout.strip()
    output2 = result2.stdout.strip()

    # Extract confidence values
    conf1 = float(output1.split('Confidence: ')[1])
    conf2 = float(output2.split('Confidence: ')[1])

    # At least one should not be exactly 1.0 or 0.0 (too perfect)
    assert not (conf1 == 1.0 and conf2 == 1.0), "Suspiciously perfect confidence scores"


def test_visualizations_contain_actual_data():
    """Test that visualization images contain actual feature map data, not blank images"""
    vis_files = [f for f in os.listdir('/app/visualizations') if f.endswith('.png')]

    for filename in vis_files[:3]:  # Test first 3
        filepath = os.path.join('/app/visualizations', filename)

        img = Image.open(filepath)
        img_array = np.array(img)

        # Check that image is not completely uniform (blank)
        if len(img_array.shape) == 3:
            # RGB image
            std_dev = np.std(img_array)
        else:
            # Grayscale
            std_dev = np.std(img_array)

        assert std_dev > 1.0, f"{filename} appears to be a blank or uniform image (std={std_dev})"


def test_test_images_json_exists():
    """Test that test_images.json exists and is valid"""
    assert os.path.exists('/app/test_images.json'), "test_images.json does not exist"

    with open('/app/test_images.json', 'r') as f:
        test_spec = json.load(f)

    assert 'images' in test_spec, "test_images.json missing 'images' key"
    assert isinstance(test_spec['images'], list), "'images' must be a list"
    assert len(test_spec['images']) > 0, "'images' list is empty"

    for img_spec in test_spec['images']:
        assert 'id' in img_spec, "Image spec missing 'id' field"
        assert 'index' in img_spec, "Image spec missing 'index' field"
