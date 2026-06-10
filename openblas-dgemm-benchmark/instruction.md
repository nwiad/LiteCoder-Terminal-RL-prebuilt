Build OpenBLAS from source with dynamic architecture support (`DYNAMIC_ARCH=1`) and benchmark DGEMM (double-precision general matrix multiply) performance across multiple thread counts. Produce structured results documenting the build configuration and benchmark data.

## Technical Requirements

- Language: C for benchmark/test programs, shell for build orchestration
- OpenBLAS must be cloned from the official GitHub repository: `https://github.com/OpenMathLib/OpenBLAS.git`
- Build with `DYNAMIC_ARCH=1` and `NO_LAPACK=0`
- Install the library system-wide (default prefix `/opt/OpenBLAS` or `/usr/local`)

## Build and Installation

1. Install all required build dependencies (gcc/gfortran, make, git, etc.).
2. Clone the OpenBLAS repository into `/app/OpenBLAS`.
3. Build OpenBLAS with at minimum these flags: `DYNAMIC_ARCH=1`, `NUM_THREADS=8`.
4. Install the built library so that `libopenblas.so` (or `.a`) is available in the installed lib directory.

After installation, the following must exist:
- The shared library file `libopenblas.so` (or `libopenblas.a`) under the install prefix lib directory
- The header file `cblas.h` under the install prefix include directory

## Benchmark Program

Create a C benchmark program at `/app/benchmark_dgemm.c` that:
- Links against the built OpenBLAS library
- Performs DGEMM (C = alpha*A*B + beta*C) using the `cblas_dgemm` function
- Tests matrix sizes: 256, 512, 1024, 2048
- For each matrix size, measures wall-clock execution time in seconds (use `gettimeofday` or `clock_gettime`)
- Computes GFLOPS as: `(2.0 * N * N * N) / (time_in_seconds * 1e9)`
- Initializes matrices with random double-precision values

Compile the benchmark to `/app/benchmark_dgemm`.

## Verification Test

Create a C test program at `/app/test_openblas.c` that:
- Calls `openblas_get_config()` to retrieve the build configuration string
- Calls `openblas_get_num_threads()` to confirm threading support
- Performs a small 4x4 DGEMM and verifies the result is numerically correct (absolute error < 1e-10 for each element)
- Prints "PASS" to stdout if all checks succeed, or "FAIL" with a description if any check fails
- Exits with code 0 on success, non-zero on failure

Compile the test to `/app/test_openblas`.

## Benchmark Execution

Run the benchmark for each of the following thread counts: 1, 2, 4, 8 (set via `OPENBLAS_NUM_THREADS` environment variable). Collect results for all matrix sizes at each thread count.

## Output Files

### /app/build_config.json

A JSON file documenting the build, with this structure:

```json
{
  "repository_url": "https://github.com/OpenMathLib/OpenBLAS.git",
  "build_flags": {
    "DYNAMIC_ARCH": 1,
    "NUM_THREADS": 8,
    "NO_LAPACK": 0
  },
  "install_prefix": "<path where OpenBLAS was installed>",
  "openblas_config": "<output of openblas_get_config()>",
  "library_path": "<full path to libopenblas.so or .a>",
  "include_path": "<full path to cblas.h>"
}
```

All values must be strings or numbers (no nulls).

### /app/benchmark_results.json

A JSON file with benchmark data in this exact structure:

```json
{
  "matrix_sizes": [256, 512, 1024, 2048],
  "thread_counts": [1, 2, 4, 8],
  "results": [
    {
      "threads": 1,
      "benchmarks": [
        {
          "matrix_size": 256,
          "time_seconds": <float>,
          "gflops": <float>
        },
        {
          "matrix_size": 512,
          "time_seconds": <float>,
          "gflops": <float>
        },
        {
          "matrix_size": 1024,
          "time_seconds": <float>,
          "gflops": <float>
        },
        {
          "matrix_size": 2048,
          "time_seconds": <float>,
          "gflops": <float>
        }
      ]
    }
  ]
}
```

- `results` must contain exactly 4 entries (one per thread count), each with exactly 4 benchmark entries.
- All `time_seconds` values must be positive floats.
- All `gflops` values must be positive floats.
- The `matrix_sizes` and `thread_counts` arrays must match the values used in `results`.

### /app/test_result.txt

Capture the stdout of running `/app/test_openblas` into this file. It must contain the string "PASS" if all verification checks succeeded.
