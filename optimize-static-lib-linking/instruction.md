## Custom Static Library Linking Optimization

Build a C static library with optimized compiler/linker flags and controlled symbol visibility, then link it into a benchmark program.

### Technical Requirements

- Language: C (compiled with GCC)
- Build system: GNU Make
- Working directory: `/app`

### Project Structure

Create the following files under `/app`:

- `mathlib.h` — Public API header
- `mathlib.c` — Library implementation (public + internal functions)
- `benchmark.c` — Benchmark program that exercises the library
- `Makefile` — Build system with two build targets

### Library API (`mathlib.h` / `mathlib.c`)

The library must implement these public functions with the following exact signatures:

```c
double fast_sqrt(double x);
double fast_pow(double base, int exp);
double fast_sin(double x);
double dot_product(const double *a, const double *b, int n);
double matrix_trace(const double *matrix, int n);
```

The library must also contain at least two internal helper functions that are **not** declared in `mathlib.h`. These internal functions must be marked with `__attribute__((visibility("hidden")))` so they do not appear as external (T) symbols in the final library.

All public functions listed in `mathlib.h` must remain visible as external symbols.

### Makefile Requirements

The Makefile must support the following targets:

1. `make optimized` — Builds the static library `libmathopt.a` and the benchmark binary `benchmark_opt` with these flags:
   - `-O3` optimization level
   - `-flto` (link-time optimization)
   - `-fvisibility=hidden` as the default visibility
   - Public API functions must override the default hidden visibility using `__attribute__((visibility("default")))` so they remain exported.

2. `make unoptimized` — Builds the static library `libmathnoop.a` and the benchmark binary `benchmark_noop` with:
   - `-O0` optimization level
   - No LTO
   - No visibility restrictions

3. `make all` — Builds both optimized and unoptimized targets.

4. `make clean` — Removes all generated `.o`, `.a`, and binary files.

The static libraries must be created using `ar rcs`.

### Benchmark Program (`benchmark.c`)

The benchmark program must:

- Include `mathlib.h` and call every public library function at least once.
- Run each function in a loop of at least 1,000,000 iterations for timing.
- Measure wall-clock time for each function's loop using `clock_gettime(CLOCK_MONOTONIC)` or equivalent.
- Print results to stdout, one line per function, in this exact format:

```
fast_sqrt: <time_in_seconds>s
fast_pow: <time_in_seconds>s
fast_sin: <time_in_seconds>s
dot_product: <time_in_seconds>s
matrix_trace: <time_in_seconds>s
```

Where `<time_in_seconds>` is a floating-point number (e.g., `0.045123`).

### Symbol Visibility Verification

After building the optimized library (`libmathopt.a`), running:

```
nm libmathopt.a | grep " T "
```

must list the five public functions (`fast_sqrt`, `fast_pow`, `fast_sin`, `dot_product`, `matrix_trace`) as text (T) symbols. The internal helper functions must **not** appear as `T` symbols in this output (they should appear as `t` or not at all).

### Output

After `make all` completes successfully, the following files must exist under `/app`:

- `libmathopt.a`
- `libmathnoop.a`
- `benchmark_opt`
- `benchmark_noop`

Both benchmark binaries must execute without errors and print the timing output described above.
