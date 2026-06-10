## Cross-Architecture Static BusyBox

Build a fully-static BusyBox executable that targets the 32-bit ARMv7 architecture using a cross-compiler on an x86_64 host, and verify it runs under QEMU user-mode emulation.

### Technical Requirements

- **Host architecture:** x86_64
- **Target architecture:** ARM 32-bit (ARMv7 / arm-linux)
- **Linking:** Fully static (no dynamic library dependencies)
- **C library:** musl libc (use the `musl`-based cross-compiler toolchain)
- **Output file:** `/app/output/busybox-armv7`

### Steps

1. Install the ARM cross-compilation toolchain (musl-based) and QEMU user-mode emulation (`qemu-arm-static` or equivalent).
2. Fetch the BusyBox source code (version 1.36.x or later).
3. Configure BusyBox for a static build with applets enabled, targeting ARMv7 with the musl cross-compiler.
4. Cross-compile BusyBox to produce a single statically-linked ARM binary.
5. Place the final binary at `/app/output/busybox-armv7`.
6. Verify the binary executes correctly under `qemu-arm-static`.

### Output Specifications

The file `/app/output/busybox-armv7` must satisfy all of the following:

1. **ELF format for ARM:** `file` output must indicate it is an ELF 32-bit executable for ARM.
2. **Statically linked:** `file` output must contain the string `statically linked`.
3. **Executable permission:** The file must have the executable bit set.
4. **Functional under QEMU:** Running `qemu-arm-static /app/output/busybox-armv7 --help` must produce output containing the string `BusyBox`.
5. **Core applets present:** Running `qemu-arm-static /app/output/busybox-armv7 --list` must include at least the following applets: `sh`, `ls`, `cat`, `echo`, `mkdir`, `rm`, `cp`, `mv`, `grep`, `sed`.
