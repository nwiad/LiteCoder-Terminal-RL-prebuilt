## Cross-compilation Toolchain Builder for ARM64

Create a shell-based build system that automates the construction of a cross-compilation toolchain targeting `aarch64-linux-musl` on an Ubuntu host. The toolchain prefix is `/opt/aarch64-linux-musl`.

### Technical Requirements

- Language: Bash (POSIX-compatible where possible)
- All scripts must be executable (`chmod +x`)
- Output directory: `/app/`

### Deliverables

Produce the following files under `/app/`:

1. **`build_toolchain.sh`** — The main orchestrator script. When executed, it must print each build phase to stdout (one phase per line) in the exact order below, prefixed with `[PHASE]`:

   ```
   [PHASE] install-prerequisites
   [PHASE] download-sources
   [PHASE] build-binutils
   [PHASE] install-kernel-headers
   [PHASE] install-musl-headers
   [PHASE] build-bootstrap-gcc
   [PHASE] build-musl
   [PHASE] build-final-gcc
   [PHASE] smoke-test
   [PHASE] package
   ```

   The script must define and use the following environment variables at the top:

   - `TARGET=aarch64-linux-musl`
   - `PREFIX=/opt/aarch64-linux-musl`
   - `SYSROOT=$PREFIX/$TARGET`
   - `PATH=$PREFIX/bin:$PATH`
   - `JOBS=$(nproc 2>/dev/null || echo 2)`

   The script must source each phase script from a `phases/` subdirectory (e.g., `source phases/01_install_prerequisites.sh`). If any phase script exits with a non-zero status, the main script must immediately print `[ERROR] <phase-name> failed` and exit with code 1.

2. **`phases/`** directory containing individual phase scripts, each implementing one build phase. Each script must be a standalone sourceable Bash file. Required files:

   - `01_install_prerequisites.sh`
   - `02_download_sources.sh`
   - `03_build_binutils.sh`
   - `04_install_kernel_headers.sh`
   - `05_install_musl_headers.sh`
   - `06_build_bootstrap_gcc.sh`
   - `07_build_musl.sh`
   - `08_build_final_gcc.sh`
   - `09_smoke_test.sh`
   - `10_package.sh`

   Each phase script must:
   - Begin with a comment header: `# Phase: <phase-name>`
   - Use `$TARGET`, `$PREFIX`, `$SYSROOT`, and `$JOBS` variables (not hardcoded values)
   - Contain the actual shell commands (configure, make, make install, etc.) appropriate for that phase

   Specific phase requirements:

   - **`02_download_sources.sh`**: Must define an associative array or equivalent named `SOURCES` mapping component names to download URLs for at least: `binutils`, `gcc`, `gmp`, `mpfr`, `mpc`, `isl`, `musl`, `linux`. Must include a checksum verification step using `sha256sum`.
   - **`03_build_binutils.sh`**: Must use `--target=$TARGET`, `--prefix=$PREFIX`, `--with-sysroot=$SYSROOT`, and `--disable-multilib` in the configure command.
   - **`06_build_bootstrap_gcc.sh`**: Must configure with `--enable-languages=c` only (no C++), `--disable-threads`, `--disable-shared`, and `--without-headers`.
   - **`08_build_final_gcc.sh`**: Must configure with `--enable-languages=c,c++`, `--enable-threads=posix`, and `--enable-shared`.
   - **`09_smoke_test.sh`**: Must create a C source file, compile it with `$PREFIX/bin/$TARGET-gcc -static`, and verify the resulting binary is a statically linked aarch64 ELF using `file` command output. Must print `[SMOKE] PASS` or `[SMOKE] FAIL` accordingly.
   - **`10_package.sh`**: Must create a tarball at `$PREFIX/../aarch64-linux-musl-toolchain.tar.gz` containing the full `$PREFIX` directory.

3. **`toolchain.json`** — A JSON metadata file describing the toolchain configuration with the following exact structure:

   ```json
   {
     "target": "aarch64-linux-musl",
     "prefix": "/opt/aarch64-linux-musl",
     "sysroot": "/opt/aarch64-linux-musl/aarch64-linux-musl",
     "components": {
       "binutils": { "version": "<version>", "url": "<url>" },
       "gcc": { "version": "<version>", "url": "<url>" },
       "musl": { "version": "<version>", "url": "<url>" },
       "linux": { "version": "<version>", "url": "<url>" },
       "gmp": { "version": "<version>", "url": "<url>" },
       "mpfr": { "version": "<version>", "url": "<url>" },
       "mpc": { "version": "<version>", "url": "<url>" },
       "isl": { "version": "<version>", "url": "<url>" }
     },
     "phases": [
       "install-prerequisites",
       "download-sources",
       "build-binutils",
       "install-kernel-headers",
       "install-musl-headers",
       "build-bootstrap-gcc",
       "build-musl",
       "build-final-gcc",
       "smoke-test",
       "package"
     ],
     "default_flags": {
       "static": true,
       "cflags": "-O2",
       "ldflags": "-static"
     }
   }
   ```

   All 8 components must be present. Version strings must follow semver-like format (e.g., `"2.42"`, `"13.2.0"`, `"1.2.4"`). URLs must be valid `https://` URLs pointing to official release tarballs (e.g., from `ftp.gnu.org`, `musl.libc.org`, `cdn.kernel.org`).
