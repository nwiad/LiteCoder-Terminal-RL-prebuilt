## Task: CPU-based Image Classification with Vision Transformer

Implement a Vision Transformer (ViT) from scratch to classify CIFAR-10 images and achieve ≥85% test accuracy using only CPU resources.

## Technical Requirements

- **Language**: Python 3.x
- **Framework**: PyTorch (CPU-only)
- **Dataset**: CIFAR-10 (automatically downloaded)
- **Model**: Vision Transformer implemented from scratch
- **Target Accuracy**: ≥85% on CIFAR-10 test set
- **Hardware Constraint**: CPU-only execution (no CUDA)

## Implementation Requirements

1. **Vision Transformer Architecture**:
   - Patch embedding layer to convert images into sequences
   - Multi-head self-attention mechanism
   - MLP (feedforward) blocks
   - Layer normalization
   - Classification head

2. **Data Pipeline**:
   - Load CIFAR-10 dataset (10 classes, 32x32 RGB images)
   - Apply data augmentation for training (random crops, flips, etc.)
   - Normalize images appropriately
   - Create train/test dataloaders

3. **Training Configuration**:
   - Implement training loop with proper loss computation
   - Use appropriate optimizer (e.g., AdamW)
   - Implement learning rate scheduling
   - Add model checkpointing to save best model
   - Track training/validation metrics

4. **Output Requirements**:
   - Save final trained model to `/app/model.pth`
   - Generate accuracy report in `/app/results.json` with format:
     ```json
     {
       "test_accuracy": 0.85,
       "train_accuracy": 0.92,
       "total_epochs": 50,
       "final_loss": 0.35
     }
     ```
   - Ensure `test_accuracy` field contains the final test set accuracy as a float

## Constraints

- All training must run on CPU (set `device = 'cpu'`)
- Model must be trained from scratch (no pretrained weights)
- Must achieve ≥85% test accuracy
- Code must be reproducible (set random seeds)
