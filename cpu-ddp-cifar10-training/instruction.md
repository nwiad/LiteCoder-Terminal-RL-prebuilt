## Task: CPU-Based Distributed Training with PyTorch DDP

Implement a CPU-based distributed data-parallel training system using PyTorch's DistributedDataParallel (DDP) to train a CNN on CIFAR-10 across multiple CPU processes.

## Technical Requirements

- Python 3.8+
- PyTorch with CPU support
- Use `torch.distributed` with `gloo` backend (CPU-compatible)
- Train across 2 processes minimum
- Input: CIFAR-10 dataset (auto-downloaded via torchvision)
- Output: `/app/training_results.json`

## Implementation Requirements

Create a training script (`train.py`) that:

1. **Model Architecture**: Implement a CNN with at least 2 convolutional layers for CIFAR-10 (10 classes, 32x32 RGB images)

2. **Distributed Setup**:
   - Initialize process group with `gloo` backend
   - Support rank and world_size configuration via environment variables or arguments
   - Wrap model with `DistributedDataParallel`

3. **Data Loading**:
   - Use `DistributedSampler` to partition CIFAR-10 training data across processes
   - Each process should handle non-overlapping data subsets

4. **Training Loop**:
   - Train for at least 2 epochs
   - Use cross-entropy loss and any standard optimizer
   - Synchronize gradients across processes automatically via DDP

5. **Results Output**:
   - Save training metrics to `/app/training_results.json` (from rank 0 only)
   - JSON structure:
     ```json
     {
       "final_epoch": 2,
       "final_train_loss": 1.234,
       "world_size": 2,
       "backend": "gloo"
     }
     ```

6. **Launch Mechanism**:
   - Provide a way to spawn multiple processes (e.g., using `torch.multiprocessing.spawn` or manual script execution)
   - Script should be executable as: `python train.py` or via a launcher

## Validation Criteria

- Training completes successfully across multiple CPU processes
- Each process handles different data samples (no duplication)
- Gradients are synchronized across processes
- Final results are saved correctly to `/app/training_results.json`
- Loss decreases over epochs (demonstrating actual learning)
