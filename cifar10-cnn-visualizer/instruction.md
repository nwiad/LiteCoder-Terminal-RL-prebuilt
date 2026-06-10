## Task: CPU-Optimized Image Classifier with Feature Visualization

Build a lightweight CNN for CIFAR-10 classification that achieves >75% test accuracy and implements feature map visualization for convolutional layers.

### Technical Requirements

- **Language**: Python 3.x
- **Framework**: PyTorch (CPU-only)
- **Dataset**: CIFAR-10 (use torchvision.datasets.CIFAR10)
- **Model Constraint**: <500K parameters
- **Accuracy Target**: >75% on CIFAR-10 test set

### Input/Output Specifications

**Input:**
- `/app/test_images.json` - JSON file containing test image specifications:
  ```json
  {
    "images": [
      {"id": 0, "source": "cifar10_test", "index": 0},
      {"id": 1, "source": "cifar10_test", "index": 100}
    ]
  }
  ```

**Output Files:**

1. `/app/model.pth` - Trained PyTorch model (state_dict)

2. `/app/metrics.json` - Training and evaluation metrics:
   ```json
   {
     "test_accuracy": 0.7623,
     "parameter_count": 487320,
     "architecture": "CustomCNN",
     "training_epochs": 50
   }
   ```

3. `/app/visualizations/` - Directory containing feature map visualizations:
   - `image_{id}_layer_{layer_name}.png` - Feature maps for each convolutional layer
   - Each visualization should show multiple feature maps from the specified layer

4. `/app/inference.py` - Inference script that:
   - Loads the trained model from `/app/model.pth`
   - Accepts an image path as command-line argument
   - Outputs predicted class label and confidence score

### Implementation Requirements

**Model Architecture:**
- Convolutional neural network with <500K parameters
- At least 2 convolutional layers for feature visualization
- Suitable for CPU inference (avoid computationally expensive operations)

**Training:**
- Train on CIFAR-10 training set (50,000 images)
- Validate and report final accuracy on CIFAR-10 test set (10,000 images)
- Must achieve >75% test accuracy

**Feature Visualization:**
- Extract and visualize feature maps from convolutional layers
- Process images specified in `/app/test_images.json`
- Save visualizations as PNG files in `/app/visualizations/`
- Visualizations should clearly show learned features

**Inference Script:**
- Must load model from `/app/model.pth`
- Accept image path via command line: `python /app/inference.py <image_path>`
- Output format: `Predicted: {class_name}, Confidence: {probability:.4f}`

### Data Format Specifications

**metrics.json fields:**
- `test_accuracy`: Float (0-1 range)
- `parameter_count`: Integer (must be <500000)
- `architecture`: String (model class name)
- `training_epochs`: Integer

**Visualization naming:**
- Format: `image_{id}_layer_{layer_name}.png`
- `{id}`: Matches the "id" field from test_images.json
- `{layer_name}`: Descriptive name of the convolutional layer (e.g., "conv1", "conv2")

### Edge Cases

- Handle CIFAR-10 dataset download automatically if not present
- Ensure model trains successfully even with limited CPU resources
- Feature visualizations should handle variable numbers of feature maps per layer
