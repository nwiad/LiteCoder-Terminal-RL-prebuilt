## Build a CPU-Based MNIST GAN from Scratch with Training and Sampling

Build and train a Generative Adversarial Network (GAN) that generates 28×28 grayscale MNIST-like digit images. The entire project must use PyTorch on CPU only (no CUDA/GPU). No pretrained weights or model-zoo shortcuts are allowed.

### Technical Requirements

- Language: Python 3
- Framework: PyTorch (CPU only). Do not use `torch.cuda` or `.to("cuda")` anywhere.
- All project files must reside under `/app/mnist_gan/`.

### Project Structure

```
/app/mnist_gan/
├── data/              # MNIST dataset (downloaded automatically via torchvision)
├── outputs/           # Generated sample grids per epoch
├── checkpoints/       # Saved generator model
├── train.py           # Training script
├── sample.py          # Sampling CLI script
├── model.py           # Generator and Discriminator class definitions
├── requirements.txt   # Dependencies (no GPU packages like cudatoolkit)
└── training_log.json  # Training loss log
```

### Model Specifications

**Generator:**
- Input: a 1D latent vector of size `100` (sampled from standard normal distribution).
- Output: a tensor of shape `(1, 28, 28)` with values in range `[-1, 1]`.
- The class must be named `Generator` and defined in `model.py`.
- Constructor signature: `Generator(latent_dim=100)`.
- Must have a `forward(self, z)` method.

**Discriminator:**
- Input: a tensor of shape `(1, 28, 28)`.
- Output: a single scalar (probability) in range `[0, 1]`.
- The class must be named `Discriminator` and defined in `model.py`.
- Constructor signature: `Discriminator()`.
- Must have a `forward(self, img)` method.

### Training Script (`train.py`)

- Downloads MNIST into `/app/mnist_gan/data/` using `torchvision.datasets.MNIST` if not already present.
- Trains the GAN for at least 5 epochs with a batch size of 64.
- At the end of each epoch, saves an 8×8 grid of 64 generated sample images as a PNG file to `/app/mnist_gan/outputs/epoch_{N}.png` (1-indexed, e.g., `epoch_1.png`, `epoch_2.png`, ...).
- After training completes, saves the generator state dict to `/app/mnist_gan/checkpoints/generator_final.pt`.
- Writes a training log to `/app/mnist_gan/training_log.json` with the following JSON structure:

```json
{
  "epochs": [
    {
      "epoch": 1,
      "d_loss": 0.693,
      "g_loss": 0.693
    },
    {
      "epoch": 2,
      "d_loss": 0.65,
      "g_loss": 0.72
    }
  ]
}
```

Each entry must contain `epoch` (int), `d_loss` (float, average discriminator loss for that epoch), and `g_loss` (float, average generator loss for that epoch).

Running `python /app/mnist_gan/train.py` must execute the full training pipeline with no additional arguments required.

### Sampling Script (`sample.py`)

- Loads the saved generator from `/app/mnist_gan/checkpoints/generator_final.pt`.
- Generates 64 images using random latent vectors of size 100.
- Saves the result as an 8×8 grid PNG image to `/app/mnist_gan/outputs/generated_samples.png`.
- Running `python /app/mnist_gan/sample.py` must produce the output with no additional arguments required.

### Output Verification Criteria

1. `/app/mnist_gan/checkpoints/generator_final.pt` exists and is a valid PyTorch state dict that can be loaded into a `Generator(latent_dim=100)` instance.
2. `/app/mnist_gan/training_log.json` exists, is valid JSON, contains an `"epochs"` key with a list of at least 5 entries, and each entry has `epoch`, `d_loss`, and `g_loss` fields.
3. `/app/mnist_gan/outputs/` contains `epoch_1.png` through `epoch_5.png` (at minimum) and each is a valid PNG image.
4. After running `sample.py`, `/app/mnist_gan/outputs/generated_samples.png` exists and is a valid PNG image.
5. The `Generator` class in `model.py` accepts a latent vector of shape `(N, 100)` and produces output of shape `(N, 1, 28, 28)`.
6. The `Discriminator` class in `model.py` accepts input of shape `(N, 1, 28, 28)` and produces output of shape `(N, 1)`.
