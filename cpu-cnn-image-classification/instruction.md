## CPU-based Deep Learning Pipeline for Binary Image Classification

Build a self-contained, CPU-only deep learning pipeline in Python that trains and evaluates a lightweight CNN for binary image classification (pneumonia vs. normal chest X-rays), then outputs a structured performance report.

### Technical Requirements

- Language: Python 3.x
- Libraries: PyTorch (CPU), torchvision, scikit-learn, numpy. No GPU or CUDA usage.
- Entry point: `/app/pipeline.py`
- Configuration input: `/app/config.json`
- Output report: `/app/report.json`
- Saved model: `/app/model.pt`

Running `python /app/pipeline.py` must read the config, execute the full pipeline, and produce all output files.

### Input: `/app/config.json`

A JSON file with the following structure (provided at runtime):

```json
{
  "num_train_samples": 200,
  "num_test_samples": 50,
  "image_size": 64,
  "num_epochs": 3,
  "batch_size": 16,
  "learning_rate": 0.001,
  "random_seed": 42
}
```

- `num_train_samples`: total training images (split evenly between two classes: "pneumonia" and "normal")
- `num_test_samples`: total test images (split evenly between two classes)
- `image_size`: height and width of square grayscale input images (1 channel)
- `num_epochs`: number of training epochs
- `batch_size`: batch size for data loaders
- `learning_rate`: optimizer learning rate
- `random_seed`: seed for reproducibility of data generation and training

### Synthetic Data Generation

Since no external dataset is available, the pipeline must generate synthetic grayscale images internally based on the config parameters. Each image should be a single-channel (1 × image_size × image_size) tensor. Class 0 = "normal", Class 1 = "pneumonia". The data must be split into training and test sets as specified by the config. Use `random_seed` for reproducible generation.

### Model Architecture

Implement a lightweight CNN with the following constraints:

- Input: 1-channel grayscale images of size `image_size × image_size`
- The network must contain at least 2 convolutional layers (each followed by ReLU activation and max pooling)
- The network must contain at least 1 fully connected layer
- Output: 2 classes (binary classification)
- Total trainable parameters must not exceed 500,000

### Training

- Use CrossEntropyLoss as the loss function
- Use Adam optimizer with the learning rate from config
- Train for exactly `num_epochs` epochs as specified in config
- Set all random seeds (Python, NumPy, PyTorch) to `random_seed` before training

### Model Saving

Save the trained model's state dict to `/app/model.pt` using `torch.save()`. The file must be loadable via `torch.load()`.

### Output: `/app/report.json`

After training and evaluation on the test set, write a JSON file with this exact structure:

```json
{
  "model_summary": {
    "total_parameters": <int>,
    "trainable_parameters": <int>
  },
  "training": {
    "num_epochs": <int>,
    "final_train_loss": <float>,
    "loss_per_epoch": [<float>, ...]
  },
  "evaluation": {
    "accuracy": <float>,
    "precision": <float>,
    "recall": <float>,
    "f1_score": <float>
  }
}
```

Field requirements:
- `total_parameters` and `trainable_parameters`: positive integers, must not exceed 500,000
- `num_epochs`: must match the config value
- `final_train_loss`: the training loss of the last epoch (non-negative float)
- `loss_per_epoch`: a list of floats with length equal to `num_epochs`, each non-negative
- `accuracy`, `precision`, `recall`, `f1_score`: floats in the range [0.0, 1.0]
- All float values must be JSON-serializable (no NaN or Infinity)
