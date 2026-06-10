## MNIST Digit Recognition with Hyperparameter Tuning

Build, train, and evaluate a CNN-based digit recognition model on the MNIST dataset with automated hyperparameter tuning using grid search. The final model must achieve ≥ 98% test accuracy.

### Technical Requirements

- Language: Python 3.8+
- Framework: PyTorch (CPU only), TorchVision
- Additional libraries: NumPy, Matplotlib
- All code in a single script: `/app/train.py`
- The script must be runnable via `python /app/train.py` with no additional arguments

### Data

- Use the standard MNIST dataset (download via TorchVision)
- Split: 50,000 training / 10,000 validation / 10,000 test

### Model Architecture

- CNN-based architecture using `Conv2d → ReLU → MaxPool` blocks
- Must include dropout regularization
- Must include fully connected output layers
- The architecture must be modular (defined as a PyTorch `nn.Module` subclass)

### Hyperparameter Tuning

Perform grid search over the following hyperparameter space:

| Hyperparameter | Values          |
|----------------|-----------------|
| Learning rate  | 0.1, 0.01, 0.001 |
| Batch size     | 64, 128         |
| Dropout rate   | 0.2, 0.5        |

Select the combination that yields the highest validation accuracy.

### Output Requirements

1. **Saved model**: `/app/best_model.pth` — the trained model state dict for the best hyperparameter combination.

2. **Results JSON**: `/app/results.json` — a JSON file with the following structure:
   ```json
   {
     "best_hyperparameters": {
       "learning_rate": <float>,
       "batch_size": <int>,
       "dropout_rate": <float>
     },
     "test_accuracy": <float between 0 and 1>,
     "training_time_seconds": <float>,
     "confusion_matrix": [[<int>, ...], ...],
     "per_class_metrics": {
       "0": {"precision": <float>, "recall": <float>, "f1": <float>},
       "1": {"precision": <float>, "recall": <float>, "f1": <float>},
       ...
       "9": {"precision": <float>, "recall": <float>, "f1": <float>}
     }
   }
   ```
   - `test_accuracy` must be ≥ 0.98
   - `training_time_seconds` must be ≤ 300 (5 minutes CPU budget)
   - `confusion_matrix` must be a 10×10 list of lists of integers
   - `per_class_metrics` must contain entries for digits "0" through "9", each with precision, recall, and f1 as floats between 0 and 1

3. **Training curves plot**: `/app/training_curves.png` — a single image containing two subplots:
   - Training/validation loss over epochs
   - Training/validation accuracy over epochs

### Constraints

- Total training time for the best model (not including grid search) must not exceed 5 minutes on CPU.
- After training and evaluation, delete downloaded MNIST data files and any intermediate checkpoint files. Only `/app/best_model.pth`, `/app/results.json`, `/app/training_curves.png`, and `/app/train.py` should remain in `/app/`.
