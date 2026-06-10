## PyTorch CPU Optimization and Benchmarking

Optimize a PyTorch sentiment analysis model for CPU inference, benchmark multiple optimization techniques, and produce a structured performance report comparing them against a baseline.

### Technical Requirements

- Language: Python 3.x
- Framework: PyTorch (CPU only, no GPU/CUDA)
- All code in a single script: `/app/optimize_benchmark.py`
- Output report: `/app/benchmark_report.json`
- The script must be runnable via `python /app/optimize_benchmark.py` and produce the output file upon completion.

### Model and Dataset

- Define a simple PyTorch `nn.Module` sentiment analysis model (e.g., embedding + linear layers) within the script. The model should accept tokenized integer sequences as input and output binary sentiment predictions (positive/negative).
- Generate a synthetic test dataset of at least 200 samples within the script. Each sample is a list of integer token IDs (sequence length between 10 and 50) with a binary label (0 or 1).
- The model does not need to be pre-trained to high accuracy; the focus is on optimization technique implementation and benchmarking correctness.

### Optimization Techniques

Implement and benchmark the following optimization approaches:

1. **baseline**: Unoptimized eager-mode PyTorch inference.
2. **torchscript**: Model optimized via TorchScript (`torch.jit.trace` or `torch.jit.script`).
3. **quantized**: Model with INT8 dynamic quantization applied via `torch.quantization.quantize_dynamic`.
4. **combined**: Model with both TorchScript and quantization applied together.

Each technique must be benchmarked independently.

### Benchmarking Requirements

- For each optimization technique, measure:
  - **avg_latency_ms**: Average inference latency per sample in milliseconds (run at least 50 inference iterations to compute the average).
  - **throughput_samples_per_sec**: Number of samples processed per second.
  - **accuracy**: Classification accuracy on the synthetic test dataset (fraction between 0.0 and 1.0).
  - **model_size_bytes**: Size of the serialized model in bytes (use `torch.save` to a temporary buffer or file to measure).

### Output Format

`/app/benchmark_report.json` must be a valid JSON file with the following structure:

```json
{
  "results": {
    "baseline": {
      "avg_latency_ms": <float>,
      "throughput_samples_per_sec": <float>,
      "accuracy": <float>,
      "model_size_bytes": <int>
    },
    "torchscript": {
      "avg_latency_ms": <float>,
      "throughput_samples_per_sec": <float>,
      "accuracy": <float>,
      "model_size_bytes": <int>
    },
    "quantized": {
      "avg_latency_ms": <float>,
      "throughput_samples_per_sec": <float>,
      "accuracy": <float>,
      "model_size_bytes": <int>
    },
    "combined": {
      "avg_latency_ms": <float>,
      "throughput_samples_per_sec": <float>,
      "accuracy": <float>,
      "model_size_bytes": <int>
    }
  },
  "summary": {
    "fastest_technique": "<string: one of baseline|torchscript|quantized|combined>",
    "smallest_model_technique": "<string: one of baseline|torchscript|quantized|combined>",
    "num_test_samples": <int>
  }
}
```

### Constraints

- All numeric metric values must be positive (> 0).
- `accuracy` values must be between 0.0 and 1.0 inclusive.
- `fastest_technique` must correspond to the technique with the lowest `avg_latency_ms`.
- `smallest_model_technique` must correspond to the technique with the smallest `model_size_bytes`.
- `num_test_samples` must be >= 200.
- The `quantized` model's `model_size_bytes` must be strictly less than the `baseline` model's `model_size_bytes` (quantization should reduce model size).
- All four technique keys must be present under `results`.
