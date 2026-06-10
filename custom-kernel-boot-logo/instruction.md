## Rebuilding the Linux Kernel with Custom Boot Logo

Download the official Linux 6.8 kernel sources, patch them with a custom boot-up logo, and produce a bootable bzImage that contains the new logo embedded in the kernel binary.

### Technical Requirements

- **Environment:** Linux (Debian/Ubuntu-based), with all necessary kernel build dependencies installed (e.g., `build-essential`, `flex`, `bison`, `libelf-dev`, `bc`, `libssl-dev`, `libncurses-dev`, etc.)
- **Kernel version:** Linux 6.8 stable release, downloaded from https://cdn.kernel.org/pub/linux/kernel/v6.x/linux-6.8.tar.xz
- **Architecture:** x86_64

### Steps and Constraints

1. **Install build dependencies:** Ensure all packages required for a full kernel compile are installed.

2. **Download and extract kernel source:**
   - Download the Linux 6.8 tarball from kernel.org.
   - Extract it so the kernel source tree is located at `/app/linux-6.8/`.

3. **Create and place the custom logo:**
   - Create an 80×80 pixel logo image in PPM format with no more than 224 colors (Clut224 indexed format).
   - The logo must NOT be a blank/single-color image — it must contain at least 2 distinct colors.
   - Place the final logo file at the path: `/app/linux-6.8/drivers/video/logo/logo_linux_clut224.ppm`
   - This file must be a valid ASCII PPM (P3) or binary PPM (P6) file with dimensions exactly 80×80 and at most 224 unique colors.

4. **Configure the kernel:**
   - Start from a default x86_64 config (e.g., `make defconfig` or `make x86_64_defconfig`).
   - Ensure `CONFIG_LOGO=y` and `CONFIG_LOGO_LINUX_CLUT224=y` are set in the final `.config`.
   - The final kernel config must be saved at `/app/linux-6.8/.config`.

5. **Build the kernel:**
   - Run the kernel build targeting `bzImage`.
   - The final bootable kernel image must exist at: `/app/linux-6.8/arch/x86/boot/bzImage`

6. **Verification artifacts:**
   - The built bzImage must be a valid x86 boot sector image (the `file` command should identify it as a Linux kernel boot image).
   - The compiled logo object file must exist at: `/app/linux-6.8/drivers/video/logo/logo_linux_clut224.o`

### Output Files

| Artifact | Path |
|---|---|
| Kernel source tree | `/app/linux-6.8/` |
| Logo PPM file | `/app/linux-6.8/drivers/video/logo/logo_linux_clut224.ppm` |
| Kernel config | `/app/linux-6.8/.config` |
| Built kernel image | `/app/linux-6.8/arch/x86/boot/bzImage` |
| Logo object file | `/app/linux-6.8/drivers/video/logo/logo_linux_clut224.o` |
