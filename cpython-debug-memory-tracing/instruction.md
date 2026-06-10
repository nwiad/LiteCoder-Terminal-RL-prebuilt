## Custom Debug Version of Python with Memory Tracing

Build a custom debug version of CPython 3.11.9 with a memory-tracing patch that logs every raw memory allocation and deallocation to a file.

### Technical Requirements

- **Language/Tools:** C (patch), Shell/Makefile (build pipeline), Python (verification)
- **CPython Version:** 3.11.9 (download the official source tarball from https://www.python.org/ftp/python/3.11.9/Python-3.11.9.tgz)
- **Install Prefix:** `/opt/pydebug`
- **Build Dependencies:** gcc, make, libffi-dev, zlib1g-dev, libssl-dev, libbz2-dev, libreadline-dev, libsqlite3-dev, wget, patch

### Build Configuration

Configure CPython with the following exact options:

- `--prefix=/opt/pydebug`
- `--with-pydebug`
- `--without-pymalloc`
- `CFLAGS="-O0 -g3 -DDEBUG_TRACING"`

Build and install the interpreter so that `/opt/pydebug/bin/python3` is a working executable.

### Memory-Tracing Patch

Create and apply a patch to the CPython source tree that intercepts the raw memory allocator (`PyMem_RawMalloc` and `PyMem_RawFree`). The patch must satisfy:

1. **Log file path:** `/tmp/memtrace.log`
2. **Log format:** Each line must contain at least:
   - A timestamp (any reasonable format, e.g., seconds since epoch with fractional part)
   - The operation type: the string `malloc` for allocations, `free` for deallocations
   - The size of the allocation (for `malloc` lines)
   - The pointer address (hex format)
3. **One log line per operation:** Each `PyMem_RawMalloc` call produces exactly one line containing `malloc`; each `PyMem_RawFree` call produces exactly one line containing `free`.
4. The patch file must be saved at `/app/memtrace.patch` before being applied.

### Verification

After building and installing, run the following Python snippet using the custom interpreter at `/opt/pydebug/bin/python3`:

```python
import ctypes, os
libc = ctypes.CDLL(None)
for _ in range(10):
    p = libc.malloc(1024)
    libc.free(p)
```

After execution:

- `/tmp/memtrace.log` must exist and be non-empty.
- The log must contain lines with `malloc` and lines with `free`.
- The total number of log lines must be **at least 20** (at least 10 `malloc` + 10 `free` entries; more is acceptable since the interpreter itself performs allocations).

### Output Artifacts

| Artifact | Path |
|---|---|
| Memory-tracing patch | `/app/memtrace.patch` |
| Custom Python interpreter | `/opt/pydebug/bin/python3` |
| Memory trace log | `/tmp/memtrace.log` |
