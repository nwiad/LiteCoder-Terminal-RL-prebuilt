## Cross-Compilation Toolchain Setup for RISC-V

Create a shell-based build system that automates the construction of a complete GCC cross-compilation toolchain for RISC-V, targeting both 32-bit (rv32imac) and 64-bit (rv64imac) architectures. The system must produce a self-contained, versioned toolchain capable of generating static and dynamically linked ELF binaries.

### Technical Requirements

- Language: Bash (POSIX-compatible shell scripts)
- Working directory: `/app`
- All scripts must be executable (`chmod +x`)

### Deliverables

1. **`/app/build_toolchain.sh`** — The main orchestrator script that drives the entire build process end-to-end. It must:
   - Accept exactly two command-line arguments:
     - `--prefix=<PATH>`: installation directory for the toolchain (e.g., `--prefix=/opt/riscv-toolchain-1.0`)
     - `--version=<VERSION>`: version label string (e.g., `--version=1.0`)
   - Print usage and exit with code 1 if arguments are missing or malformed.
   - Define and use the following shell variables (at minimum):
     - `INSTALL_DIR` — resolved from `--prefix`
     - `TOOLCHAIN_VERSION` — resolved from `--version`
     - `RISCV32_TARGET` set to `riscv32-unknown-linux-gnu`
     - `RISCV64_TARGET` set to `riscv64-unknown-linux-gnu`
     - `BUILD_DIR` — a temporary build directory under `/app`
   - Source (`.` or `source`) each of the phase scripts below in order.
   - Exit with code 0 on success.

2. **`/app/scripts/01_install_deps.sh`** — Install host build dependencies. Must contain commands (or clearly structured package lists) to install at least: `build-essential`, `bison`, `flex`, `texinfo`, `libgmp-dev`, `libmpfr-dev`, `libmpc-dev`, `libisl-dev`, `libexpat-dev`, `wget`, `git`.

3. **`/app/scripts/02_download_sources.sh`** — Download pristine upstream sources. Must:
   - Define download URLs for at least these components: `binutils`, `gcc`, `glibc`, `linux` (kernel headers), `gdb`.
   - Download each into a `${BUILD_DIR}/sources` directory.
   - Verify downloads using SHA256 checksums (store expected checksums in a variable or associative array and compare after download).
   - Exit with code 1 and an error message if any checksum fails.

4. **`/app/scripts/03_prepare_sources.sh`** — Prepare a unified GCC source tree. Must:
   - Create symbolic links for `gmp`, `mpfr`, `mpc`, and `isl` inside the GCC source directory.
   - Validate that each symlink target exists before linking; exit with code 1 if any source directory is missing.

5. **`/app/scripts/04_build_binutils.sh`** — Build and install cross-binutils. Must:
   - Build binutils for both `riscv32-unknown-linux-gnu` and `riscv64-unknown-linux-gnu` targets.
   - Use out-of-tree builds (separate build directories from source).
   - Install into `${INSTALL_DIR}`.
   - Use `--disable-multilib` for each target-specific build.

6. **`/app/scripts/05_install_headers.sh`** — Install Linux kernel headers for RISC-V. Must:
   - Install headers for both 32-bit and 64-bit RISC-V into the appropriate sysroot directories under `${INSTALL_DIR}`.
   - Use `ARCH=riscv` when invoking the kernel header install.

7. **`/app/scripts/06_build_bootstrap_gcc.sh`** — Build a bootstrap (C-only) GCC. Must:
   - Build a stage-1 GCC enabling only the C language (`--enable-languages=c`).
   - Target both `riscv32-unknown-linux-gnu` and `riscv64-unknown-linux-gnu`.
   - Use `--without-headers` and `--with-newlib` for the bootstrap phase.
   - Install into `${INSTALL_DIR}`.

8. **`/app/scripts/07_build_glibc.sh`** — Build and install glibc. Must:
   - Build glibc for both 32-bit and 64-bit RISC-V targets.
   - Configure with `--host` set to the appropriate cross-target triplet.
   - Install into the corresponding sysroot under `${INSTALL_DIR}`.

9. **`/app/scripts/08_build_full_gcc.sh`** — Rebuild GCC with full C/C++ support. Must:
   - Enable languages: `c,c++`.
   - Link against the newly built glibc.
   - Build for both 32-bit and 64-bit targets.
   - Install into `${INSTALL_DIR}`.

10. **`/app/scripts/09_build_gdb.sh`** — Build and install GDB. Must:
    - Build GDB (including `gdbserver`) for both RISC-V targets.
    - Configure with `--with-expat` for XML support.
    - Install into `${INSTALL_DIR}`.

11. **`/app/scripts/10_package_and_test.sh`** — Package and verify. Must:
    - Create a compressed tarball named `riscv-toolchain-${TOOLCHAIN_VERSION}.tar.gz` in `/app`.
    - Contain a verification section that compiles four small test programs (using the built cross-compilers):
      - `test_rv32_static.c` — 32-bit, statically linked (`-static`)
      - `test_rv32_dynamic.c` — 32-bit, dynamically linked
      - `test_rv64_static.c` — 64-bit, statically linked (`-static`)
      - `test_rv64_dynamic.c` — 64-bit, dynamically linked
    - Use `file` command on each resulting binary to verify it is a RISC-V ELF of the correct class (ELF32/ELF64) and linkage type.
    - Exit with code 1 if any verification check fails.

12. **`/app/config.json`** — A JSON configuration file summarizing the toolchain build parameters:
    ```json
    {
      "toolchain_name": "riscv-cross-toolchain",
      "targets": ["riscv32-unknown-linux-gnu", "riscv64-unknown-linux-gnu"],
      "architectures": ["rv32imac", "rv64imac"],
      "languages": ["c", "c++"],
      "components": {
        "binutils": "<version>",
        "gcc": "<version>",
        "glibc": "<version>",
        "linux": "<version>",
        "gdb": "<version>"
      },
      "sysroot_layout": {
        "riscv32": "${INSTALL_DIR}/riscv32-unknown-linux-gnu/sysroot",
        "riscv64": "${INSTALL_DIR}/riscv64-unknown-linux-gnu/sysroot"
      }
    }
    ```
    Replace `<version>` with the actual version strings used in the download script. The `sysroot_layout` values must use the literal string `${INSTALL_DIR}` as a placeholder.

### Constraints

- All phase scripts (`/app/scripts/01_install_deps.sh` through `/app/scripts/10_package_and_test.sh`) must be individually sourceable from `build_toolchain.sh` and must not use `#!/bin/bash` shebangs (they are sourced, not executed directly).
- Every script must reference `INSTALL_DIR`, `BUILD_DIR`, and target triplet variables defined in `build_toolchain.sh` — no hardcoded paths.
- Out-of-tree builds must be used for all compiled components (binutils, gcc, glibc, gdb).
- The `config.json` must be valid JSON parseable by standard tools.
