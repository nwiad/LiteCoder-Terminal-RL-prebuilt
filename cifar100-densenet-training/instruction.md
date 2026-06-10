## High-Accuracy CIFAR-100 Classification with DenseNet-BC

Build a complete, reproducible training pipeline in Python 3 that trains a DenseNet-BC model on CIFAR-100, performs hyperparameter search, and exports the best model as TorchScript.

### Technical Requirements

- Language: Python 3.x
- Libraries: PyTorch, torchvision, TensorBoard, scikit-learn
- Entry point: `python /app/train.py` — running this single script must execute the full pipeline (data loading → training → hyperparameter search → best model selection → export → summary generation).
- Random seed: set to `42` for reproducibility across all random sources (Python, NumPy, PyTorch).
- All output artifacts must be written under `/app/output/`.

### Model Architecture

Implement a DenseNet-BC (Bottleneck + Compression) with:
- Growth rate: 40
- Compression factor (θ): 0.5
- Number of dense blocks: 3
- Number of output classes: 100 (CIFAR-100)
- Configurable dropout rate (used during hyperparameter search)

### Data Pipeline

- Dataset: CIFAR-100 (download automatically via torchvision if not present)
- Split the standard training set into training (90%) and validation (10%) subsets. Use the standard test set as-is.
- Apply data augmentation on the training subset (at minimum: random horizontal flip, random crop with padding).
- Normalize using CIFAR-100 channel-wise mean and standard deviation.
- Use deterministic data loaders (seeded workers).

### Training

- Support mixed-precision training on CPU (FP32 / BF16) using PyTorch AMP.
- Implement early stopping with a patience of at least 5 epochs based on validation accuracy.
- Log training loss, validation loss, and validation accuracy per epoch to TensorBoard under `/app/output/tb_logs/`. Each hyperparameter search run must have its own subdirectory.

### Hyperparameter Search

Perform a search (grid or random) over at least these three hyperparameters:
- Learning rate (at least 3 distinct values)
- Weight decay (at least 2 distinct values)
- Dropout rate (at least 2 distinct values)

Each combination constitutes a separate run. The best run is the one with the highest validation accuracy.

### Best Run Selection and Export

1. Identify the run with the highest validation accuracy.
2. Copy its checkpoint, configuration, and metrics into `/app/output/best_run/`.
3. Export the best model as TorchScript to `/app/output/best_run/model.pt`.
4. The exported TorchScript model must accept input tensors of shape `(N, 3, 32, 32)` and produce output of shape `(N, 100)`.

### Summary Output

Generate `/app/output/summary.json` with the following structure:

```json
{
  "best_hyperparams": {
    "learning_rate": <float>,
    "weight_decay": <float>,
    "dropout": <float>
  },
  "best_val_accuracy": <float between 0 and 100>,
  "test_accuracy": <float between 0 and 100>,
  "total_params": <int>,
  "model_file_size_mb": <float>,
  "num_runs": <int>
}
```

- `best_val_accuracy` and `test_accuracy` are percentages (0–100).
- `total_params` is the total number of trainable parameters in the model.
- `model_file_size_mb` is the size of `/app/output/best_run/model.pt` in megabytes.
- `num_runs` is the total number of hyperparameter search runs executed.
- `num_runs` must be ≥ 12 (at least 3 LR × 2 WD × 2 dropout).

### Accuracy Target

The best run must achieve a validation accuracy (`best_val_accuracy`) of at least **65%** on CIFAR-100.

### Output File Structure

```
/app/output/
├── tb_logs/            # TensorBoard log directories (one per run)
├── best_run/
│   ├── model.pt        # TorchScript exported model
│   ├── checkpoint.pth  # PyTorch checkpoint (state_dict + config + metrics)
│   └── config.json     # Hyperparameters of the best run
└── summary.json        # Summary report
```
