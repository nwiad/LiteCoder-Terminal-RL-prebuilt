## CPU-Optimized MNIST GAN Training and Evaluation

Train and evaluate a Generative Adversarial Network (GAN) on the MNIST dataset using CPU-only computation, achieving a Fréchet Inception Distance (FID) score below 150 within 20 epochs.

### Technical Requirements

- Language: Python 3.x
- Deep learning framework: PyTorch (CPU only, no CUDA)
- Entry point: `/app/train.py` — running `python train.py` must execute the full pipeline (training + evaluation + output generation)
- The MNIST dataset should be automatically downloaded (e.g., via `torchvision.datasets.MNIST`) into `/app/data/`

### Architecture Requirements

- **Generator**: Takes a 1D latent noise vector of size 100 as input and outputs a 28×28 grayscale image with pixel values normalized to [0, 1].
- **Discriminator**: Takes a 28×28 grayscale image as input and outputs a single scalar probability.
- Both networks must use only CPU tensors (no `.cuda()` or `.to('cuda')` calls).

### Training Requirements

- Train for exactly 20 epochs on the MNIST training set.
- Use CPU optimization techniques (e.g., multi-threaded data loading with `num_workers >= 2`, `torch.no_grad()` during evaluation).
- Batch size: 64.

### Output Requirements

All outputs must be generated automatically when `train.py` is executed.

1. **Trained Generator Model**
   - Save the trained generator's state dict to: `/app/generator.pth`

2. **Generated Sample Images**
   - After training, generate exactly 64 images using the trained generator with random latent vectors (size 100 each).
   - Save the 64 generated images as a single grid image to: `/app/generated_samples.png`
     - The grid should be 8×8 (8 columns, 8 rows).
     - Each cell is a 28×28 grayscale image.

3. **Evaluation Report**
   - Compute the FID score between 1000 generated images and 1000 real MNIST test images.
   - Save the evaluation report as JSON to: `/app/evaluation.json`
   - The JSON must contain the following top-level keys:
     ```json
     {
       "fid_score": <float>,
       "num_epochs": 20,
       "batch_size": 64,
       "latent_dim": 100,
       "device": "cpu",
       "generator_params": <int>,
       "discriminator_params": <int>,
       "final_generator_loss": <float>,
       "final_discriminator_loss": <float>
     }
     ```
   - `fid_score` must be a finite positive number less than 150.
   - `generator_params` and `discriminator_params` are the total number of trainable parameters in each network.
   - `final_generator_loss` and `final_discriminator_loss` are the average losses from the last epoch.

### Constraints

- The entire pipeline (training + evaluation + output generation) must run on CPU only.
- All output files (`generator.pth`, `generated_samples.png`, `evaluation.json`) must exist after execution completes.
- The FID score reported in `evaluation.json` must be below 150.
