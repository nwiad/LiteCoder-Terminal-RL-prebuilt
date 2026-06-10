## PyTorch CPU-based MNIST Autoencoder

Build, train, and evaluate a PyTorch autoencoder on the MNIST dataset using CPU only. The autoencoder compresses 28×28 grayscale digit images into a 16-dimensional latent space and reconstructs them. All code should be in a single Python script `/app/train_autoencoder.py`.

### Technical Requirements

- Language: Python 3.x
- Framework: PyTorch (CPU build, no CUDA)
- Dataset: MNIST (downloaded programmatically via `torchvision.datasets.MNIST` to `/app/data/`)
- No GPU usage allowed; all tensors must stay on CPU

### Model Architecture

The autoencoder must use fully-connected (Linear) layers with the following exact structure:

**Encoder:** 784 → 512 → 256 → 128 → 16
**Decoder:** 16 → 128 → 256 → 512 → 784

- Use ReLU activation between all hidden layers
- Use Sigmoid activation at the decoder output layer
- No batch normalization layers
- Input images are flattened from 28×28 to 784

### Training Specifications

- Optimizer: Adam (default learning rate)
- Loss function: MSE (Mean Squared Error)
- Batch size: 256
- Epochs: 10
- Use the standard MNIST train split for training

### Output Files

All output files must be created at the following exact paths:

1. **Model checkpoint:** `/app/outputs/ae_mnist.pt`
   - Save the model's `state_dict()` using `torch.save()`

2. **Metrics file:** `/app/outputs/metrics.json`
   - A JSON file with the following structure:
   ```json
   {
     "train_loss_per_epoch": [0.0512, 0.0321, ...],
     "test_avg_mse_per_image": 0.0123,
     "test_avg_mse_per_pixel": 0.0000159,
     "total_epochs": 10,
     "batch_size": 256,
     "latent_dim": 16
   }
   ```
   - `train_loss_per_epoch`: list of 10 floats, one average MSE loss value per epoch
   - `test_avg_mse_per_image`: average MSE computed over all test images (each image is a 784-dim vector)
   - `test_avg_mse_per_pixel`: `test_avg_mse_per_image / 784`

3. **Training log:** `/app/logs/train.log`
   - One line per epoch in the format: `Epoch [N/10], Loss: X.XXXX`
   - After training, append a line: `Test Avg MSE per image: X.XXXXXX`
   - After that, append a line: `Test Avg MSE per pixel: X.XXXXXXXX`

4. **Reconstruction visualization:** `/app/outputs/reconstruction.png`
   - A saved matplotlib figure showing 10 randomly selected test images
   - Top row: 10 original images
   - Bottom row: 10 corresponding reconstructed images
   - Each subplot displays a 28×28 grayscale image

### Quality Constraints

- The final `test_avg_mse_per_image` (over 784-dim vectors with pixel values in [0,1]) must be below 0.05 after 10 epochs of training
- The saved model at `/app/outputs/ae_mnist.pt` must be loadable and produce reconstructions consistent with the reported metrics

### Directory Structure After Execution

```
/app/
├── train_autoencoder.py
├── data/
│   └── MNIST/          (downloaded dataset)
├── logs/
│   └── train.log
└── outputs/
    ├── ae_mnist.pt
    ├── metrics.json
    └── reconstruction.png
```
