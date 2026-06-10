## CPU-Based MNIST Denoising Autoencoder

Build and train a denoising autoencoder on the MNIST dataset using PyTorch (CPU-only). The model must recover clean digits from noisy inputs and achieve a test MSE below 0.25.

### Technical Requirements

- Language: Python 3.x
- Framework: PyTorch (CPU-only, no CUDA)
- All output files written under `/app/`

### Noise Model

- Input noise type: random bit-flip noise applied to binarized MNIST images
- Noise rate: 20% of pixels are flipped (0→1 or 1→0)
- MNIST pixel values must be binarized (thresholded to 0 or 1) before applying noise

### Model Architecture Constraints

- Fully-connected (linear) autoencoder only — no convolutional layers
- Maximum 3 hidden layers in the encoder and 3 in the decoder
- Maximum 256 neurons per hidden layer
- Input/output dimension: 784 (28×28 flattened)

### Training Requirements

- Train on the MNIST training set (60,000 images)
- Evaluate on the MNIST test set (10,000 images)
- Loss function: Mean Squared Error (MSE)
- Training must complete within 5 minutes of wall-clock time on CPU
- Save the best model checkpoint to `/app/ckpt/best_model.pt`

### Output Files

1. `/app/metrics.json` — A JSON file containing:
   ```json
   {
     "test_mse": <float>,
     "training_time_seconds": <float>,
     "total_parameters": <int>
   }
   ```
   - `test_mse`: final MSE evaluated on the full MNIST test set with 20% bit-flip noise (must be < 0.25)
   - `training_time_seconds`: total training wall-clock time in seconds
   - `total_parameters`: total number of trainable parameters in the model

2. `/app/reconstruction.png` — A saved image showing a grid of sample reconstructions from the test set. The grid must contain at least 5 columns, where each column shows three rows: (top) clean original image, (middle) noisy input, (bottom) model reconstruction.

3. `/app/ckpt/best_model.pt` — The saved PyTorch model checkpoint (loadable via `torch.load()`).

### Evaluation Criteria

- `test_mse` in `/app/metrics.json` must be a valid float less than 0.25
- `total_parameters` must be a positive integer
- `training_time_seconds` must be less than 300
- `/app/reconstruction.png` must be a valid image file
- `/app/ckpt/best_model.pt` must be a valid PyTorch checkpoint file
- The model loaded from the checkpoint must be a fully-connected network (no Conv layers)
