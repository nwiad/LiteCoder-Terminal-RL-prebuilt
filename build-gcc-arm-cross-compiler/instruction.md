## Build GCC Cross Compiler for ARM

Build a complete GCC cross-compiler toolchain from source targeting ARMv7 (bare-metal) on the current Ubuntu system. The toolchain must use newlib as the C library and be installed to a specific prefix.

### Technical Requirements

- **Host system:** Ubuntu (current)
- **Target triplet:** `arm-none-eabi`
- **GCC version:** 13.x (use the latest 13.x release available from https://ftp.gnu.org/gnu/gcc/)
- **C library:** newlib (latest stable release from https://sourceware.org/pub/newlib/)
- **Install prefix:** `/opt/arm-none-eabi`
- **Prerequisites:** GMP, MPFR, MPC, and ISL must be built and used (either in-tree or as separate builds)

### Build Steps Overview

1. Install all necessary build dependencies via `apt`.
2. Create a structured working directory under `/app/build-arm-toolchain/` for sources and build artifacts.
3. Download and extract GCC 13.x source and its prerequisites (GMP, MPFR, MPC, ISL).
4. Download and extract newlib source.
5. Build and install binutils for the `arm-none-eabi` target into `/opt/arm-none-eabi`.
6. Build a bootstrap (stage 1) GCC cross-compiler (C only, without libc support).
7. Build and install newlib using the bootstrap compiler.
8. Build and install the final (stage 2) GCC cross-compiler with C and C++ support, linked against newlib.

### Directory Structure

The working directory must be organized as:

```
/app/build-arm-toolchain/
├── src/          # extracted source tarballs
├── build/        # out-of-tree build directories
```

The final installed toolchain must reside under:

```
/opt/arm-none-eabi/
├── bin/          # cross-compiler binaries
├── lib/          # host libraries
├── arm-none-eabi/
│   ├── lib/      # target libraries (newlib)
│   └── include/  # target headers (newlib)
```

### Verification Requirements

1. The following binaries must exist and be executable under `/opt/arm-none-eabi/bin/`:
   - `arm-none-eabi-gcc`
   - `arm-none-eabi-g++`
   - `arm-none-eabi-as`
   - `arm-none-eabi-ld`
   - `arm-none-eabi-objdump`
   - `arm-none-eabi-objcopy`
   - `arm-none-eabi-ar`

2. Running `arm-none-eabi-gcc -v` must show:
   - Target: `arm-none-eabi`
   - GCC version 13.x
   - Configured with `--with-newlib`

3. Create a test C file at `/app/test_cross.c` with the following content:

```c
volatile int result;
int main(void) {
    int a = 10;
    int b = 20;
    result = a + b;
    while(1);
    return 0;
}
```

4. Compile the test file to an ELF binary at `/app/test_cross.elf`:
   ```
   /opt/arm-none-eabi/bin/arm-none-eabi-gcc -mcpu=cortex-m3 -mthumb -nostartfiles -o /app/test_cross.elf /app/test_cross.c
   ```

5. The resulting `/app/test_cross.elf` must:
   - Be a valid ELF file for ARM architecture (verifiable via `file` command showing "ELF 32-bit LSB executable, ARM")
   - Contain the `main` symbol (verifiable via `arm-none-eabi-objdump -t`)

6. Write a summary report to `/app/output.json` with the following structure:

```json
{
  "gcc_version": "<full version string from arm-none-eabi-gcc -dumpfullversion>",
  "target": "arm-none-eabi",
  "install_prefix": "/opt/arm-none-eabi",
  "newlib_version": "<newlib version used>",
  "languages": ["c", "c++"],
  "binutils_version": "<binutils version used>",
  "test_compile_success": true
}
```
