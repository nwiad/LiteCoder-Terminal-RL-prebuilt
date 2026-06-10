## CPU-Based MNIST GAN Training

Implement and train a Generative Adversarial Network (GAN) on the MNIST dataset using PyTorch, running entirely on CPU, to generate handwritten digit images.

### Technical Requirements

- Language: Python 3.x
- Framework: PyTorch (CPU only, no CUDA)
- Main script: `/app/train_gan.py`
- All model operations must explicitly use `torch.device("cpu")`

### Architecture

**Generator:**
- Input: a latent vector of size 100 (sampled from standard normal distribution)
- Output: a flattened image tensor of size 784 (representing a 28×28 grayscale image)
- Output activation: `tanh` (pixel values in range [-1, 1])
- The Generator class must be named `Generator`

**Discriminator:**
- Input: a flattened image tensor of size 784
- Output: a single scalar (probability via `sigmoid`)
- The Discriminator class must be named `Discriminator`

Both `Generator` and `Discriminator` must be subclasses of `torch.nn.Module` and implement a `forward` method.

### Training

- Use the MNIST training set (downloaded via `torchvision.datasets.MNIST` to `/app/data/`)
- Train for at least 10 epochs
- Use Binary Cross-Entropy loss (`torch.nn.BCELoss`)
- Use Adam optimizer for both Generator and Discriminator
- Batch size: 64
- Images must be normalized to [-1, 1]

### Output Files

After training completes, the script must produce the following:

1. `/app/generator.pth` — saved state dict of the trained Generator model
2. `/app/discriminator.pth` — saved state dict of the trained Discriminator model
3. `/app/generated_samples.png` — a grid image of generated digits (at least 16 samples arranged in a grid using `torchvision.utils.save_image` or equivalent), saved as a PNG file with dimensions at least 112×112 pixels
4. `/app/metrics.json` — a JSON file with the following structure:

```json
{
  "num_epochs": <int>,
  "final_g_loss": <float>,
  "final_d_loss": <float>,
  "total_training_time_seconds": <float>,
  "num_generated_samples": <int>,
  "device": "cpu"
}
```

- `num_epochs`: the total number of epochs trained (>= 10)
- `final_g_loss`: generator loss from the last training batch of the final epoch
- `final_d_loss`: discriminator loss from the last training batch of the final epoch
- `total_training_time_seconds`: wall-clock training time in seconds (> 0)
- `num_generated_samples`: number of sample images generated in the grid (>= 16)
- `device`: must be the string `"cpu"`

### Execution

Running `python /app/train_gan.py` should execute the full pipeline: data loading, training, model saving, sample generation, and metrics output. No command-line arguments are required.
