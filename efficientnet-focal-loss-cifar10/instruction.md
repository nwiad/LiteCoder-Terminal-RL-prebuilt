## Task: EfficientNet-B0 Image Classification with Custom Focal Loss

Implement and train an EfficientNet-B0 model on CIFAR-10 using a custom Focal Loss function, then evaluate its performance against a standard CrossEntropyLoss baseline.

**Technical Requirements:**
- Python 3.x with PyTorch
- Input: CIFAR-10 dataset (downloaded via torchvision)
- Output: `/app/results.json` containing evaluation metrics

**Implementation Requirements:**

1. **Focal Loss Implementation:**
   - Implement Focal Loss with configurable alpha and gamma parameters
   - Default parameters: alpha=0.25, gamma=2.0
   - Must handle multi-class classification (10 classes)

2. **EfficientNet-B0 Architecture:**
   - Build EfficientNet-B0 from scratch or use torchvision implementation
   - Train without pre-trained weights (random initialization)
   - Adapt final layer for 10-class output

3. **Dataset Preparation:**
   - Use CIFAR-10 dataset (50,000 training, 10,000 test images)
   - Apply artificial class imbalance: reduce samples for classes 0-4 to 20% of original count
   - Apply standard data augmentation (random crop, horizontal flip, normalization)

4. **Training Configuration:**
   - Train two models: one with Focal Loss, one with CrossEntropyLoss
   - Minimum 10 epochs for each model
   - Use validation split (10% of training data)
   - Implement early stopping (patience=5 epochs)
   - Optimizer: Adam or SGD with learning rate scheduling

5. **Output Format (`/app/results.json`):**
```json
{
  "focal_loss_model": {
    "test_accuracy": 0.0,
    "per_class_accuracy": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    "final_loss": 0.0,
    "epochs_trained": 0
  },
  "crossentropy_model": {
    "test_accuracy": 0.0,
    "per_class_accuracy": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    "final_loss": 0.0,
    "epochs_trained": 0
  },
  "comparison": {
    "accuracy_improvement": 0.0,
    "better_model": "focal_loss|crossentropy"
  }
}
```

**Evaluation Metrics:**
- Overall test accuracy (percentage)
- Per-class accuracy for all 10 CIFAR-10 classes
- Final validation loss
- Number of epochs trained before early stopping

**Edge Cases:**
- Handle class imbalance correctly in loss calculation
- Ensure per-class accuracy is computed for all classes including minority classes
- Validate that both models complete training successfully
