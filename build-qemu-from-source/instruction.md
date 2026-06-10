## Build the QEMU Emulator Suite from Source

Clone the official QEMU repository, configure it for ARM and RISC-V targets, build it from source, and produce a structured build report.

### Technical Requirements

- **Environment:** Linux (Debian/Ubuntu-based)
- **Build dependencies:** Install all required build-time dependencies using native system packages only (no PyPI).

### Steps

1. Clone the official upstream QEMU Git repository (https://gitlab.com/qemu-project/qemu.git) into `/app/qemu-upstream`. Ensure submodules are initialized.

2. Create an out-of-tree build directory at `/app/qemu-build`. Configure the source from within this build directory with exactly these flags:
   - `--target-list=arm-softmmu,riscv32-softmmu,riscv64-softmmu`

3. Build QEMU using `make -j$(nproc)` from the build directory.

4. Install the built QEMU suite system-wide via `sudo make install` (default prefix `/usr/local`).

5. Verify the following three binaries are available on `PATH` and executable:
   - `qemu-system-arm`
   - `qemu-system-riscv32`
   - `qemu-system-riscv64`

6. Run a smoke test for each of the three binaries: launch with `-machine none -display none -serial mon:stdio` and confirm each binary starts without error (exits cleanly).

7. Generate a build report file at `/app/qemu-build-report.txt` with the following exact format (one item per line, using the exact labels shown):

```
git_commit: <full 40-character Git commit hash of the checked-out QEMU source>
configure_flags: --target-list=arm-softmmu,riscv32-softmmu,riscv64-softmmu
cpu_cores: <integer number of CPU cores used during build, i.e., output of nproc>
qemu_version: <full output of qemu-system-arm --version, first line only>
```

### Output

- Installed binaries: `qemu-system-arm`, `qemu-system-riscv32`, `qemu-system-riscv64` available on PATH under `/usr/local/bin/`.
- Build report: `/app/qemu-build-report.txt` in the exact format specified above.
