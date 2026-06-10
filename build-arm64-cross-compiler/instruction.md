## Cross-Compiler Construction for ARM64

Build a self-contained, statically-linked cross-compiler toolchain that targets ARM64 (aarch64-linux-gnu) from an x86_64 Linux host. The toolchain must include binutils, a two-stage GCC (C and C++), and musl libc, and must be packaged as a redistributable tarball.

### Technical Requirements

- **Host:** x86_64 Linux (Debian/Ubuntu-based, apt available)
- **Target triple:** `aarch64-linux-gnu`
- **Source versions:** binutils 2.40, GCC 13.2.0, musl 1.2.5
- **Install prefix:** `/opt/cross-arm64`
- **All toolchain binaries must be statically linked** (no dynamic library dependencies)

### Build Steps

1. Install all necessary host build dependencies via `apt`.
2. Download source tarballs for binutils-2.40, gcc-13.2.0, and musl-1.2.5.
3. Build binutils targeting `aarch64-linux-gnu`, installed to `/opt/cross-arm64`.
4. Build GCC stage1 (C-only, no shared libs) using the new binutils, installed to `/opt/cross-arm64`.
5. Build musl libc for aarch64 using the stage1 compiler, installed to `/opt/cross-arm64/aarch64-linux-gnu`.
6. Build GCC stage2 (C and C++ enabled) linked against the musl headers and libraries, installed to `/opt/cross-arm64`.
7. Compile and link a minimal "Hello, World!" C program and a minimal "Hello, World!" C++ program using the final toolchain. Place the resulting binaries at `/app/hello_c` and `/app/hello_cpp`.
8. Package the entire `/opt/cross-arm64` directory into a tarball at `/app/cross-arm64-toolchain.tar.gz`.
9. Remove intermediate build directories to minimize disk usage.

### Output Specifications

The following files must exist after completion:

| Path | Description |
|---|---|
| `/opt/cross-arm64/bin/aarch64-linux-gnu-gcc` | Stage2 GCC C compiler binary |
| `/opt/cross-arm64/bin/aarch64-linux-gnu-g++` | Stage2 GCC C++ compiler binary |
| `/opt/cross-arm64/bin/aarch64-linux-gnu-as` | Assembler from binutils |
| `/opt/cross-arm64/bin/aarch64-linux-gnu-ld` | Linker from binutils |
| `/opt/cross-arm64/bin/aarch64-linux-gnu-ar` | Archiver from binutils |
| `/opt/cross-arm64/aarch64-linux-gnu/lib/libc.a` | musl static C library |
| `/app/hello_c` | Statically-linked ARM64 ELF "Hello, World!" C binary |
| `/app/hello_cpp` | Statically-linked ARM64 ELF "Hello, World!" C++ binary |
| `/app/cross-arm64-toolchain.tar.gz` | Tarball of the complete toolchain |

### Verification Criteria

- Every binary under `/opt/cross-arm64/bin/` must be a statically-linked x86_64 ELF executable (i.e., `file` reports "statically linked" and `ldd` reports "not a dynamic executable").
- `/app/hello_c` and `/app/hello_cpp` must be statically-linked ELF executables for ARM64 (`ELF 64-bit LSB executable, ARM aarch64`).
- `/opt/cross-arm64/bin/aarch64-linux-gnu-gcc -v` must report version `13.2.0` and target `aarch64-linux-gnu`.
- `/app/cross-arm64-toolchain.tar.gz` must be a valid gzip-compressed tar archive containing the `/opt/cross-arm64` tree.
- `musl-gcc` or the stage2 compiler must be able to produce static aarch64 binaries using musl as the C library.
