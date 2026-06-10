Build and evaluate a CNN-based image classification pipeline for Fashion-MNIST that produces a trained model, training history visualization, and confusion matrix evaluation.

## Technical Requirements

- Python 3.x with TensorFlow (CPU) and matplotlib
- All operations must be CPU-only (no GPU dependencies)
- Use Keras API for model building and Fashion-MNIST data loading

## Input Specifications

- Dataset: Fashion-MNIST (load via `tensorflow.keras.datasets.fashion_mnist`)
- Save downloaded data as numpy arrays to `/app/fashion_mnist_data.npz`
- Image format: 28×28 grayscale images
- 10 classes: T-shirt/top, Trouser, Pullover, Dress, Coat, Sandal, Shirt, Sneaker, Bag, Ankle boot

## Model Architecture Requirements

- 2 convolutional blocks, each containing:
  - Conv2D layer
  - Pooling layer (MaxPooling2D or AveragePooling2D)
- 1 or more Dense layers for classification
- Output layer: 10 units (one per class)
- Optimizer: Adam
- Loss function: sparse_categorical_crossentropy
- Training: exactly 5 epochs

## Output Requirements

1. **Trained Model**: `/app/fashion_mnist_cnn.h5`
   - Keras model file in HDF5 format
   - Must be loadable via `tensorflow.keras.models.load_model()`

2. **Training History Plot**: `/app/history.png`
   - Line plot showing training accuracy and loss over 5 epochs
   - Must include both metrics on the same or separate subplots
   - Saved as PNG image file

3. **Confusion Matrix**: `/app/cm.png`
   - Confusion matrix computed on test set predictions
   - Visualized as a heatmap or grid
   - Saved as PNG image file

4. **Final Deliverable**: `/app/deliverables.tar.gz`
   - Tarball containing: `fashion_mnist_cnn.h5`, `history.png`, `cm.png`
   - Must be extractable with standard tar utilities

## Evaluation Criteria

- Model must complete training without errors
- Test set accuracy must be printed to stdout
- All three output files must exist and be valid before creating tarball
- Tarball must contain exactly the three required files
