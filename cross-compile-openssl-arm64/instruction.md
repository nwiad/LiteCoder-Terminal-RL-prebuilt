## OpenSSL Cross-Compilation Build Script for ARM Cortex-A53

Write a shell script that cross-compiles OpenSSL 3.0.9 from source for an ARM Cortex-A53 (aarch64) target, producing statically-linked, stripped `libssl.a` and `libcrypto.a` suitable for a size-sensitive embedded Linux image.

### Technical Requirements

- Language: Bash (the script must start with `#!/usr/bin/env bash`)
- Output file: `/app/build_openssl.sh`
- The script must be syntactically valid Bash and pass `bash -n` without errors.
- The script must use `set -euo pipefail` near the top for strict error handling.

### Environment Assumptions

The script should assume the following pre-existing environment:

- Build host: x86-64 Ubuntu 22.04
- Cross toolchain installed at `/opt/cross/a53-linux-musl/` with prefix `aarch64-linux-musl-`
- Toolchain binaries: `aarch64-linux-musl-gcc`, `aarch64-linux-musl-ar`, `aarch64-linux-musl-ranlib`, `aarch64-linux-musl-strip` located under `/opt/cross/a53-linux-musl/bin/`
- OpenSSL 3.0.9 tarball already downloaded to `/tmp/openssl-3.0.9.tar.gz`
- Installation prefix: `/opt/a53-ssl`

### Script Functional Requirements

The script must perform the following steps, in order:

1. **Tarball extraction**: Extract `/tmp/openssl-3.0.9.tar.gz` into a working directory and `cd` into the extracted source directory (`openssl-3.0.9`).

2. **Cross-compilation environment**: Export or set the following environment variables pointing to the cross toolchain:
   - `CC` — the cross C compiler
   - `AR` — the cross archiver
   - `RANLIB` — the cross ranlib
   The variable values must reference the full path or use `CROSS_COMPILE`/`--cross-compile-prefix` so that the correct toolchain is used.

3. **Configure**: Invoke the OpenSSL `./Configure` (capital C) command with all of the following options/flags:
   - Target: `linux-aarch64`
   - `--prefix=/opt/a53-ssl`
   - `--cross-compile-prefix=aarch64-linux-musl-` (or equivalent CC/AR/RANLIB exports using the full toolchain path)
   - `no-shared` — disable shared library builds
   - `no-tests` — skip building tests
   - `no-asm` — disable assembly optimizations (for portability)
   - Must NOT include any flag that enables shared libraries

4. **Build**: Run `make` to build the libraries. Only static libraries should be produced. The make invocation should use a parallel jobs flag (e.g., `-j$(nproc)` or `-j4` or similar).

5. **Install**: Run `make install_sw` (software-only install, no docs) to install into the prefix directory `/opt/a53-ssl`.

6. **Strip**: Strip debug symbols from the installed static libraries (`/opt/a53-ssl/lib/libssl.a` and `/opt/a53-ssl/lib/libcrypto.a` or under `lib64`) using the cross `aarch64-linux-musl-strip` tool with the `--strip-debug` or `-g` flag.

7. **Cleanup**: Remove the build/source directory to save space.

### Additional Constraints

- The script must NOT use any host-native compiler (e.g., bare `gcc` or `cc`) for the OpenSSL build itself.
- The script must NOT pass `shared` or `--shared` to Configure.
- The `PATH` should be updated to include `/opt/cross/a53-linux-musl/bin/` so cross tools are discoverable.
- All critical commands (configure, make, install, strip) should be present and in the correct logical order.
