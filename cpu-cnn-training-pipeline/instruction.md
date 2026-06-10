## CPU-Based Deep CNN Training & Evaluation Pipeline

Build a complete, reproducible training and evaluation pipeline for a deep CNN using PyTorch (CPU only) for binary image classification (natural vs. man-made scenes). Since no external dataset download is available, generate a synthetic dataset locally.

### Technical Requirements

- Language: Python 3.x
- Framework: PyTorch (CPU only, no CUDA)
- Additional libraries: torchvision, onnx, tensorboard, scikit-learn, Pillow, numpy
- Random seed: set `torch.manual_seed(42)` and `numpy.random.seed(42)` at the start for reproducibility
- Entry point: `/app/pipeline.py` — running `python pipeline.py` executes the full pipeline end-to-end

### Dataset

Generate a synthetic dataset of 600 RGB images (128×128 pixels) under `/app/dataset/`:
- Two classes: `natural` (label 0) and `man_made` (label 1), 300 images each
- Directory structure:
  ```
  /app/dataset/natural/img_0000.png ... img_0299.png
  /app/dataset/man_made/img_0000.png ... img_0299.png
  ```
- `natural` images: random pixel noise with dominant green/blue channels
- `man_made` images: random pixel noise with dominant red/gray channels
- Split ratio: 70% train / 15% validation / 15% test (stratified by class)

### Data Loading & Augmentation

- Use `torch.utils.data.Dataset` and `DataLoader`
- Training augmentation: random horizontal flip, normalize with mean=[0.485, 0.456, 0.406] and std=[0.229, 0.224, 0.225]
- Validation/test: only resize to 128×128 and normalize (same mean/std)
- Batch size: 32

### Model Architecture

Define a custom CNN class named `SceneCNN` in `/app/model.py` with:
- At least 5 `nn.Conv2d` layers
- `nn.BatchNorm2d` after each conv layer
- `nn.ReLU` activation after each batch norm
- `nn.Dropout` (p=0.3) before the final fully-connected layer
- Final output: 2 classes (natural, man_made)
- The class must have a standard `forward(self, x)` method accepting input shape `(B, 3, 128, 128)`

### Training

- Optimizer: SGD with momentum=0.9, learning_rate=0.01
- Loss: CrossEntropyLoss
- Epochs: 10
- Log training loss and validation accuracy to TensorBoard under `/app/runs/`
- Implement early stopping with patience=3 based on validation loss
- Save the best model checkpoint (by validation loss) to `/app/best_model.pth`

### Evaluation

After training, evaluate the best checkpoint on the test set and write results to `/app/results.json` with this exact structure:
```json
{
  "test_accuracy": <float between 0 and 1>,
  "test_loss": <float>,
  "num_test_samples": <int>,
  "classification_report": {
    "natural": {"precision": <float>, "recall": <float>, "f1-score": <float>},
    "man_made": {"precision": <float>, "recall": <float>, "f1-score": <float>}
  },
  "confusion_matrix": [[<int>, <int>], [<int>, <int>]]
}
```

### ONNX Export

Export the best model to `/app/model.onnx` with:
- Opset version: 11
- Input name: `input`
- Output name: `output`
- Dynamic axes for batch dimension
- Dummy input shape: `(1, 3, 128, 128)`

### Output Files

The pipeline must produce all of the following:
| File | Description |
|---|---|
| `/app/dataset/` | Generated synthetic image dataset |
| `/app/model.py` | CNN model definition (`SceneCNN` class) |
| `/app/pipeline.py` | Full pipeline entry point |
| `/app/best_model.pth` | Best model checkpoint |
| `/app/results.json` | Test evaluation metrics |
| `/app/model.onnx` | Exported ONNX model |
| `/app/runs/` | TensorBoard log directory |
