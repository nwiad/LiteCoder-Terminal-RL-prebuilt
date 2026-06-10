## Optimizing CPU-based BERT Fine-Tuning

Write a Python script (`/app/train.py`) that fine-tunes a pre-trained BERT model (`bert-base-uncased`) on a sentiment analysis task using CPU-only infrastructure, with CPU-specific optimizations applied. The script should produce a structured performance report.

### Technical Requirements

- Language: Python 3.x
- Libraries: `transformers`, `torch`, `datasets`, `scikit-learn`
- All training must run on CPU (no CUDA/GPU)
- Input: The script should load the SST-2 dataset from Hugging Face `datasets` library (the `glue` `sst2` split)
- Output: `/app/performance_report.json`

### Script Requirements

The script `/app/train.py` must:

1. **CPU Optimization Configuration**: Before training, apply CPU-specific optimizations by setting environment variables for threading. The script must set `OMP_NUM_THREADS` and `MKL_NUM_THREADS` environment variables programmatically (via `os.environ`) before importing or initializing PyTorch training components.

2. **Dataset Preparation**: Load the SST-2 dataset from Hugging Face (`glue`, `sst2`). Use the `validation` split as the test set. Tokenize using `BertTokenizer` from `bert-base-uncased` with `max_length=128`, `padding="max_length"`, and `truncation=True`. To keep training feasible on CPU, use only the first **200** examples from the `train` split and the first **50** examples from the `validation` split.

3. **Model Fine-Tuning**: Fine-tune `BertForSequenceClassification` (with `num_labels=2`) using Hugging Face `Trainer` API. Training arguments must include:
   - `output_dir="./results"`
   - `num_train_epochs=1`
   - `per_device_train_batch_size=8`
   - `per_device_eval_batch_size=8`
   - `no_cuda=True`
   - `logging_steps=10`
   - `save_strategy="no"`

4. **Evaluation**: After training, evaluate on the test subset and compute accuracy using `sklearn.metrics.accuracy_score`.

5. **Resource Monitoring**: Record wall-clock training time (in seconds) using Python's `time` module (measuring the duration of `trainer.train()`).

6. **Performance Report**: Write `/app/performance_report.json` with the following exact structure:

```json
{
  "cpu_optimizations": {
    "omp_num_threads": "<value set>",
    "mkl_num_threads": "<value set>"
  },
  "training_config": {
    "model_name": "bert-base-uncased",
    "max_length": 128,
    "num_train_epochs": 1,
    "per_device_train_batch_size": 8,
    "train_samples": 200,
    "eval_samples": 50
  },
  "results": {
    "test_accuracy": <float between 0 and 1>,
    "training_time_seconds": <float>
  }
}
```

All numeric values must be actual measured values (not placeholders). `test_accuracy` must be a float rounded to 4 decimal places. `training_time_seconds` must be a positive float.

### Execution

Running `python /app/train.py` should complete end-to-end and produce `/app/performance_report.json` with no manual intervention.
