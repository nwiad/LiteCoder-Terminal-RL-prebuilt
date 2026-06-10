Build a minimal, bootable Linux system from source that boots in QEMU and stays under 20 MB total size.

## Technical Requirements

- Platform: x86_64 architecture
- Kernel: Linux kernel (minimal configuration)
- Userspace: BusyBox (static binary)
- Bootloader: SYSLINUX (isolinux)
- Output format: ISO 9660 bootable image
- Emulator: QEMU for testing

## Build Components

1. **Linux Kernel**: Cross-compile with minimal configuration for x86_64
2. **BusyBox**: Build static binary with essential utilities (sh, ls, cat, mount, etc.)
3. **Initramfs**: CPIO archive containing:
   - `/init` script (executable, sets up environment and launches shell)
   - BusyBox symlinks for utilities
   - Essential device nodes (`/dev/console`, `/dev/null`)
4. **Bootloader**: SYSLINUX isolinux.bin with proper configuration

## Output Requirements

- Final bootable ISO image: `/app/mini-linux.iso`
- Build log documenting commands: `/app/build.log`
- Size verification: ISO must be ≤ 20 MB (20971520 bytes)

## Functional Requirements

The system must:
- Boot successfully in QEMU (x86_64)
- Reach an interactive shell prompt
- Support basic commands: `ls`, `cat`, `echo`, `mount`, `ps`
- Display kernel boot messages
- Provide a functional `/init` that mounts essential filesystems (proc, sys, devtmpfs)

## Verification

The ISO image at `/app/mini-linux.iso` must:
1. Be a valid ISO 9660 filesystem
2. Contain kernel, initramfs, and bootloader files
3. Boot in QEMU without errors
4. Present a shell prompt within reasonable boot time
5. Have total size ≤ 20 MB
