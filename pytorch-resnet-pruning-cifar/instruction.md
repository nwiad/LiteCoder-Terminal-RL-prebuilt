## PyTorch Model Optimization via Pruning

Optimize a pre-trained ResNet18 model on CIFAR-10 by applying magnitude-based unstructured pruning, then produce a performance comparison report.

### Technical Requirements

- Language: Python 3.x
- Libraries: PyTorch (CPU), torchvision, matplotlib
- All output files must be written under `/app/output/`

### Task Steps

1. Download CIFAR-10 and train (or fine-tune from `torchvision.models.resnet18(pretrained=True)`) a ResNet18 that achieves **≥ 85% test accuracy** on CIFAR-10. Save the original model checkpoint to `/app/output/original_model.pth`.

2. Apply **magnitude-based unstructured pruning** using `torch.nn.utils.prune` to all `Conv2d` and `Linear` layers. The global pruning amount must achieve **≥ 30% overall sparsity** (i.e., at least 30% of all prunable parameters are zero). After pruning, remove the pruning re-parameterization wrappers and save the pruned model to `/app/output/pruned_model.pth`.

3. Benchmark the original model vs. the pruned model on the CIFAR-10 test set and collect the following metrics:
   - `original_accuracy`: float, test accuracy of the original model (0–100 scale, e.g., 87.5)
   - `pruned_accuracy`: float, test accuracy of the pruned model (0–100 scale)
   - `accuracy_drop`: float, `original_accuracy - pruned_accuracy` (must be **≤ 2.0**)
   - `original_param_count`: int, total number of parameters in the original model
   - `pruned_nonzero_param_count`: int, number of non-zero parameters in the pruned model
   - `sparsity`: float, percentage of zero parameters in the pruned model (0–100 scale, must be **≥ 30.0**)
   - `original_size_mb`: float, file size of `/app/output/original_model.pth` in megabytes (rounded to 2 decimal places)
   - `pruned_size_mb`: float, file size of `/app/output/pruned_model.pth` in megabytes (rounded to 2 decimal places)
   - `original_inference_time_ms`: float, average CPU inference time per batch (batch size = 1) for the original model in milliseconds (averaged over ≥ 50 runs)
   - `pruned_inference_time_ms`: float, average CPU inference time per batch (batch size = 1) for the pruned model in milliseconds (averaged over ≥ 50 runs)

4. Write all metrics to `/app/output/metrics.json` as a single flat JSON object with exactly the keys listed above. Example structure:
   ```json
   {
     "original_accuracy": 87.52,
     "pruned_accuracy": 86.31,
     "accuracy_drop": 1.21,
     "original_param_count": 11173962,
     "pruned_nonzero_param_count": 7821773,
     "sparsity": 30.0,
     "original_size_mb": 42.73,
     "pruned_size_mb": 42.73,
     "original_inference_time_ms": 12.34,
     "pruned_inference_time_ms": 11.02
   }
   ```

5. Generate a bar-chart comparison image using matplotlib that visualizes at least accuracy, parameter count, and inference time for original vs. pruned models. Save it to `/app/output/report.png`.

6. Write a plain-text summary (≥ 3 lines) to `/app/output/summary.txt` that includes the original accuracy, pruned accuracy, accuracy drop, and sparsity percentage.

### Output Files

| File | Format | Description |
|---|---|---|
| `/app/output/original_model.pth` | PyTorch checkpoint | Original trained ResNet18 |
| `/app/output/pruned_model.pth` | PyTorch checkpoint | Pruned ResNet18 (wrappers removed) |
| `/app/output/metrics.json` | JSON | All benchmark metrics (flat object, keys as specified) |
| `/app/output/report.png` | PNG image | Bar-chart comparison report |
| `/app/output/summary.txt` | Plain text | Human-readable summary of results |

### Constraints

- `original_accuracy` ≥ 85.0
- `sparsity` ≥ 30.0
- `accuracy_drop` ≤ 2.0
- All numeric values in `metrics.json` must be numbers (not strings)
- `report.png` must be a valid PNG file with size > 0 bytes
- `summary.txt` must contain at least 3 lines of text
