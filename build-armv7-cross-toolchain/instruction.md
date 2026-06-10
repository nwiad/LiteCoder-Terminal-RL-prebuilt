## Cross-Compilation Toolchain Construction

Build a complete cross-compilation toolchain targeting ARMv7 from an x86_64 host using crosstool-NG, validate it by cross-compiling a test program, and package everything for distribution.

### Technical Requirements

- **Host:** x86_64 Linux (Ubuntu-based)
- **Tool:** crosstool-NG (latest stable release)
- **Target architecture:** ARMv7 (arm-unknown-linux-gnueabi or similar arm eabi triplet)
- **Toolchain install prefix:** `/opt/armv7-toolchain`
- **Language:** Shell script (Bash) for automation; C for the test program

### Deliverables

All deliverables must exist at the specified paths upon completion.

1. **Automation script:** `/app/build_toolchain.sh`
   - A single executable Bash script that, when run on a fresh Ubuntu image, reproducibly performs the full toolchain build.
   - Must install all required build-time dependencies for crosstool-NG.
   - Must fetch the crosstool-NG release tarball, verify its SHA256 checksum, and unpack it.
   - Must configure crosstool-NG for an ARMv7 eabi target with recent stable component versions (GCC, glibc, binutils, Linux headers).
   - Must build the toolchain non-interactively and install it into `/opt/armv7-toolchain`.
   - Must clean up build artifacts outside `/opt/armv7-toolchain` after the build completes.
   - The script must be executable (`chmod +x`).

2. **Toolchain directory:** `/opt/armv7-toolchain`
   - Must contain a `bin/` subdirectory with cross-compiler binaries (e.g., `arm-*-gcc`, `arm-*-g++`, `arm-*-ld`).
   - The cross-compiler binaries must be functional and target ARM.

3. **Test C source:** `/app/hello_arm.c`
   - A simple C program that prints exactly `Hello, ARM` (followed by a newline) to stdout and exits with code 0.

4. **Compiled test binary:** `/app/hello_arm`
   - Produced by cross-compiling `/app/hello_arm.c` using the built toolchain.
   - Must be statically linked (`-static`).
   - Must be an ELF binary for ARM architecture (ELF 32-bit LSB executable, ARM, EABI5 or similar).
   - `file /app/hello_arm` must contain the string `ARM`.
   - `readelf -h /app/hello_arm` must show `Machine:` as `ARM`.

5. **ELF inspection report:** `/app/elf_report.txt`
   - Contains the output of `readelf -h /app/hello_arm`.
   - Must include lines showing the ELF is for ARM architecture and is a statically linked executable.

6. **Distribution tarball:** `/app/armv7-toolchain.tar.gz`
   - A gzip-compressed tar archive of the entire `/opt/armv7-toolchain` directory.
   - Must be extractable with `tar xzf /app/armv7-toolchain.tar.gz`.
   - When extracted, must reproduce the toolchain directory structure with `bin/` containing the cross-compiler binaries.

7. **CI one-liner:** `/app/ci_command.txt`
   - A single-line shell command that a teammate can run to reproduce the exact toolchain build from scratch.
   - Must reference `/app/build_toolchain.sh`.

### Verification Criteria

- `/opt/armv7-toolchain/bin/` contains at least one executable matching the glob pattern `arm-*-gcc`.
- `/app/hello_arm` exists, is an ELF binary, and `file /app/hello_arm` output contains `ARM`.
- `/app/hello_arm` is statically linked (verified via `file` output containing `statically linked`).
- `/app/elf_report.txt` exists and contains the string `ARM` in the Machine field.
- `/app/armv7-toolchain.tar.gz` exists and is a valid gzip archive.
- `/app/build_toolchain.sh` exists and is executable.
- `/app/ci_command.txt` exists and is non-empty.
- `/app/hello_arm.c` exists and contains a `main` function that prints `Hello, ARM`.
