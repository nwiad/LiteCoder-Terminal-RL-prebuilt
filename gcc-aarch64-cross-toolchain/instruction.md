## GCC Cross-Compiler Toolchain for AArch64 Linux

Build a complete GCC-based cross-compiler toolchain that runs on x86_64 Linux and targets AArch64 (64-bit ARM) Linux systems, capable of producing statically-linked ELF binaries. Automate the entire process via a single build script.

### Technical Requirements

- **Host:** x86_64 Linux
- **Target triplet:** `aarch64-linux-gnu`
- **Installation prefix:** `/opt/cross-aarch64`
- **Build script:** `/app/build_toolchain.sh` — a self-contained Bash script that, when executed, performs all steps below from start to finish.

### Build Script Responsibilities

The script `/app/build_toolchain.sh` must perform the following in order:

1. **Prerequisites:** Install all host packages required to bootstrap the toolchain (e.g., build-essential, texinfo, bison, flex, etc.).

2. **Directory structure:** Create the following directories under the prefix:
   - `/opt/cross-aarch64/bin`
   - `/opt/cross-aarch64/lib`
   - `/opt/cross-aarch64/include`
   - `/opt/cross-aarch64/aarch64-linux-gnu`

3. **Source acquisition:** Download and extract upstream source tarballs for at least: binutils, gcc, glibc, linux kernel headers, and GCC prerequisite math libraries (GMP, MPFR, MPC, ISL). Symlink the math libraries into the GCC source tree.

4. **Cross-binutils:** Build and install binutils targeting `aarch64-linux-gnu` into the prefix. The following executables must exist after this step:
   - `/opt/cross-aarch64/bin/aarch64-linux-gnu-as`
   - `/opt/cross-aarch64/bin/aarch64-linux-gnu-ld`
   - `/opt/cross-aarch64/bin/aarch64-linux-gnu-objdump`

5. **Linux kernel headers:** Install AArch64 kernel headers into `/opt/cross-aarch64/aarch64-linux-gnu/include` (must contain `linux/` and `asm/` subdirectories).

6. **Stage-1 GCC:** Build and install a minimal (bootstrap) GCC that can compile C code for the target. Must produce:
   - `/opt/cross-aarch64/bin/aarch64-linux-gnu-gcc`

7. **glibc:** Build and install glibc for `aarch64-linux-gnu` into the sysroot. After installation:
   - `/opt/cross-aarch64/aarch64-linux-gnu/lib/libc.a` must exist.

8. **Stage-2 GCC:** Build and install the final GCC with at least C and C++ language support. Must produce:
   - `/opt/cross-aarch64/bin/aarch64-linux-gnu-gcc`
   - `/opt/cross-aarch64/bin/aarch64-linux-gnu-g++`

9. **Validation:** Compile a test program and verify the output:
   - Write a C source file `/app/hello.c` containing a minimal "Hello World" program that prints exactly `Hello, AArch64!` followed by a newline to stdout and returns 0.
   - Cross-compile it with static linking to produce `/app/hello_aarch64`.
   - `/app/hello_aarch64` must be a statically-linked ELF 64-bit LSB executable for ARM aarch64 (verified via `file` command).

### Output Artifacts

After successful execution of `/app/build_toolchain.sh`, the following must exist:

| Path | Description |
|---|---|
| `/opt/cross-aarch64/bin/aarch64-linux-gnu-gcc` | Cross GCC compiler |
| `/opt/cross-aarch64/bin/aarch64-linux-gnu-g++` | Cross G++ compiler |
| `/opt/cross-aarch64/bin/aarch64-linux-gnu-as` | Cross assembler |
| `/opt/cross-aarch64/bin/aarch64-linux-gnu-ld` | Cross linker |
| `/opt/cross-aarch64/bin/aarch64-linux-gnu-objdump` | Cross objdump |
| `/opt/cross-aarch64/aarch64-linux-gnu/lib/libc.a` | Static C library for target |
| `/opt/cross-aarch64/aarch64-linux-gnu/include/linux/` | Kernel headers directory |
| `/opt/cross-aarch64/aarch64-linux-gnu/include/asm/` | Arch-specific kernel headers |
| `/app/hello.c` | Test C source file |
| `/app/hello_aarch64` | Statically-linked AArch64 ELF binary |

### Validation Criteria

- `file /app/hello_aarch64` output must contain: `ELF 64-bit LSB`, `ARM aarch64`, and `statically linked`.
- `aarch64-linux-gnu-gcc --version` must execute successfully and print a GCC version string.
- `aarch64-linux-gnu-g++ --version` must execute successfully.
