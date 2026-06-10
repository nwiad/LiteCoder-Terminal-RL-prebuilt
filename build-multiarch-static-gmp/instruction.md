## Build a Multi-Architecture Static GMP Library with GCC Optimization

Build GMP 6.3.0 from source for x86_64 (native) and aarch64 (cross-compiled) into static, position-independent archives with aggressive optimization and hardening flags. Produce a structured JSON test report and a final distribution tarball.

### Technical Requirements

- Language/Tools: Bash, GCC, Make, aarch64-linux-gnu cross-compilation toolchain
- GMP version: 6.3.0 (download from https://gmplib.org/download/gmp/gmp-6.3.0.tar.xz)
- All work rooted under `/app`

### Directory Layout

Create the following directory structure before building:

```
/app/builds/x86_64/src/
/app/builds/x86_64/build/
/app/builds/x86_64/dist/
/app/builds/aarch64/src/
/app/builds/aarch64/build/
/app/builds/aarch64/dist/
```

Each architecture's GMP source should be extracted into its respective `src/` directory, configured and built in `build/`, and installed into `dist/`.

### Build Specifications

**x86_64 (native) build:**
- Configure with `--enable-fat` for multi-microarchitecture support
- Must produce a static library only (`--disable-shared --enable-static`)
- CFLAGS must include at minimum: `-fPIC`, `-O2`, `-fstack-protector-strong`, `-D_FORTIFY_SOURCE=2`
- Install prefix: `/app/builds/x86_64/dist`

**aarch64 (cross-compiled) build:**
- Use `aarch64-linux-gnu-gcc` as the cross compiler
- Host triplet: `aarch64-linux-gnu`
- Must produce a static library only (`--disable-shared --enable-static`)
- CFLAGS must include at minimum: `-fPIC`, `-O2`, `-mtune=cortex-a72`, `-fstack-protector-strong`, `-D_FORTIFY_SOURCE=2`
- Install prefix: `/app/builds/aarch64/dist`

### Test Execution

- Run `make check` for the x86_64 build and capture the full console output to `/app/builds/x86_64/test.log`
- For aarch64, since tests cannot run natively on x86_64, run `make check` if QEMU user-mode emulation is available; otherwise skip and note it in the report. Save any output to `/app/builds/aarch64/test.log` (create an empty file if skipped).

### Output Files

**1. Static libraries:**
- `/app/builds/x86_64/dist/lib/libgmp.a`
- `/app/builds/aarch64/dist/lib/libgmp.a`

**2. JSON test report at `/app/report.json`:**

The report must be a JSON object with the following structure:

```json
{
  "gmp_version": "6.3.0",
  "architectures": [
    {
      "arch": "x86_64",
      "compiler": "<gcc version string>",
      "cflags": "<actual CFLAGS used>",
      "configure_options": "<configure command line flags>",
      "library_path": "/app/builds/x86_64/dist/lib/libgmp.a",
      "tests_run": true,
      "test_summary": {
        "total": <int>,
        "passed": <int>,
        "failed": <int>
      }
    },
    {
      "arch": "aarch64",
      "compiler": "<cross-compiler version string>",
      "cflags": "<actual CFLAGS used>",
      "configure_options": "<configure command line flags>",
      "library_path": "/app/builds/aarch64/dist/lib/libgmp.a",
      "tests_run": <true|false>,
      "test_summary": {
        "total": <int>,
        "passed": <int>,
        "failed": <int>
      }
    }
  ]
}
```

- `test_summary.total`, `passed`, `failed` must be integers. If tests were not run, set all to `0`.
- `tests_run` is a boolean indicating whether `make check` was executed for that architecture.

**3. Distribution tarball at `/app/gmp-6.3.0-multiarch-optimized.tar.gz`:**

Must contain:
- Both `libgmp.a` files (preserving the per-architecture directory structure under `builds/`)
- The `report.json` file
- Both `test.log` files

The tarball should be created from `/app` so paths inside are relative (e.g., `builds/x86_64/dist/lib/libgmp.a`).
