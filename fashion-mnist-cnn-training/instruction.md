## Fashion-MNIST Image Classification with Custom CNN

Build and train a custom CNN from scratch using TensorFlow/Keras to classify Fashion-MNIST images. All work must be CPU-only. Write a single Python script `/app/train.py` that performs all steps below and produces the required output artifacts.

### Technical Requirements

- Language: Python 3.x
- Framework: TensorFlow / Keras
- Device: CPU only (do not require or use GPU)
- Random seed: 42 (for reproducibility)
- Working directory: `/app/`

### Dataset

- Use the Fashion-MNIST dataset (load via `tensorflow.keras.datasets.fashion_mnist`).
- Normalize pixel values to [0, 1] (float32).
- Split into train/validation/test sets of sizes 55,000 / 5,000 / 10,000 using random seed 42. The original training set (60,000) is split into train (55k) and validation (5k); the original test set (10,000) is used as-is.

### Model Architecture

The CNN must contain:
- At least 3 convolutional blocks, where each block includes a Conv2D layer followed by BatchNormalization, ReLU activation, and MaxPooling2D.
- A GlobalAveragePooling2D layer after the convolutional blocks.
- One or more Dense layers leading to a 10-class softmax output.

### Training Configuration

- Optimizer: Adam
- Loss: categorical cross-entropy
- Metrics: accuracy
- Epochs: 10
- Batch size: 128
- Data augmentation applied to training data: random rotation up to 20°, width shift range 0.1, height shift range 0.1.

### Callbacks

- TensorBoard logging to `/app/logs/`
- ModelCheckpoint saving the best model (by validation accuracy) to `/app/best_model.h5`

### Output Artifacts

All output files must be created under `/app/`:

| File | Description |
|---|---|
| `/app/fashion_mnist_cnn.h5` | Final trained model in HDF5 format |
| `/app/saved_model/` | Final trained model in TensorFlow SavedModel format |
| `/app/best_model.h5` | Best model checkpoint (by val accuracy) |
| `/app/training_curves.png` | Plot with 2 subplots: training/validation accuracy and training/validation loss over epochs |
| `/app/logs/` | TensorBoard log directory |
| `/app/output.json` | Evaluation results (see schema below) |

### output.json Schema

```json
{
  "test_accuracy": <float, e.g. 0.8723>,
  "test_loss": <float>,
  "per_class": {
    "T-shirt/top": {"precision": <float>, "recall": <float>, "f1": <float>},
    "Trouser": {"precision": <float>, "recall": <float>, "f1": <float>},
    "Pullover": {"precision": <float>, "recall": <float>, "f1": <float>},
    "Dress": {"precision": <float>, "recall": <float>, "f1": <float>},
    "Coat": {"precision": <float>, "recall": <float>, "f1": <float>},
    "Sandal": {"precision": <float>, "recall": <float>, "f1": <float>},
    "Shirt": {"precision": <float>, "recall": <float>, "f1": <float>},
    "Sneaker": {"precision": <float>, "recall": <float>, "f1": <float>},
    "Bag": {"precision": <float>, "recall": <float>, "f1": <float>},
    "Ankle boot": {"precision": <float>, "recall": <float>, "f1": <float>}
  }
}
```

All float values must be rounded to 4 decimal places. The 10 class names must match exactly as listed above.

### Success Criteria

- `test_accuracy` in `/app/output.json` must be ≥ 0.85.
- All output artifacts listed above must exist.
- `training_curves.png` must contain both accuracy and loss curves.
