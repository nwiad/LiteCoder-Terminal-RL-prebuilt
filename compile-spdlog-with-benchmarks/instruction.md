## Compile C++ Logger Library (spdlog) with Benchmarks

Clone and compile the spdlog C++ logging library (version 1.15.3) from GitHub, producing optimized shared libraries and benchmark executables. Then create a test program that links against the compiled library, and generate a build summary report.

### Technical Requirements

- Language/Tools: C++, CMake, Make/Ninja
- Working directory: /app
- Clone spdlog v1.15.3 from https://github.com/gabime/spdlog.git into `/app/spdlog`
- Build directory: `/app/spdlog/build`
- Install prefix: `/app/spdlog/install`

### Build Configuration

Configure CMake with the following options:
- `CMAKE_BUILD_TYPE=Release`
- `SPDLOG_BUILD_SHARED=ON` (produce shared `.so` libraries)
- `SPDLOG_BUILD_BENCH=ON` (compile benchmark executables)
- `SPDLOG_BUILD_EXAMPLE=OFF`
- `CMAKE_INSTALL_PREFIX=/app/spdlog/install`

Run `make install` (or equivalent) after compilation so headers and libraries are placed under the install prefix.

### Expected Build Artifacts

After a successful build and install, the following must exist:

1. Shared library: at least one `.so` file under `/app/spdlog/install/lib/` (e.g., `libspdlog.so`)
2. Header files: `/app/spdlog/install/include/spdlog/spdlog.h`
3. Benchmark executables: at least one executable file under `/app/spdlog/build/bench/`

### Test Program

Create a file `/app/test_spdlog.cpp` that:
- Includes `<spdlog/spdlog.h>`
- Calls `spdlog::info(...)` to log a message containing the string `"spdlog test passed"`
- Returns exit code 0 on success

Compile this test program, linking it against the shared library installed in `/app/spdlog/install`. The compiled executable must be placed at `/app/test_spdlog`. Running `/app/test_spdlog` must produce output on stdout or stderr containing the substring `spdlog test passed`.

### Build Summary Report

Generate a JSON file at `/app/build_report.json` with the following structure:

```json
{
  "spdlog_version": "1.15.3",
  "build_type": "Release",
  "shared_libs": ["<relative path from /app/spdlog/install/lib/ for each .so file found>"],
  "benchmark_executables": ["<relative path from /app/spdlog/build/bench/ for each benchmark executable found>"],
  "install_prefix": "/app/spdlog/install",
  "test_program_compiled": true
}
```

- `shared_libs`: array of `.so` filenames (not full paths) found under the install lib directory.
- `benchmark_executables`: array of executable filenames (not full paths) found under the build bench directory.
- `test_program_compiled`: boolean, `true` if `/app/test_spdlog` exists and is executable.
