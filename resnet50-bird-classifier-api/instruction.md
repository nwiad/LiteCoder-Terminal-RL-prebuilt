## Task: CPU-Optimized ResNet50 for Bird Species Classification

Build a CPU-optimized ResNet50 model fine-tuned on CIFAR-100 (10 classes) and deploy it as a Flask REST API for real-time inference.

**Technical Requirements:**
- Python 3.8+
- PyTorch (CPU-only)
- Flask
- Input: Base64-encoded 32×32 PNG images
- Output: JSON with top-3 class predictions and probabilities
- Inference latency: <200ms median on 4-core CPU

**Project Structure:**
```
/app/
├── model/
│   └── bird_resnet50_cpu.pt
├── data/
│   ├── cifar10bird_train.pt
│   └── cifar10bird_val.pt
├── app/
│   └── app.py
├── scripts/
│   ├── prepare_data.py
│   ├── train.py
│   └── benchmark.py
├── requirements.txt
└── README.md
```

**Data Preparation:**
- Download CIFAR-100 dataset
- Select first 10 classes only
- Apply augmentation: horizontal flips and random crops
- Save train/val splits to `/app/data/cifar10bird_train.pt` and `/app/data/cifar10bird_val.pt`

**Model Requirements:**
- Base architecture: ResNet50
- Modify final layer: replace 1000-class fc with 10-unit fc
- Optimize with `torch.compile` for CPU inference
- Training: AdamW optimizer, 5 epochs, batch size 64
- Save best checkpoint to `/app/model/bird_resnet50_cpu.pt`

**Flask API Specification:**

Endpoint: `GET /ping`
- Response: `{"status": "healthy"}` with status code 200

Endpoint: `POST /predict`
- Request body (JSON):
  ```json
  {
    "image": "<base64-encoded-png-string>"
  }
  ```
- Image format: 32×32 PNG, base64-encoded
- Response (JSON):
  ```json
  {
    "predictions": [
      {"class": 0, "probability": 0.85},
      {"class": 3, "probability": 0.10},
      {"class": 7, "probability": 0.03}
    ]
  }
  ```
- Return top-3 predictions sorted by probability (descending)
- Probabilities should be float values between 0 and 1

**Benchmark Requirements:**
- Script location: `/app/scripts/benchmark.py`
- Warm-up: 10 dummy inference calls
- Measurement: 100 sequential inference calls
- Output metrics to `/app/benchmark_results.json`:
  ```json
  {
    "median_latency_ms": 150.5,
    "p95_latency_ms": 180.2,
    "mean_latency_ms": 155.3
  }
  ```

**Deployment Requirements:**
- `/app/requirements.txt`: Pin all dependencies (CPU-only, no CUDA)
- `/app/README.md`: Include setup instructions with exact commands:
  - `pip install -r requirements.txt`
  - `python app/app.py`
- Server must start on `http://0.0.0.0:5000`

**Error Handling:**
- `/predict` endpoint must return status code 400 for invalid base64 or non-PNG images
- `/predict` endpoint must return status code 500 for model inference errors
