Build and train a hybrid CNN-MLP classifier for MNIST digit classification that achieves at least 99.2% test accuracy using CPU-only training.

## Technical Requirements

**Language:** Python 3.8+

**Required Dependencies:** PyTorch, torchvision, tqdm

**Output File:** `/app/results.json`

## Task Description

Implement a complete training pipeline that downloads MNIST data, trains a hybrid CNN-MLP model, and outputs the final test accuracy. The model must combine convolutional feature extraction with multi-layer perceptron classification.

## Model Architecture Requirements

- Minimum 3 convolutional layers for feature extraction
- Global pooling layer after convolutions
- 2 hidden layers in the MLP classifier head
- Use ReLU activations and appropriate regularization

## Training Specifications

- Device: CPU only (no CUDA)
- Batch size: 64
- Epochs: 20
- Optimizer: Adam
- Track both training and validation accuracy per epoch
- Save model checkpoint with highest validation accuracy

## Output Format

Write results to `/app/results.json` with the following structure:

```json
{
  "test_accuracy": 99.25,
  "best_val_accuracy": 99.30,
  "final_epoch": 20,
  "model_path": "/app/best_model.pth"
}
```

**Required fields:**
- `test_accuracy`: Final accuracy on MNIST test set (float, percentage)
- `best_val_accuracy`: Highest validation accuracy achieved during training (float, percentage)
- `final_epoch`: Total number of epochs completed (integer)
- `model_path`: Path to saved best model checkpoint (string)

## Success Criteria

The `test_accuracy` value in `/app/results.json` must be ≥ 99.2
