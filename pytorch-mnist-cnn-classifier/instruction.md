## PyTorch CPU Image Classifier with Early Stopping & Confusion Matrix

Build a single self-contained Python script (`/app/mnist_cnn.py`) that trains a PyTorch CNN on MNIST with early stopping and produces a confusion matrix plot.

### Technical Requirements

- Language: Python 3.x
- Libraries: PyTorch (CPU-only), torchvision, matplotlib, seaborn, scikit-learn
- All code must be in a single script: `/app/mnist_cnn.py`
- CPU-only execution (no CUDA/GPU usage)

### Data

- Use the MNIST dataset via `torchvision.datasets.MNIST`, downloading automatically to `/app/data/` if not present.
- Split the original 60,000 training samples into a training set (50,000) and a validation set (10,000). Use the last 10,000 samples of the training set as the validation set.
- Use the standard 10,000-sample MNIST test set for final evaluation.

### Model

- Implement a convolutional neural network with at least two convolutional layers followed by at least one fully connected layer.
- The model must accept 1×28×28 grayscale images and output logits for 10 classes (digits 0–9).

### Training with Early Stopping

- Use cross-entropy loss and an Adam optimizer.
- Train for a maximum of 50 epochs.
- Implement early stopping based on validation loss with a patience of 5 epochs (stop if validation loss does not improve for 5 consecutive epochs).
- After early stopping triggers (or max epochs reached), save the best model weights (the weights from the epoch with the lowest validation loss) to `/app/mnist_cnn_best.pth`.

### Evaluation & Outputs

After training, load the best model from `/app/mnist_cnn_best.pth` and evaluate on the test set. The script must produce the following output files:

1. `/app/mnist_cnn_best.pth` — PyTorch model state dict of the best model.

2. `/app/confusion_matrix.png` — A confusion matrix heatmap plot generated using seaborn's `heatmap`. Requirements:
   - Axes labeled with digit classes 0–9.
   - X-axis label: `Predicted`.
   - Y-axis label: `Actual`.
   - Cell values (counts) displayed as integer annotations in the heatmap.

3. `/app/results.json` — A JSON file with the following structure:
   ```json
   {
     "test_accuracy": 0.98,
     "best_epoch": 7,
     "total_epochs_run": 12,
     "early_stopping_triggered": true,
     "confusion_matrix": [[980, 0, 1, ...], ...]
   }
   ```
   - `test_accuracy`: float, accuracy on the 10,000 test samples (correct predictions / total), rounded to 4 decimal places.
   - `best_epoch`: int (1-indexed), the epoch that achieved the lowest validation loss.
   - `total_epochs_run`: int, total number of epochs actually executed before stopping.
   - `early_stopping_triggered`: boolean, `true` if training stopped before reaching 50 epochs.
   - `confusion_matrix`: a 10×10 list of lists (row = actual, column = predicted) with integer counts.

### Performance

- The trained model must achieve a test accuracy of at least 0.95 (95%).
