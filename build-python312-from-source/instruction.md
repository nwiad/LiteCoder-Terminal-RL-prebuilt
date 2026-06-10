## Building a Custom Python 3.12 Interpreter from Source with Full Optimization

Compile Python 3.12.0 from source on Ubuntu with profile-guided optimization (PGO) and link-time optimization (LTO), install it to a custom prefix, and produce a build report.

### Technical Requirements

- **OS:** Ubuntu (current environment)
- **Python version:** 3.12.0 (official CPython source tarball from https://www.python.org/ftp/python/3.12.0/Python-3.12.0.tgz)
- **Install prefix:** `/opt/python312`
- **Report file:** `/app/build_report.json`
- **Benchmark output:** `/app/benchmark_result.json`

### Build Requirements

1. Install all necessary build dependencies for compiling CPython from source (including SSL, zlib, libffi, readline, sqlite, bzip2, lzma, etc.).
2. Download the official Python 3.12.0 source tarball and extract it.
3. Configure the build with the following optimizations enabled:
   - Profile-guided optimization (PGO) via `--enable-optimizations`
   - Link-time optimization (LTO) via `--with-lto`
   - Install prefix set to `/opt/python312`
4. Compile using all available CPU cores.
5. Install the built interpreter to `/opt/python312`.

### Installation Verification

After installation, the following must be true:

- `/opt/python312/bin/python3.12` exists and is executable.
- `/opt/python312/bin/python3.12 --version` outputs a string containing `3.12.0`.
- `/opt/python312/bin/pip3.12` exists and is executable (ensurepip must work).
- `/opt/python312/lib/python3.12/` directory exists and contains standard library modules.

### Symbolic Links

Create the following symbolic links:

- `/usr/local/bin/python3.12` → `/opt/python312/bin/python3.12`
- `/usr/local/bin/pip3.12` → `/opt/python312/bin/pip3.12`

### Build Report (`/app/build_report.json`)

Generate a JSON file with the following structure:

```json
{
  "python_version": "<output of python3.12 --version>",
  "install_prefix": "/opt/python312",
  "binary_path": "/opt/python312/bin/python3.12",
  "optimizations": {
    "pgo": true,
    "lto": true
  },
  "build_config": "<output of python3.12 -c \"import sysconfig; print(sysconfig.get_config_var('CONFIG_ARGS'))\">",
  "ssl_support": "<true if 'import ssl' succeeds, false otherwise>",
  "sqlite_support": "<true if 'import sqlite3' succeeds, false otherwise>",
  "ctypes_support": "<true if 'import ctypes' succeeds, false otherwise>",
  "lzma_support": "<true if 'import lzma' succeeds, false otherwise>"
}
```

- `optimizations.pgo` must be `true` (the `build_config` string must contain `--enable-optimizations`).
- `optimizations.lto` must be `true` (the `build_config` string must contain `--with-lto`).
- `ssl_support`, `sqlite_support`, `ctypes_support`, and `lzma_support` should all be `true`.
- All values for boolean fields must be JSON booleans (`true`/`false`), not strings.

### Benchmark (`/app/benchmark_result.json`)

Write a Python benchmark script and run it with the newly built interpreter. The benchmark must:

1. Measure execution time (in seconds) of a CPU-bound task (e.g., computing Fibonacci, prime sieve, or similar).
2. Run the same task using both the system default `python3` (if available) and `/opt/python312/bin/python3.12`.
3. Output results to `/app/benchmark_result.json` with this structure:

```json
{
  "task_name": "<name of the benchmark task>",
  "custom_python": {
    "binary": "/opt/python312/bin/python3.12",
    "time_seconds": <float>
  },
  "system_python": {
    "binary": "<path to system python3>",
    "time_seconds": <float>
  }
}
```

- If system `python3` is not available, set `system_python` to `null`.
- `time_seconds` values must be positive floats.
