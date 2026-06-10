## Create a Custom Memory-Tracking Shared Library

Create a memory-tracking shared library for C programs that intercepts `malloc` and `free` calls via `LD_PRELOAD`, logging all allocations and deallocations to a file.

### Technical Requirements

- Language: C (compiled with GCC)
- Working directory: `/app`

### Files to Create

1. `/app/memtracker.c` — Source file for the shared library that wraps `malloc` and `free`.
2. `/app/Makefile` — Builds the shared library and the test program.
3. `/app/test_program.c` — A simple C program that performs memory allocations and deallocations for testing.

### Build Requirements

- The Makefile must have a default target (invoked via `make`) that produces:
  - `/app/libmemtracker.so` — the shared library (compiled with `-shared`, `-fPIC`, and linked with `-ldl`).
  - `/app/test_program` — the compiled test program.
- Running `make clean` must remove all generated `.so`, `.o`, and executable files.

### Memory Tracker Library (`memtracker.c`) Specifications

- The library must intercept `malloc` and `free` by defining wrapper functions that use `dlsym` with `RTLD_NEXT` to call the real implementations.
- All log output must be written to the file specified by the environment variable `MEMTRACKER_LOG`. If `MEMTRACKER_LOG` is not set, log to `/app/memtrack.log` by default.
- Each `malloc` call must produce a log line in the following exact format:
  ```
  [MALLOC] size=<bytes> ptr=<address>
  ```
  where `<bytes>` is the requested allocation size (as a decimal integer) and `<address>` is the returned pointer (in `0x` hex format, e.g., `0x55a3bc001260`).
- Each `free` call must produce a log line in the following exact format:
  ```
  [FREE] ptr=<address>
  ```
  where `<address>` is the pointer being freed (in `0x` hex format). If `NULL` is passed to `free`, log `ptr=0x0` or `ptr=(nil)`.
- Each log line must be on its own line (terminated by `\n`).
- The log file must be opened in append mode so multiple runs accumulate.

### Test Program (`test_program.c`) Specifications

- The test program must perform at least:
  - 3 separate `malloc` calls with different sizes (e.g., 32, 64, 128 bytes).
  - Corresponding `free` calls for each allocation.
- The program must print `"Test program completed."` to stdout before exiting with code 0.

### Testing Procedure

Running the following commands from `/app` must work:

```
make
MEMTRACKER_LOG=/app/memtrack.log LD_PRELOAD=./libmemtracker.so ./test_program
```

After execution, `/app/memtrack.log` must:
- Contain at least 3 lines matching the pattern `[MALLOC] size=<N> ptr=0x...`
- Contain at least 3 lines matching the pattern `[FREE] ptr=0x...`
- Have `[MALLOC]` lines appear before their corresponding `[FREE]` lines for the same pointer address
