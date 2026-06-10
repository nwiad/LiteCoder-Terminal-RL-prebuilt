## Handwritten Digit Recognition with CNN

Build a CNN model from scratch using PyTorch to classify handwritten digits on the MNIST dataset, achieving ≥97% test accuracy on CPU.

### Technical Requirements

- Language: Python 3.x
- Framework: PyTorch (no pretrained weights, no transfer learning)
- Device: CPU only
- Entry point: `/app/train.py` — running `python train.py` must execute the full pipeline (data loading, training, evaluation, and all output generation)

### Data

- Use the standard MNIST dataset (download via `torchvision.datasets.MNIST` or equivalent)
- Store/cache downloaded data under `/app/data/`

### Model Architecture

Implement a 4-layer CNN with the following sequential structure:
1. Conv2d → ReLU → MaxPool2d
2. Conv2d → ReLU → MaxPool2d
3. Flatten → Linear → ReLU
4. Linear (output layer, 10 classes)

### Training Configuration

- Loss: Cross-entropy
- Optimizer: SGD with momentum = 0.9
- Epochs: exactly 3
- CPU-optimised settings: `pin_memory=False`, `num_workers=0`, `torch.set_num_threads(2)`

### Output Files

All output files must be generated automatically when `train.py` is executed.

1. **Model checkpoint:** `/app/mnist_cnn.pt`
   - Saved via `torch.save(model.state_dict(), ...)` using the best test-accuracy epoch's weights

2. **Training log:** `/app/training_log.json`
   - A JSON file containing a list of per-epoch records. Example structure:
     ```json
     {
       "epochs": [
         {"epoch": 1, "train_acc": 95.12, "test_acc": 96.45},
         {"epoch": 2, "train_acc": 97.30, "test_acc": 97.80},
         {"epoch": 3, "train_acc": 98.01, "test_acc": 98.15}
       ],
       "best_test_acc": 98.15,
       "total_time_seconds": 123.4
     }
     ```
   - `train_acc` and `test_acc` are percentages (0–100)
   - `best_test_acc` must be ≥ 97.0
   - `total_time_seconds` is the wall-clock training time in seconds

3. **Prediction visualization:** `/app/preds.png`
   - An 8×8 grid image showing 64 randomly sampled test images
   - Each subplot must display the image with both the predicted label and the true label (e.g., as a title like "Pred: 3 / True: 3")

### Acceptance Criteria

- `python train.py` runs to completion without error
- `/app/mnist_cnn.pt` exists and is a valid PyTorch state dict loadable into the defined CNN architecture
- `/app/training_log.json` exists, is valid JSON matching the schema above, and `best_test_acc` ≥ 97.0
- `/app/preds.png` exists and is a valid image file
