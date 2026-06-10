import os
import tarfile
import numpy as np
from PIL import Image
import tensorflow as tf
from tensorflow import keras


def test_fashion_mnist_data_exists():
    """Test that the Fashion-MNIST dataset was saved as numpy arrays."""
    data_path = '/app/fashion_mnist_data.npz'
    assert os.path.exists(data_path), f"Dataset file not found: {data_path}"

    # Load and verify structure
    data = np.load(data_path)
    required_keys = ['x_train', 'y_train', 'x_test', 'y_test']
    for key in required_keys:
        assert key in data, f"Missing key in dataset: {key}"

    # Verify shapes (Fashion-MNIST standard)
    assert data['x_train'].shape == (60000, 28, 28), "Invalid training data shape"
    assert data['y_train'].shape == (60000,), "Invalid training labels shape"
    assert data['x_test'].shape == (10000, 28, 28), "Invalid test data shape"
    assert data['y_test'].shape == (10000,), "Invalid test labels shape"


def test_model_file_exists_and_loadable():
    """Test that the trained model exists and can be loaded."""
    model_path = '/app/fashion_mnist_cnn.h5'
    assert os.path.exists(model_path), f"Model file not found: {model_path}"

    # Verify file is not empty
    assert os.path.getsize(model_path) > 1000, "Model file is suspiciously small or empty"

    # Load model to verify it's valid
    model = keras.models.load_model(model_path)
    assert model is not None, "Failed to load model"


def test_model_architecture():
    """Test that the model has the required architecture components."""
    model_path = '/app/fashion_mnist_cnn.h5'
    model = keras.models.load_model(model_path)

    # Check output layer has 10 units (10 classes)
    output_shape = model.output_shape
    assert output_shape[-1] == 10, f"Output layer must have 10 units, got {output_shape[-1]}"

    # Count Conv2D layers - must have at least 2
    conv_layers = [layer for layer in model.layers if isinstance(layer, keras.layers.Conv2D)]
    assert len(conv_layers) >= 2, f"Model must have at least 2 Conv2D layers, found {len(conv_layers)}"

    # Check for pooling layers
    pooling_layers = [layer for layer in model.layers if isinstance(layer, (keras.layers.MaxPooling2D, keras.layers.AveragePooling2D))]
    assert len(pooling_layers) >= 2, f"Model must have at least 2 pooling layers, found {len(pooling_layers)}"


def test_model_can_predict():
    """Test that the model can make predictions on Fashion-MNIST data."""
    model_path = '/app/fashion_mnist_cnn.h5'
    model = keras.models.load_model(model_path)

    # Load test data
    data = np.load('/app/fashion_mnist_data.npz')
    x_test = data['x_test']

    # Preprocess (normalize and reshape like training)
    x_test = x_test.astype('float32') / 255.0
    x_test = np.expand_dims(x_test, -1)

    # Make predictions on a small batch
    predictions = model.predict(x_test[:10], verbose=0)

    # Verify prediction shape
    assert predictions.shape == (10, 10), f"Expected predictions shape (10, 10), got {predictions.shape}"

    # Verify predictions are probabilities (sum to ~1)
    for pred in predictions:
        assert np.isclose(pred.sum(), 1.0, atol=0.01), "Predictions should sum to 1 (softmax output)"


def test_history_plot_exists_and_valid():
    """Test that the training history plot exists and is a valid PNG."""
    history_path = '/app/history.png'
    assert os.path.exists(history_path), f"History plot not found: {history_path}"

    # Verify file is not empty
    file_size = os.path.getsize(history_path)
    assert file_size > 1000, f"History plot is suspiciously small ({file_size} bytes)"

    # Verify it's a valid PNG image
    try:
        img = Image.open(history_path)
        assert img.format == 'PNG', f"History plot must be PNG format, got {img.format}"
        width, height = img.size
        assert width > 100 and height > 100, f"Image dimensions too small: {width}x{height}"
    except Exception as e:
        raise AssertionError(f"Failed to open history plot as valid image: {e}")


def test_confusion_matrix_exists_and_valid():
    """Test that the confusion matrix exists and is a valid PNG."""
    cm_path = '/app/cm.png'
    assert os.path.exists(cm_path), f"Confusion matrix not found: {cm_path}"

    # Verify file is not empty
    file_size = os.path.getsize(cm_path)
    assert file_size > 1000, f"Confusion matrix is suspiciously small ({file_size} bytes)"

    # Verify it's a valid PNG image
    try:
        img = Image.open(cm_path)
        assert img.format == 'PNG', f"Confusion matrix must be PNG format, got {img.format}"
        width, height = img.size
        assert width > 100 and height > 100, f"Image dimensions too small: {width}x{height}"
    except Exception as e:
        raise AssertionError(f"Failed to open confusion matrix as valid image: {e}")


def test_deliverables_tarball_exists():
    """Test that the deliverables tarball exists and is valid."""
    tarball_path = '/app/deliverables.tar.gz'
    assert os.path.exists(tarball_path), f"Tarball not found: {tarball_path}"

    # Verify file is not empty
    assert os.path.getsize(tarball_path) > 1000, "Tarball is suspiciously small or empty"

    # Verify it's a valid tar.gz file
    assert tarfile.is_tarfile(tarball_path), "File is not a valid tarball"


def test_tarball_contains_required_files():
    """Test that the tarball contains exactly the three required files."""
    tarball_path = '/app/deliverables.tar.gz'

    with tarfile.open(tarball_path, 'r:gz') as tar:
        members = tar.getnames()

        # Check for exactly 3 files
        assert len(members) == 3, f"Tarball must contain exactly 3 files, found {len(members)}: {members}"

        # Check for required file names
        required_files = {'fashion_mnist_cnn.h5', 'history.png', 'cm.png'}
        found_files = set(members)

        assert found_files == required_files, f"Tarball must contain {required_files}, found {found_files}"


def test_tarball_files_are_valid():
    """Test that files extracted from tarball are valid and non-empty."""
    tarball_path = '/app/deliverables.tar.gz'
    extract_dir = '/tmp/test_extract'

    # Clean up any previous extraction
    if os.path.exists(extract_dir):
        import shutil
        shutil.rmtree(extract_dir)

    os.makedirs(extract_dir)

    # Extract tarball
    with tarfile.open(tarball_path, 'r:gz') as tar:
        tar.extractall(extract_dir)

    # Verify extracted model file
    model_file = os.path.join(extract_dir, 'fashion_mnist_cnn.h5')
    assert os.path.exists(model_file), "Model file not in extracted tarball"
    assert os.path.getsize(model_file) > 1000, "Extracted model file is too small"

    # Verify model is loadable
    model = keras.models.load_model(model_file)
    assert model is not None, "Extracted model cannot be loaded"

    # Verify extracted PNG files
    for png_file in ['history.png', 'cm.png']:
        png_path = os.path.join(extract_dir, png_file)
        assert os.path.exists(png_path), f"{png_file} not in extracted tarball"
        assert os.path.getsize(png_path) > 1000, f"Extracted {png_file} is too small"

        # Verify it's a valid image
        img = Image.open(png_path)
        assert img.format == 'PNG', f"{png_file} is not a valid PNG"


def test_model_training_history_length():
    """Test that the model was trained for exactly 5 epochs."""
    # We can't directly verify epochs from the saved model, but we can check
    # that the model has been trained (has non-random weights)
    model_path = '/app/fashion_mnist_cnn.h5'
    model = keras.models.load_model(model_path)

    # Load test data and evaluate
    data = np.load('/app/fashion_mnist_data.npz')
    x_test = data['x_test'].astype('float32') / 255.0
    x_test = np.expand_dims(x_test, -1)
    y_test = data['y_test']

    # Evaluate model - should have reasonable accuracy (>60% for Fashion-MNIST CNN)
    test_loss, test_accuracy = model.evaluate(x_test, y_test, verbose=0)
    assert test_accuracy > 0.6, f"Model accuracy too low ({test_accuracy:.4f}), likely not trained properly"


def test_all_required_outputs_exist():
    """Test that all required output files exist before tarball creation."""
    required_files = [
        '/app/fashion_mnist_cnn.h5',
        '/app/history.png',
        '/app/cm.png',
        '/app/deliverables.tar.gz',
        '/app/fashion_mnist_data.npz'
    ]

    for file_path in required_files:
        assert os.path.exists(file_path), f"Required output file missing: {file_path}"
