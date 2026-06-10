## Task: MNIST Neural Network with Auto-Generated Training Report

Build, train, and evaluate a neural network on the MNIST dataset, then generate a self-contained HTML report with training visualizations and results.

### Technical Requirements

- **Language**: Python 3.x
- **Required Libraries**: tensorflow (or tensorflow-cpu), matplotlib, seaborn, scikit-learn, jinja2
- **Dataset**: MNIST handwritten digits (via tensorflow.keras.datasets.mnist)
- **Output File**: `/app/mnist_report.html`

### Model Specifications

Build a sequential CNN with the following architecture:
- Convolutional and pooling layers
- Dense layers with dropout for regularization
- Train for exactly 5 epochs with a validation split
- Use categorical crossentropy loss and an appropriate optimizer

### Output Requirements

Generate a single self-contained HTML file (`/app/mnist_report.html`) that includes:

1. **Training Metrics**:
   - Final test accuracy (as percentage)
   - Training and validation loss curves (line plot)
   - Training and validation accuracy curves (line plot)

2. **Confusion Matrix**:
   - 10x10 heatmap showing predicted vs actual labels for all test samples
   - Include axis labels for digits 0-9

3. **Sample Predictions**:
   - Grid of 16 random test images (4x4 layout)
   - Each image shows: the digit image, predicted label, and actual label
   - Clearly indicate correct vs incorrect predictions

4. **Technical Details**:
   - All plots must be embedded as base64-encoded images (no external files)
   - HTML must be viewable in standard browsers without requiring a server
   - Include model architecture summary and training parameters

### Data Format

- Input images: 28x28 grayscale pixels, normalized to [0, 1]
- Labels: integers 0-9 representing digit classes
- Use standard MNIST train/test split (60,000 training, 10,000 test samples)

### Validation

The HTML file must:
- Be a valid, self-contained HTML5 document
- Open successfully in a web browser
- Display all required visualizations and metrics
- Contain no broken image links or external dependencies
