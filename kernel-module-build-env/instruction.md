## Linux Kernel Module Build Environment

Set up a reproducible, containerised build environment for compiling an out-of-tree Linux kernel module against a vendor-supplied 5.10 kernel source tree, with all artifacts and configuration files placed under `/app`.

### Scenario

A hardware start-up provides a lightly-customized 5.10 kernel tree and a tiny "hello-world" kernel module. The tree was never installed into `/lib/modules`, no `.deb`/`.rpm` exists, and the vendor Makefile hard-codes fragile paths like `~/projects/acme-510/`. You must containerise the build so it is portable and CI-friendly.

### Technical Requirements

- All files must be created under `/app`
- No external network access or Docker daemon is required — produce the source files and build configuration only

### Required Files

1. `/app/Dockerfile`
   - Must use a Debian or Ubuntu base image (e.g., `ubuntu:22.04` or `debian:bookworm`)
   - Must install at minimum these packages: `build-essential`, `bc`, `kmod`, `flex`, `bison`, `libssl-dev`, `libelf-dev`
   - Must contain a step that extracts the vendor kernel tarball to `/opt/acme-510`
   - Must create a symlink `/opt/acme-510/current` pointing to the versioned kernel directory (e.g., `/opt/acme-510/linux-5.10`)
   - Must run kernel preparation commands in this order: `make mrproper`, `make defconfig`, `make modules_prepare`
   - Must build the out-of-tree module using `KDIR` pointing to the kernel tree under `/opt/acme-510`
   - Must copy the resulting `.ko` file into `/artifacts` inside the container
   - Must contain a step that runs `insmod` on the built module
   - Must set `LABEL maintainer=` and `LABEL build.command=` with the exact `docker build`/`docker run` incantation
   - Must use `set -e` or equivalent in all `RUN` shell commands (fail-fast)
   - Must not contain any interactive steps (no `apt-get install` without `-y`, no prompts)
   - Must pin the base image tag (no `latest`)

2. `/app/vendor-tarball/acme-kernel-5.10.tar.gz`
   - A real gzip-compressed tar archive
   - When extracted, must produce a directory named `linux-5.10/`
   - The `linux-5.10/` directory must contain at minimum a `Makefile` with a line matching `VERSION = 5` and a line matching `PATCHLEVEL = 10`
   - Must also contain a `scripts/` directory (can be empty or contain placeholder files)
   - Must also contain a `Kbuild` or `Kconfig` file (can be a placeholder)

3. `/app/module-src/hello.c`
   - A syntactically valid C source file for a Linux kernel module
   - Must include `<linux/module.h>` and `<linux/init.h>`
   - Must define an init function using `module_init()` macro
   - Must define an exit/cleanup function using `module_exit()` macro
   - Must contain a `MODULE_LICENSE()` declaration
   - The init function must call `printk` with a message containing the string `"hello acme"`

4. `/app/module-src/Makefile`
   - Must accept `KDIR` from the environment (e.g., `KDIR ?= /opt/acme-510/current`)
   - Must NOT contain any hard-coded home directory paths (no `~`, no `/home/`, no `~/projects/`)
   - Must use the kbuild system by invoking `make -C $(KDIR) M=` pattern for building
   - Must define `obj-m` targeting the hello module (e.g., `obj-m += hello.o` or `obj-m := hello.o`)
   - Must include both a default build target and a `clean` target

5. `/app/README.md`
   - Must contain the exact `docker build` command to build the image
   - Must contain the exact `docker run` command to run the container
   - Must mention `/artifacts` as the output directory for the built `.ko` file
