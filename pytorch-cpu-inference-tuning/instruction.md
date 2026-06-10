## PyTorch CPU Performance Tuning and Model Optimization

Optimize a PyTorch vision model's CPU inference throughput by applying standard optimizations, benchmarking the results, and exposing the optimized model via an HTTP endpoint.

### Technical Requirements

- Language: Python 3.x
- Framework: PyTorch (>=1.13), Flask
- All files must be created under `/app/`

### Baseline Model

Create a baseline CIFAR-10 CNN model with the following fixed architecture and save it to `/app/cifar10_baseline.pth`:

- `conv1`: Conv2d(3, 32, kernel_size=3, padding=1) → ReLU → MaxPool2d(2)
- `conv2`: Conv2d(32, 64, kernel_size=3, padding=1) → ReLU → MaxPool2d(2)
- `conv3`: Conv2d(64, 128, kernel_size=3, padding=1) → ReLU → MaxPool2d(2)
- `fc1`: Linear(128 * 4 * 4, 256) → ReLU
- `fc2`: Linear(256, 10)

The model class must be named `CIFAR10Net` and defined in `/app/model.py`. Save the model's `state_dict` to `/app/cifar10_baseline.pth` using `torch.save()`.

### Required Files

1. `/app/model.py` — Contains the `CIFAR10Net` class definition.

2. `/app/benchmark.py` — Benchmark script that:
   - Loads the model from `/app/cifar10_baseline.pth`
   - Creates a synthetic CIFAR-10 validation dataset (32×32 RGB images, 10 classes, at least 10000 samples)
   - Runs 3 warm-up iterations followed by 10 timed iterations
   - Measures and reports images/s throughput (mean and std)
   - Computes top-1 accuracy on the synthetic dataset
   - Writes results to `/app/benchmark_results.json`

   `/app/benchmark_results.json` format:
   ```json
   {
     "baseline": {
       "throughput_mean": <float>,
       "throughput_std": <float>,
       "top1_accuracy": <float>,
       "batch_size": <int>
     },
     "optimized": {
       "throughput_mean": <float>,
       "throughput_std": <float>,
       "top1_accuracy": <float>,
       "batch_size": <int>,
       "optimizations_applied": [<string>, ...]
     }
   }
   ```
   All throughput values are in images/second. Accuracy is a float between 0.0 and 1.0.

3. `/app/optimize.py` — Optimization script that applies the following optimizations and saves the result:
   - Sets `torch.set_num_threads()` based on available CPU cores
   - Converts the model to `channels_last` memory format
   - Converts the model to TorchScript via `torch.jit.trace` or `torch.jit.script`
   - Applies `torch.jit.optimize_for_inference` on the scripted model
   - Saves the optimized TorchScript model to `/app/cifar10_optimized.pt`
   - Verifies numerical consistency: the max absolute difference between baseline and optimized model outputs on the same random input (batch of 8, 3×32×32) must be < 1e-4
   - Writes verification result to `/app/optimization_report.json`

   `/app/optimization_report.json` format:
   ```json
   {
     "optimizations_applied": [<string>, ...],
     "numerical_consistency": true/false,
     "max_abs_diff": <float>,
     "optimized_model_path": "cifar10_optimized.pt"
   }
   ```
   `optimizations_applied` must be a list of string labels describing each optimization (e.g., `"channels_last"`, `"torchscript"`, `"optimize_for_inference"`).

4. `/app/model_server.py` — Flask HTTP server that:
   - Loads the optimized model from `/app/cifar10_optimized.pt` at startup
   - Exposes a `POST /predict` endpoint
   - Accepts JSON input: `{"input": [<nested list representing a batch of 3×32×32 images>]}`
   - Returns JSON output: `{"predictions": [<int>, ...], "probabilities": [[<float>, ...], ...]}`
     - `predictions`: list of predicted class indices (0-9)
     - `probabilities`: list of softmax probability vectors (each of length 10)
   - Exposes a `GET /health` endpoint that returns `{"status": "ok"}`
   - Runs on `0.0.0.0:5000`

5. `/app/results.json` — Final summary file produced after running all steps:
   ```json
   {
     "baseline_throughput": <float>,
     "optimized_throughput": <float>,
     "speedup": <float>,
     "baseline_accuracy": <float>,
     "optimized_accuracy": <float>,
     "numerical_consistency": true/false
   }
   ```
   `speedup` is `optimized_throughput / baseline_throughput`.

### Constraints

- The model architecture in `CIFAR10Net` must not be modified during optimization.
- The optimized model must produce numerically consistent results with the baseline (max absolute difference < 1e-4).
- All JSON output files must be valid JSON and parseable by `json.load()`.
- `benchmark.py` must be runnable standalone via `python /app/benchmark.py` and produce `/app/benchmark_results.json`.
- `optimize.py` must be runnable standalone via `python /app/optimize.py` and produce both `/app/cifar10_optimized.pt` and `/app/optimization_report.json`.
- `model_server.py` must be runnable via `python /app/model_server.py` (it depends on `/app/cifar10_optimized.pt` existing).
