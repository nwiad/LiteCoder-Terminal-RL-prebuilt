## Build CPU-only PyTorch 2.4 from Source with MKL Backend

Build a CPU-only distribution of PyTorch 2.4 from source on Ubuntu 22.04, linked against Intel MKL, and produce a distributable wheel file along with a validation report.

### Technical Requirements

- **OS:** Ubuntu 22.04
- **Python:** 3.10+
- **PyTorch version:** 2.4.x (release branch `release/2.4`)
- **Math backend:** Intel MKL
- **CUDA:** Disabled entirely (no CUDA/cuDNN/NCCL support)

### Build Configuration

The build must be configured as CPU-only with MKL. At minimum, the following constraints apply:
- CUDA support must be disabled.
- MKL must be the BLAS backend.
- The build must produce a pip-installable `.whl` file.

### Output Requirements

1. **Wheel file:** Place the built `.whl` file in `/app/dist/`. The filename must match the pattern `torch-2.4*.whl`.

2. **Validation report:** Write a JSON file to `/app/validation_report.json` with the following structure:

```json
{
  "wheel_path": "<relative path to .whl from /app/dist/>",
  "torch_version": "<installed torch version string>",
  "mkl_enabled": <true|false>,
  "cuda_available": <true|false>,
  "blas_info": "<output of torch.backends.mkl.is_available() or BLAS config string>",
  "tensor_test_passed": <true|false>,
  "matrix_mul_test_passed": <true|false>
}
```

Field definitions:
- `wheel_path`: The filename of the `.whl` file in `/app/dist/`.
- `torch_version`: The result of `torch.__version__` after installing the built wheel.
- `mkl_enabled`: `true` if `torch.backends.mkl.is_available()` returns `True`.
- `cuda_available`: Must be `false`. Result of `torch.cuda.is_available()`.
- `blas_info`: A string describing the BLAS backend in use (e.g., from `torch.__config__.show()`).
- `tensor_test_passed`: `true` if basic tensor creation and arithmetic (e.g., creating a tensor, addition, multiplication) succeed.
- `matrix_mul_test_passed`: `true` if a matrix multiplication of two 512x512 random float tensors completes without error and produces a result of shape (512, 512).

### Validation Criteria

After building and installing the wheel in a clean virtual environment:
- `torch.__version__` must start with `"2.4"`.
- `torch.backends.mkl.is_available()` must return `True`.
- `torch.cuda.is_available()` must return `False`.
- Basic tensor operations (creation, add, mul) must work correctly.
- Matrix multiplication of shape (512,512) x (512,512) must produce shape (512,512).
- All boolean fields in `validation_report.json` must reflect actual test results (not hardcoded).
