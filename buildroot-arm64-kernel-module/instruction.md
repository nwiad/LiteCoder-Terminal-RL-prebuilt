## Build a Minimal Linux Kernel Module with Buildroot Automation

Create a buildroot-based automation that sets up an external package tree for cross-compiling a minimal custom Linux kernel module targeting ARM64 (aarch64). The deliverable is a fully structured buildroot external tree, kernel module source, buildroot package definition, board overlay, and a top-level Makefile — all ready to produce a bootable root filesystem image containing the pre-installed `.ko` module.

### Technical Requirements

- Language: C (kernel module), Makefile (build system), Shell (scripts)
- Target architecture: ARM64 (aarch64), QEMU "virt" machine
- Buildroot: Clone the stable LTS release from https://github.com/buildroot/buildroot.git (tag `2024.02.x` or the latest `20xx.02` LTS branch) into `/app/buildroot/`.
- All project files live under `/app/`.

### Directory Structure

The following directory layout must be created exactly:

```
/app/
├── Makefile                          # Top-level one-liner Makefile
├── BUILD_NOTES.txt                   # Documentation of build steps
├── buildroot/                        # Cloned buildroot repository
├── br2-external/
│   ├── external.desc                 # BR2_EXTERNAL descriptor
│   ├── external.mk                   # Includes package dirs
│   ├── Config.in                     # Top-level Config.in for external packages
│   ├── configs/
│   │   └── qemu_aarch64_hello_defconfig  # Custom defconfig
│   ├── package/
│   │   └── hello-world-module/
│   │       ├── Config.in             # Kconfig entry for the module
│   │       ├── hello-world-module.mk # Buildroot package .mk file
│   │       └── src/
│   │           ├── hello.c           # Kernel module source
│   │           └── Makefile          # Kbuild Makefile for the module
│   └── board/
│       └── qemu-aarch64/
│           └── rootfs_overlay/
│               └── lib/
│                   └── modules/
│                       └── .gitkeep  # Placeholder; actual .ko placed here at build time
```

### Kernel Module (`br2-external/package/hello-world-module/src/hello.c`)

- The module must be named `hello_world` (resulting in `hello-world.ko` or `hello_world.ko`).
- On `module_init`, it must print to the kernel log: `Hello, Buildroot World!`
- On `module_exit`, it must print to the kernel log: `Goodbye, Buildroot World!`
- Must use `MODULE_LICENSE("GPL")` and `MODULE_AUTHOR("Embedded Team")`.
- The Kbuild Makefile (`src/Makefile`) must build `hello_world.o` as a module (`obj-m`).

### Buildroot External Package

1. **`br2-external/external.desc`**: Must contain a `name` field (e.g., `HELLO_WORLD_EXT`) and a `desc` field.

2. **`br2-external/Config.in`**: Must source the package's `Config.in` via: `source "$BR2_EXTERNAL_HELLO_WORLD_EXT_PATH/package/hello-world-module/Config.in"`

3. **`br2-external/external.mk`**: Must include the package `.mk` file via: `include $(sort $(wildcard $(BR2_EXTERNAL_HELLO_WORLD_EXT_PATH)/package/*/*.mk))`

4. **`br2-external/package/hello-world-module/Config.in`**: Must define a `bool` config option `BR2_PACKAGE_HELLO_WORLD_MODULE` with a help text. It must `depends on BR2_LINUX_KERNEL`.

5. **`br2-external/package/hello-world-module/hello-world-module.mk`**: Must follow buildroot's package infrastructure for kernel modules (`kernel-module` and `generic-package`). It must:
   - Define `HELLO_WORLD_MODULE_VERSION` (e.g., `1.0`)
   - Define `HELLO_WORLD_MODULE_SITE` using `$(BR2_EXTERNAL_HELLO_WORLD_EXT_PATH)/package/hello-world-module/src` as a local site method (`HELLO_WORLD_MODULE_SITE_METHOD = local`)
   - Use `$(eval $(kernel-module))` and `$(eval $(generic-package))`

### Custom Defconfig (`br2-external/configs/qemu_aarch64_hello_defconfig`)

- Must be based on QEMU aarch64 virt defaults.
- Must set at minimum:
  - `BR2_aarch64=y`
  - `BR2_TOOLCHAIN_EXTERNAL=y`
  - `BR2_LINUX_KERNEL=y`
  - `BR2_LINUX_KERNEL_USE_DEFCONFIG=y` with a suitable defconfig name (e.g., `defconfig`)
  - `BR2_PACKAGE_HELLO_WORLD_MODULE=y`
  - `BR2_TARGET_ROOTFS_EXT2=y`
  - `BR2_ROOTFS_OVERLAY` pointing to the board overlay directory

### Top-Level Makefile (`/app/Makefile`)

- Must have a default target `all` that invokes buildroot's make with `BR2_EXTERNAL=/app/br2-external`.
- Must have a `defconfig` target that loads the custom defconfig.
- Must have a `clean` target.
- The Makefile must set `BR2_EXTERNAL` and reference `/app/buildroot` as the buildroot directory.

### BUILD_NOTES.txt (`/app/BUILD_NOTES.txt`)

Must document:
- The host dependencies needed (at minimum: `build-essential`, `libncurses-dev`, `unzip`, `wget`, `bc`, `rsync`, `cpio`, `python3`, `file`)
- The exact buildroot version/tag cloned
- The sequence of commands to build (defconfig load, then full build)
- How to verify the `.ko` is present in the output image
- How to boot the image with QEMU aarch64 and load the module (`insmod`)

### Output Verification

After a successful build (not required to actually execute the build during this task, but the structure must be build-ready), the following must hold:
- All files listed in the directory structure above exist with correct content.
- `hello.c` compiles conceptually as a valid kernel module (correct includes, macros, init/exit functions).
- The `.mk` file is syntactically valid buildroot package infrastructure.
- The top-level `Makefile` correctly delegates to buildroot with the external tree.
