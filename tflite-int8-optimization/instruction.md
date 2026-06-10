## TensorFlow Lite Model Optimization for CPU Deployment

Build a Python script (`/app/optimize.py`) that creates a small sentiment-analysis model, converts it to TensorFlow Lite with int8 quantization, benchmarks both versions, and produces a structured report.

### Technical Requirements

- Python 3.x with TensorFlow 2.x (CPU-only is fine)
- All work in a single script: `/app/optimize.py`
- Output report: `/app/report.json`
- Exported TFLite model file: `/app/model_int8.tflite`

### Workflow

1. **Build a small sentiment-analysis model**: Create and train a simple Keras sequential model for binary sentiment classification. Use the IMDB review dataset bundled with TensorFlow (`tf.keras.datasets.imdb`). Limit vocabulary to 10,000 words and pad/truncate sequences to length 200. Train for at least 2 epochs.

2. **Export the original FP32 model**: Save the trained Keras model as a SavedModel to `/app/saved_model/`.

3. **Convert to TensorFlow Lite with int8 quantization**:
   - Use `tf.lite.TFLiteConverter` to convert the SavedModel.
   - Apply post-training full integer quantization (`tf.lite.Optimize.DEFAULT`).
   - Provide a representative dataset (at least 100 samples from the training set) for calibration.
   - Save the quantized model to `/app/model_int8.tflite`.

4. **Benchmark latency**: Measure average inference latency (in milliseconds) for both the original Keras FP32 model and the int8 TFLite model. Run inference on at least 100 test samples and compute the mean latency per sample for each model.

5. **Evaluate accuracy**: Compute top-1 accuracy of both models on the first 1,000 samples of the IMDB test set.

6. **Compute model size**: Measure file size in bytes of the SavedModel directory (sum of all files) and the `.tflite` file. Compute compression ratio = FP32 size / int8 size.

### Output: `/app/report.json`

A JSON file with the following exact structure:

```json
{
  "fp32_accuracy": <float, 0.0-1.0>,
  "int8_accuracy": <float, 0.0-1.0>,
  "accuracy_retention": <float, ratio of int8_accuracy / fp32_accuracy>,
  "fp32_latency_ms": <float, mean per-sample latency in ms>,
  "int8_latency_ms": <float, mean per-sample latency in ms>,
  "fp32_size_bytes": <int>,
  "int8_size_bytes": <int>,
  "compression_ratio": <float, fp32_size / int8_size>,
  "meets_accuracy_requirement": <bool, true if accuracy_retention >= 0.9>
}
```

All float values must be rounded to 4 decimal places.

### Constraints

- The int8 TFLite model (`/app/model_int8.tflite`) must be a valid FlatBuffer file loadable by `tf.lite.Interpreter`.
- `fp32_accuracy` must be > 0.5 (i.e., the model must be better than random guessing).
- `compression_ratio` must be > 1.0 (the int8 model must be smaller than the FP32 model).
- `meets_accuracy_requirement` must be a boolean reflecting whether `accuracy_retention >= 0.9`.
- All keys listed above must be present in `report.json`. No extra top-level keys are allowed.
