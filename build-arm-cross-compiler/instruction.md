## Building a Cross-Compiler Toolchain for ARM

Build a complete GCC-based cross-compiler toolchain from source targeting ARM Cortex-A9, installed under `/opt/arm-cross`, on an x86_64 Linux host.

### Technical Requirements

- **Host:** x86_64-linux-gnu (Ubuntu 22.04)
- **Target triplet:** `arm-linux-musleabihf`
- **Architecture:** ARMv7-A (Cortex-A9, hard-float, little-endian, EABI)
- **C library:** musl libc (statically linked by default)
- **Install prefix:** `/opt/arm-cross`
- **Components to build from source:** binutils, GCC (C and C++ frontends), GMP, MPFR, MPC, ISL, musl libc, Linux kernel headers

### Directory Structure

The installed toolchain under `/opt/arm-cross` must contain at minimum:

```
/opt/arm-cross/
├── bin/
│   ├── arm-linux-musleabihf-gcc
│   ├── arm-linux-musleabihf-g++
│   ├── arm-linux-musleabihf-as
│   ├── arm-linux-musleabihf-ld
│   ├── arm-linux-musleabihf-ar
│   ├── arm-linux-musleabihf-objdump
│   ├── arm-linux-musleabihf-readelf
│   └── arm-linux-musleabihf-strip
├── arm-linux-musleabihf/
│   ├── lib/
│   └── include/
└── lib/
    └── gcc/arm-linux-musleabihf/
```

### Functional Requirements

1. **Binutils:** Build and install cross-binutils for `arm-linux-musleabihf`.

2. **GCC (two-stage build):**
   - Stage 1: Build a minimal bootstrap GCC (C only, no libc support) sufficient to compile musl.
   - Stage 2: Build the final GCC with full C and C++ support, linked against the built musl.

3. **musl libc:** Build musl using the stage-1 compiler. Install headers, startup files, and the full library under the sysroot.

4. **Linux kernel headers:** Install sanitized kernel headers for ARM into the sysroot.

5. **Self-contained toolchain:** The toolchain must not depend on or link against host glibc libraries for target binaries. All target libraries must reside within `/opt/arm-cross`.

### Verification

1. `/opt/arm-cross/bin/arm-linux-musleabihf-gcc` must exist and be executable.

2. Running `/opt/arm-cross/bin/arm-linux-musleabihf-gcc -dumpmachine` must output exactly `arm-linux-musleabihf`.

3. Running `/opt/arm-cross/bin/arm-linux-musleabihf-gcc -v` must show the compiler was configured with `--target=arm-linux-musleabihf` and the prefix `/opt/arm-cross`.

4. The toolchain must successfully compile the following C program saved as `/app/hello_arm.c`:

   ```c
   #include <stdio.h>
   int main() {
       printf("Hello ARM\n");
       return 0;
   }
   ```

   Compile command:
   ```
   /opt/arm-cross/bin/arm-linux-musleabihf-gcc -static -o /app/hello_arm /app/hello_arm.c
   ```

   The resulting `/app/hello_arm` binary must:
   - Be a statically linked ELF 32-bit LSB executable for ARM (`readelf -h /app/hello_arm` shows `Machine: ARM`, `Class: ELF32`)
   - Not dynamically link to any shared libraries (`readelf -d /app/hello_arm` shows no NEEDED entries or reports "There is no dynamic section")

5. The toolchain must successfully compile a C++ program saved as `/app/hello_arm.cpp`:

   ```cpp
   #include <iostream>
   int main() {
       std::cout << "Hello ARM C++" << std::endl;
       return 0;
   }
   ```

   Compile command:
   ```
   /opt/arm-cross/bin/arm-linux-musleabihf-g++ -static -o /app/hello_arm_cpp /app/hello_arm.cpp
   ```

   The resulting `/app/hello_arm_cpp` must also be a statically linked ELF 32-bit ARM executable.

6. Create a compressed tarball of the toolchain at `/app/arm-cross-toolchain.tar.gz`:
   ```
   tar czf /app/arm-cross-toolchain.tar.gz -C /opt arm-cross
   ```
   This file must exist and be a valid gzip-compressed tar archive.

### Output Files

| File | Description |
|---|---|
| `/opt/arm-cross/` | Installed cross-compiler toolchain directory |
| `/app/hello_arm.c` | C test source file |
| `/app/hello_arm` | Compiled static ARM ELF binary (C) |
| `/app/hello_arm.cpp` | C++ test source file |
| `/app/hello_arm_cpp` | Compiled static ARM ELF binary (C++) |
| `/app/arm-cross-toolchain.tar.gz` | Packaged toolchain tarball |
