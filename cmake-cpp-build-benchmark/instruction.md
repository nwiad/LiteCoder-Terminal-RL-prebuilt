## Build, Test, and Benchmark a C++ Project Using CMake and Make

Set up a CMake-based C++ project, build it with optimized flags, validate the build, benchmark compilation performance, and generate a structured build report.

### Technical Requirements

- Language: C++17 (or later), CMake (3.10+), Make or Ninja
- Working directory: /app
- Output report: /app/build_report.json

### Task Steps

1. **Create a C++ project under `/app/src/`** with the following source files:

   - `main.cpp`: A program that accepts a single command-line argument (an integer N), computes the sum of integers from 1 to N using a function defined in `mathlib.h`/`mathlib.cpp`, and prints the result to stdout in the format: `Sum(1..N) = <result>` (e.g., `Sum(1..100) = 5050`).
   - `mathlib.h` / `mathlib.cpp`: A small math library that provides at minimum:
     - `long long computeSum(int n)` — returns the sum of integers from 1 to n.
     - `bool isPrime(int n)` — returns whether n is prime.
   - `test_mathlib.cpp`: A test executable that tests `computeSum` and `isPrime` with at least 3 test cases each. It must print `ALL TESTS PASSED` to stdout if all tests pass, or print which test failed and exit with a non-zero exit code.

2. **Create a `CMakeLists.txt` in `/app/`** that:
   - Sets the project name to `CompilerBenchmark`.
   - Requires C++17 standard.
   - Builds two targets:
     - An executable named `benchmark_app` from `main.cpp` and `mathlib.cpp`.
     - An executable named `test_mathlib` from `test_mathlib.cpp` and `mathlib.cpp`.
   - Supports a `Release` build type with `-O2` optimization flag.

3. **Build the project** in a build directory at `/app/build/` using CMake with `Release` build type. Both `benchmark_app` and `test_mathlib` executables must be successfully compiled and present under `/app/build/`.

4. **Run validation**:
   - Execute `test_mathlib` and confirm all tests pass.
   - Execute `benchmark_app 100` and confirm the output is `Sum(1..100) = 5050`.

5. **Benchmark compilation**: Measure the wall-clock time (in seconds) it takes to perform a clean rebuild of the project (i.e., remove build artifacts, then rebuild from scratch).

6. **Generate `/app/build_report.json`** with the following exact JSON structure:

```json
{
  "project_name": "CompilerBenchmark",
  "compiler": "<compiler name and version, e.g. g++ 11.4.0>",
  "cpp_standard": "C++17",
  "build_type": "Release",
  "optimization_flags": "-O2",
  "targets": [
    {
      "name": "benchmark_app",
      "type": "executable",
      "sources": ["main.cpp", "mathlib.cpp"]
    },
    {
      "name": "test_mathlib",
      "type": "executable",
      "sources": ["test_mathlib.cpp", "mathlib.cpp"]
    }
  ],
  "test_results": {
    "total": <int>,
    "passed": <int>,
    "failed": <int>,
    "status": "PASSED" or "FAILED"
  },
  "benchmark_app_output": "Sum(1..100) = 5050",
  "rebuild_time_seconds": <float>,
  "build_directory": "/app/build"
}
```

All fields are required. The `compiler` field must reflect the actual compiler used. The `rebuild_time_seconds` must be a positive number reflecting the actual measured time.
