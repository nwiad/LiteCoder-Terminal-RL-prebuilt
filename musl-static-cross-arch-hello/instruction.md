## Build a Cross-Architecture Static Hello-World with musl

Compile a fully static x86_64 and aarch64 "hello world" C program using musl libc on an x86_64 host, so both binaries can run on bare Linux kernels without any shared libraries.

### Technical Requirements

- Language: C
- Host architecture: x86_64
- Target architectures: x86_64 and aarch64 (ARM64)
- Libc: musl (not glibc)
- Linking: 100% static (no dynamic dependencies)
- Working directory: `/app`

### Source File

Create a C source file at `/app/hello.c` that:
- Prints exactly `Hello, World!` followed by a newline to stdout
- Returns exit code 0

### Output Binaries

1. `/app/hello-x86_64` — statically linked x86_64 ELF binary compiled with musl
2. `/app/hello-aarch64` — statically linked aarch64 ELF binary compiled with musl (cross-compiled from x86_64 host)

### Toolchain Setup

- Install a native musl toolchain for x86_64 (e.g., `musl-tools` or equivalent)
- Install a musl-based cross-compiler toolchain capable of producing aarch64 binaries (e.g., `aarch64-linux-musl-gcc` or equivalent)

### Verification Criteria

1. Both binaries must be ELF executables for their respective architectures:
   - `file /app/hello-x86_64` must indicate `ELF 64-bit LSB` and `x86-64`
   - `file /app/hello-aarch64` must indicate `ELF 64-bit LSB` and `ARM aarch64`

2. Both binaries must be statically linked:
   - `file` output for each binary must contain `statically linked`
   - `ldd` on each binary must report `not a dynamic executable` (or equivalent)

3. The x86_64 binary must execute correctly on the host and produce exactly:
   ```
   Hello, World!
   ```

4. Both binaries must be smaller than 100 KB each in file size.
