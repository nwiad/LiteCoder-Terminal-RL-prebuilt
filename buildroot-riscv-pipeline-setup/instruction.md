## Bootstrap a Multi-Stage Buildroot Linux System for RISC-V

Create a reproducible two-stage Buildroot build pipeline for RISC-V 64-bit. The pipeline must produce configuration files, build scripts, and a partitioned raw disk image. All artifacts are generated under `/app`.

### Technical Requirements

- Language/Tools: Bash scripts, Buildroot defconfig format, standard Linux utilities (`dd`, `mkfs.ext2`, `sfdisk`/`fdisk`, `sha256sum`)
- Working directory: `/app`

### Deliverables

#### 1. Buildroot Defconfig Fragment — `/app/configs/riscv64_two_stage_defconfig`

A valid Buildroot defconfig file that configures the following (one `BR2_*` option per line):

- Architecture: RISC-V 64-bit, little-endian
- ISA extension: RV64GC (i.e., `rv64imafdc`)
- C library: glibc
- Linux kernel version: 6.1.x series (any patch level in 6.1)
- BusyBox enabled as the init system
- Dropbear SSH server enabled
- Root filesystem type: ext2
- Toolchain uses glibc (not musl or uclibc)

The file must:
- Contain only lines matching the pattern `BR2_SOMETHING=y`, `BR2_SOMETHING="value"`, or `# BR2_SOMETHING is not set`; no free-form comments or blank lines are required but are allowed.
- Include at minimum these categories of settings (exact symbol names must be valid Buildroot 2023.02.x symbols):
  - `BR2_riscv` set to `y`
  - `BR2_RISCV_64` set to `y`
  - `BR2_PACKAGE_BUSYBOX` set to `y`
  - `BR2_PACKAGE_DROPBEAR` set to `y`
  - `BR2_TARGET_ROOTFS_EXT2` set to `y`
  - `BR2_TOOLCHAIN_BUILDROOT_GLIBC` set to `y`
  - A `BR2_LINUX_KERNEL_CUSTOM_VERSION_VALUE` containing `6.1`

#### 2. Build Script — `/app/build.sh`

An executable Bash script (`#!/bin/bash`) that automates the two-stage build pipeline. The script must:

- Be executable (`chmod +x`).
- Define and use a variable `BUILDROOT_VERSION` set to a `2023.02.x` release (e.g., `2023.02.9`).
- Contain a stage-1 section (comments or function named `stage1` or containing the string `stage1` or `Stage 1` or `STAGE_1`) that:
  - Downloads or references the Buildroot tarball.
  - Verifies the tarball's SHA-256 checksum (must invoke `sha256sum`).
  - Extracts the tarball.
  - Initiates a toolchain-only build targeting the cross-compiler path `output/host/bin/riscv64-linux-gcc`.
- Contain a stage-2 section (comments or function named `stage2` or containing the string `stage2` or `Stage 2` or `STAGE_2`) that:
  - Reuses the stage-1 toolchain.
  - Builds the full Linux image including BusyBox, Dropbear, and ext2 rootfs.
- Contain a disk-image packaging step that produces `/app/sdcard.img`.
- Compute and write the SHA-256 hash of `sdcard.img` to `/app/sdcard.img.sha256`. The sha256 file must contain the hash string (at minimum 64 hex characters).

#### 3. Disk Image — `/app/sdcard.img`

Since a full Buildroot compilation is not feasible in this environment, produce a structurally correct **empty** raw disk image that matches the target layout:

- Total size: exactly 8 MiB (8388608 bytes).
- Partition layout (MBR):
  - Partition 1: starts at offset 1 MiB (sector 2048 with 512-byte sectors), size 7 MiB, type Linux (0x83).
- The partition at offset 1 MiB must contain a valid ext2 filesystem (created via `mkfs.ext2` or equivalent). The ext2 filesystem must be mountable.
- Write the SHA-256 of the final `sdcard.img` to `/app/sdcard.img.sha256`.

#### 4. QEMU Boot Script — `/app/qemu_boot.sh`

An executable Bash script that documents how to boot the image in QEMU:

- Must reference `qemu-system-riscv64`.
- Must include flags for: no-graphics mode (`-nographic`), serial console, and machine type (`-machine virt` or `sifive_u`).
- Must reference `sdcard.img` or a kernel/rootfs path.
- Must be executable.

#### 5. Cross-Compile Test Script — `/app/cross_compile_test.sh`

An executable Bash script that:

- Contains a minimal C "Hello RISC-V" program (inline or references a `/app/hello.c` file).
- Invokes `riscv64-linux-gcc` (or a path containing `riscv64`) to cross-compile it.
- References `qemu-riscv64` (user-mode) or `qemu-system-riscv64` to run the resulting binary.
- Must be executable.

### Summary of Output Files

| File | Description |
|---|---|
| `/app/configs/riscv64_two_stage_defconfig` | Buildroot defconfig |
| `/app/build.sh` | Two-stage build script |
| `/app/sdcard.img` | 8 MiB raw disk image with MBR + ext2 |
| `/app/sdcard.img.sha256` | SHA-256 hash of sdcard.img |
| `/app/qemu_boot.sh` | QEMU boot command script |
| `/app/cross_compile_test.sh` | Cross-compile and run hello world |
