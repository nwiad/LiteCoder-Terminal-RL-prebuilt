## Task: CPU-Based Model Compression via Knowledge Distillation

Compress a ResNet34 teacher model into a ResNet18 student model using knowledge distillation on CIFAR-10, achieving ≥85% test accuracy without GPU acceleration.

**Technical Requirements:**
- Python 3.x with PyTorch (CPU-only)
- CIFAR-10 dataset
- All training and inference must run on CPU (no CUDA)
- Output files: `/app/resnet18_cifar10_distilled.pt`, `/app/metrics.json`

**Implementation Requirements:**

1. **Model Architecture:**
   - Teacher: Pre-trained ResNet34 on CIFAR-10
   - Student: ResNet18 (randomly initialized)

2. **Knowledge Distillation Parameters:**
   - Temperature (T): 4
   - Alpha (α): 0.7 (weight for distillation loss)
   - Distillation loss: KL divergence between teacher and student softmax outputs
   - Hard label loss: Cross-entropy with ground truth

3. **Training Configuration:**
   - Dataset: CIFAR-10 (train/test split)
   - Maximum epochs: 100
   - Stop early if student achieves ≥85% test accuracy
   - Use deterministic data loaders for reproducibility

4. **Output Files:**

   **Model checkpoint** (`/app/resnet18_cifar10_distilled.pt`):
   - Final trained student model state_dict
   - File size must be < 35 MB

   **Metrics file** (`/app/metrics.json`):
   ```json
   {
     "teacher_accuracy": <float>,
     "student_accuracy": <float>,
     "teacher_params": <int>,
     "student_params": <int>,
     "teacher_size_mb": <float>,
     "student_size_mb": <float>,
     "training_time_seconds": <float>,
     "epochs_trained": <int>
   }
   ```

**Success Criteria:**
- Student model test accuracy ≥ 85%
- Student model file size < 35 MB
- All operations completed on CPU
- Valid metrics.json with all required fields
