## End-to-End CPU-Based Image Classification Pipeline with PyTorch CIFAR-10

Build a complete, reproducible image-classification pipeline that trains a compact CNN on CIFAR-10 (CPU only), tunes hyper-parameters via Optuna, evaluates with standard classification metrics, and exports the model to ONNX format.

### Technical Requirements

- **Language:** Python 3.x
- **Key libraries:** PyTorch (CPU build), torchvision, optuna, scikit-learn, onnx, onnxruntime
- **All scripts must run on CPU only (no CUDA required).**
- **Working directory:** `/app`

### Directory Structure

```
/app/
├── data/                        # CIFAR-10 dataset (auto-downloaded)
├── artifacts/                   # All outputs go here
│   ├── best_model.pth           # Best checkpoint from training
│   ├── last_model.pth           # Last checkpoint from training
│   ├── optuna.db                # Optuna SQLite study database
│   ├── classification_report.csv
│   ├── confusion_matrix.png
│   ├── model.onnx
│   └── onnx_verify.txt
├── dataset_info.txt
├── train.py
├── tune.py
├── eval.py
├── export_onnx.py
├── run_all.sh
├── requirements.txt
└── README.md
```

### Script Specifications

#### 1. `dataset_info.txt`

Located at `/app/dataset_info.txt`. Must contain at minimum:
- Number of training samples and test samples
- Number of classes (10)
- Image shape (e.g., 3x32x32)
- Per-channel mean and standard deviation of the training set

#### 2. `/app/train.py`

A training script with argparse CLI supporting at least these arguments:
- `--lr` (learning rate, float)
- `--batch_size` (int)
- `--epochs` (int)
- `--dropout` (float)
- `--weight_decay` (float)

Requirements:
- Must use a learning rate scheduler (ReduceLROnPlateau or similar).
- Must implement early stopping logic.
- Must save two checkpoints to `/app/artifacts/`: `best_model.pth` (best validation performance) and `last_model.pth` (final epoch).
- Each `.pth` file must be a valid PyTorch state dict loadable via `torch.load()`.

#### 3. `/app/tune.py`

A hyperparameter tuning script using Optuna.
- Must search over at least: `lr`, `batch_size`, `dropout`, `weight_decay`.
- Must use trial pruning for unpromising trials.
- Must store the study in a SQLite database at `/app/artifacts/optuna.db`.
- Must print the top-3 trials (by objective value) to stdout upon completion.
- The study must contain at least 3 completed trials.

#### 4. `/app/eval.py`

An evaluation script that:
- Loads the best checkpoint from `/app/artifacts/best_model.pth`.
- Runs inference on the CIFAR-10 test set.
- Writes `/app/artifacts/classification_report.csv`: a CSV file with columns that include `precision`, `recall`, `f1-score`, and `support` for each of the 10 CIFAR-10 classes. The CSV must be parseable by `pandas.read_csv()`.
- Writes `/app/artifacts/confusion_matrix.png`: a valid PNG image file.

#### 5. `/app/export_onnx.py`

An ONNX export script that:
- Loads the best checkpoint from `/app/artifacts/best_model.pth`.
- Exports the model to `/app/artifacts/model.onnx`.
- The ONNX file must be loadable by `onnx.load()` and pass `onnx.checker.check_model()`.
- Verifies the exported ONNX model using ONNX Runtime on at least 1000 random CIFAR-10 test samples.
- Writes `/app/artifacts/onnx_verify.txt` containing at minimum a line with the top-1 accuracy (as a decimal or percentage).

#### 6. `/app/run_all.sh`

A bash orchestration script that:
- Starts with `set -euo pipefail`.
- Sequentially executes: `tune.py` → `train.py` (using best hyperparameters from tuning) → `eval.py` → `export_onnx.py`.
- Must be executable (`chmod +x`).

#### 7. `/app/requirements.txt`

Must list all required Python packages with pinned versions (e.g., `torch==X.Y.Z`).

#### 8. `/app/README.md`

Must contain:
- Usage instructions for running the pipeline.
- A directory/file map describing the project structure.

### Output Format Specifications

- **`classification_report.csv`**: Valid CSV with a header row. Must contain columns for `precision`, `recall`, `f1-score`, and `support`. Must have rows for all 10 CIFAR-10 classes (airplane, automobile, bird, cat, deer, dog, frog, horse, ship, truck).
- **`confusion_matrix.png`**: A valid PNG image (verifiable by reading the file header bytes `\x89PNG`).
- **`model.onnx`**: A valid ONNX model file that accepts input of shape `(1, 3, 32, 32)`.
- **`onnx_verify.txt`**: Must contain a numeric accuracy value (float between 0.0 and 1.0, or percentage between 0 and 100).
- **`optuna.db`**: A valid SQLite database queryable with `optuna.load_study()`.
