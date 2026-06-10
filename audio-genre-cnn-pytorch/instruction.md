## Audio Genre Classification with PyTorch

Train a lightweight CNN on the GTZAN 10-second snippets dataset to classify music genres. The entire pipeline must use only PyTorch (CPU build), torchaudio, and tensorboard — no other audio or ML libraries.

### Technical Requirements

- **Language:** Python 3.x
- **Libraries:** PyTorch (CPU), torchaudio, tensorboard. No external audio libraries (e.g., librosa, soundfile) beyond what torchaudio provides.
- **Training:** CPU-only, no GPU/CUDA required.
- **Entry point:** `/app/train.py` — running `python train.py` must execute the full pipeline (download data, train, evaluate, save outputs).

### Dataset

- Use the GTZAN dataset (10-second audio snippets, 10 genres).
- Download and extract the dataset programmatically within `train.py`.
- All 10 genres must be represented: blues, classical, country, disco, hiphop, jazz, metal, pop, reggae, rock.

### Data Pipeline

- Resample all audio to 16 kHz on-the-fly.
- Crop or pad each clip to exactly 4 seconds (64000 samples at 16 kHz).
- Convert audio to log-mel spectrograms with 64 mel bins, producing input tensors of shape `(1, 64, 64)`.
- Split data into train, validation, and test sets. The test set must contain at least 10% of total samples.

### Model Architecture

- A CNN with exactly 4 convolutional layers.
- Each convolutional block must include: Conv2d → BatchNorm2d → ReLU → MaxPool2d.
- Input shape: `(batch, 1, 64, 64)` (single-channel log-mel spectrogram).
- Output: 10 logits (one per genre).

### Training

- Optimizer: Adam.
- Loss: Cross-entropy.
- Train for at least 20 epochs.
- Track and save the best model checkpoint by validation accuracy.
- Log to TensorBoard under `/app/runs/` directory. Logs must include at minimum: training loss and training accuracy per epoch.

### Output Requirements

1. **Best model checkpoint:** Save to `/app/best_model.pth`. Must be loadable via `torch.load()`.

2. **Metrics file:** Save to `/app/metrics.json` with the following structure:
```json
{
  "test_accuracy": 0.65,
  "num_epochs_trained": 20,
  "num_genres": 10,
  "best_val_accuracy": 0.68,
  "genre_labels": ["blues", "classical", "country", "disco", "hiphop", "jazz", "metal", "pop", "reggae", "rock"]
}
```
- `test_accuracy` and `best_val_accuracy` are floats between 0.0 and 1.0.
- `test_accuracy` must be ≥ 0.40.
- `num_genres` must be 10.
- `genre_labels` must list all 10 GTZAN genres.

3. **TensorBoard logs:** Directory `/app/runs/` must exist and contain valid TensorBoard event files.
