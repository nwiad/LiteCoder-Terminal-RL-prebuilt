## Task: Image Classification with Custom CNN

Build and train a custom Convolutional Neural Network (CNN) from scratch on the CIFAR-10 dataset using PyTorch. The implementation must use only low-level PyTorch operations without torchvision.models or pre-trained models.

### Technical Requirements

- Python 3.x with PyTorch (CPU build)
- No transfer learning or torchvision.models
- Custom CNN architecture with at least 3 convolutional layers
- CIFAR-10 dataset (10 classes, 32x32 RGB images)

### Implementation Requirements

1. **Data Processing**: Download CIFAR-10 and create custom Dataset/DataLoader with normalization (zero-mean, unit-variance)

2. **Model Architecture**: Define a CNN using nn.Module with:
   - At least 3 convolutional layers
   - ReLU activations
   - MaxPooling layers
   - BatchNorm layers
   - Fully connected classifier head

3. **Training**: Implement training loop that tracks metrics per epoch (train/validation loss and accuracy)

4. **Evaluation**: Compute test accuracy and generate confusion matrix on test set

5. **Visualization**: Generate plots for training curves and confusion matrix

### Output Files

All outputs must be saved to `/app/` directory:

**`/app/metrics.json`** - Training and evaluation metrics in JSON format:
```json
{
  "train_loss": [epoch1_loss, epoch2_loss, ...],
  "train_accuracy": [epoch1_acc, epoch2_acc, ...],
  "val_loss": [epoch1_loss, epoch2_loss, ...],
  "val_accuracy": [epoch1_acc, epoch2_acc, ...],
  "test_accuracy": 0.XX,
  "total_parameters": XXXXX,
  "confusion_matrix": [[c00, c01, ...], [c10, c11, ...], ...]
}
```

- `train_loss`, `train_accuracy`, `val_loss`, `val_accuracy`: Arrays of numeric values (one per epoch)
- `test_accuracy`: Float between 0 and 1
- `total_parameters`: Integer count of model parameters
- `confusion_matrix`: 10x10 array of integers (CIFAR-10 has 10 classes)

**`/app/training_curves.png`** - Visualization showing:
- Training and validation loss over epochs
- Training and validation accuracy over epochs

**`/app/confusion_matrix.png`** - Heatmap visualization of the 10x10 confusion matrix with class labels

**`/app/model_weights.pth`** - Saved PyTorch model state dictionary

### Success Criteria

- All 4 output files must exist at specified paths
- `metrics.json` must be valid JSON matching the schema above
- Test accuracy should be > 0.4 (40%) to demonstrate basic learning
- Confusion matrix must be 10x10 with integer values
- PNG files must be valid image files
