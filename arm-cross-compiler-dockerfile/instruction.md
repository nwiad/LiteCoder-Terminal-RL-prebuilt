## Containerized C/C++ Cross-Compiler Build

Create a multi-stage Dockerfile at `/app/Dockerfile` that builds a GCC-based cross-compiler toolchain targeting ARM Cortex-A9 (armv7-a / hard-float ABI) inside a Ubuntu 22.04 container, producing a reproducible toolchain tarball.

### Technical Requirements

- **Language/Tool:** Dockerfile (multi-stage or single-stage)
- **Base Image:** `ubuntu:22.04`
- **Output file (inside container):** `/tmp/arm-cortex-a9--linux-gnueabihf.tar.xz`
- **Dockerfile location:** `/app/Dockerfile`

### Target Toolchain Specifications

- **Target triplet:** `arm-linux-gnueabihf`
- **Architecture:** `armv7-a` with hard-float ABI (`-mfloat-abi=hard`)
- **CPU:** Cortex-A9
- **FPU:** VFPv3-D16 or NEON (either is acceptable)
- **Languages:** C and C++

### Source Versions

Use the following component versions (fetch official release tarballs from GNU mirrors or kernel.org):

| Component   | Version  |
|-------------|----------|
| binutils    | 2.42     |
| GCC         | 13.2.0   |
| glibc       | 2.38     |
| Linux headers | 6.6.x (any 6.6 patch release) |
| gmp         | 6.3.0    |
| mpfr        | 4.2.1    |
| mpc         | 1.3.1    |
| isl         | 0.26     |

### Dockerfile Requirements

1. **Build dependencies:** The Dockerfile must install all necessary build dependencies (e.g., `build-essential`, `wget`/`curl`, `texinfo`, `bison`, `flex`, `gawk`, `xz-utils`, etc.) in an early layer.

2. **Source fetching:** Download and unpack source tarballs for binutils, GCC (with gmp, mpfr, mpc, isl), glibc, and Linux kernel headers.

3. **Non-root build user:** Create a non-root user named `xbuilder` and use it for the compilation steps. The toolchain install prefix must be `/cross`.

4. **Build stages (in order):**
   - Build and install **binutils** for `arm-linux-gnueabihf` with sysroot support under `/cross`.
   - Install **Linux kernel headers** for `arm` architecture into the sysroot at `/cross/arm-linux-gnueabihf`.
   - **Stage-1 GCC** (bootstrap): Build a minimal C-only GCC sufficient to compile glibc. Configure with `--without-headers` or `--with-newlib` and `--disable-shared`.
   - Build and install **glibc** for `armv7-a` hard-float into the sysroot.
   - **Stage-2 GCC** (full): Rebuild GCC with full C and C++ support and link-time optimization (`--enable-lto`).

5. **Post-build processing:**
   - Strip debug symbols from all binaries and libraries in `/cross` using `strip` or the cross-strip tool.
   - Remove unnecessary static libraries that are not needed for cross-compilation.

6. **Reproducibility:** The final tarball must be created with deterministic file ordering and normalized timestamps. Use flags such as `--sort=name`, `--mtime=`, and `--owner=0 --group=0` (or equivalent) when creating the `.tar.xz` archive.

7. **Sanity check:** As a final step in the Dockerfile, compile a simple C "Hello, World!" program using the built cross-compiler (`/cross/bin/arm-linux-gnueabihf-gcc`) and verify it produces a valid ARM ELF binary. Install `qemu-user` (or `qemu-user-static`) and execute the compiled binary with `qemu-arm` to confirm it runs and prints output.

### Output Tarball Structure

The tarball `/tmp/arm-cortex-a9--linux-gnueabihf.tar.xz` must contain the toolchain rooted at a top-level directory. When extracted, the following paths must exist within the archive:

- `bin/arm-linux-gnueabihf-gcc` — the C cross-compiler
- `bin/arm-linux-gnueabihf-g++` — the C++ cross-compiler
- `bin/arm-linux-gnueabihf-ld` — the linker
- `bin/arm-linux-gnueabihf-as` — the assembler
- `arm-linux-gnueabihf/` — sysroot directory containing `lib/` and `include/`
- `lib/gcc/arm-linux-gnueabihf/13.2.0/` — GCC internal libraries

### Verification Criteria

The Dockerfile is considered correct if:

1. `docker build -t cross-arm .` completes successfully from `/app`.
2. The image contains `/tmp/arm-cortex-a9--linux-gnueabihf.tar.xz`.
3. The tarball contains the required cross-compiler binaries listed above.
4. The sanity-check step (compiling and running a Hello World ARM binary via qemu-arm) succeeds during the build.
5. The `xbuilder` user exists in the final image.
6. The toolchain prefix `/cross` exists and contains `bin/`, `lib/`, and `arm-linux-gnueabihf/` subdirectories.
