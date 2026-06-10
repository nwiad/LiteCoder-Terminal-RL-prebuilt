## Build Toolchain Bootstrap

Bootstrap a GCC cross-compiler toolchain from source targeting bare-metal ARM Cortex-M4 (arm-none-eabi), then verify it by compiling test programs.

### Technical Requirements

- **OS:** Ubuntu (standard container utilities available)
- **Target triplet:** `arm-none-eabi`
- **Target architecture flags:** `-mcpu=cortex-m4 -mthumb`
- **Toolchain install prefix:** `/app/toolchain`
- **Toolchain binaries must be in:** `/app/toolchain/bin/`
- **All build work performed under:** `/app/build/`

### Component Versions

Use the following source versions (download from official GNU/Sourceware mirrors):

- **binutils:** 2.42
- **GCC:** 13.2.0
- **newlib:** 4.4.0.20231231

### Step-by-Step Requirements

**1. Install Build Dependencies**

Install all packages required to build binutils, GCC, and newlib from source (e.g., `make`, `g++`, `libgmp-dev`, `libmpfr-dev`, `libmpc-dev`, `texinfo`, `wget`, etc.).

**2. Build and Install binutils**

- Build binutils 2.42 for target `arm-none-eabi`
- Install into `/app/toolchain`
- After installation, the following binaries must exist:
  - `/app/toolchain/bin/arm-none-eabi-as`
  - `/app/toolchain/bin/arm-none-eabi-ld`
  - `/app/toolchain/bin/arm-none-eabi-objcopy`
  - `/app/toolchain/bin/arm-none-eabi-objdump`

**3. Build and Install Bootstrap GCC (C only)**

- Build a minimal bootstrap GCC 13.2.0 (C language only, `--without-headers`, `--with-newlib`)
- Target: `arm-none-eabi`
- Install into `/app/toolchain`
- After installation: `/app/toolchain/bin/arm-none-eabi-gcc` must exist

**4. Build and Install newlib**

- Build newlib 4.4.0.20231231 for `arm-none-eabi` using the bootstrap compiler from step 3
- Install into `/app/toolchain`
- After installation, the following must exist:
  - `/app/toolchain/arm-none-eabi/lib/libc.a`
  - `/app/toolchain/arm-none-eabi/lib/libm.a`
  - `/app/toolchain/arm-none-eabi/include/stdio.h`
  - `/app/toolchain/arm-none-eabi/include/stdlib.h`

**5. Rebuild GCC with newlib Support**

- Rebuild GCC 13.2.0 with C and C++ language support, linked against the newlib installed in step 4
- Install into `/app/toolchain`
- After installation, both must exist:
  - `/app/toolchain/bin/arm-none-eabi-gcc`
  - `/app/toolchain/bin/arm-none-eabi-g++`

**6. Verification Test Programs**

Create and compile the following test programs. All source files and outputs go under `/app/test/`.

**Test 1: Bare-metal hello (no libc)**

Create `/app/test/hello_bare.c`:
```c
volatile unsigned int * const UART0DR = (unsigned int *)0x40004000;

void print_uart0(const char *s) {
    while (*s != '\0') {
        *UART0DR = (unsigned int)(*s);
        s++;
    }
}

void _start(void) {
    print_uart0("Hello, bare-metal!\n");
    while (1);
}
```

Compile to ELF: `/app/test/hello_bare.elf`
Convert to binary: `/app/test/hello_bare.bin`

Use flags: `-mcpu=cortex-m4 -mthumb -nostdlib -T /app/test/cortexm4.ld`

**Test 2: Cortex-M4 linker script**

Create `/app/test/cortexm4.ld` — a linker script for ARM Cortex-M4 with:
- FLASH region starting at `0x08000000`, size `512K`
- RAM region starting at `0x20000000`, size `128K`
- `.isr_vector` section placed at start of FLASH
- `.text`, `.rodata` in FLASH
- `.data`, `.bss` in RAM (with load address in FLASH)

**Test 3: LED blink program**

Create `/app/test/blink.c`:
```c
#include <stdint.h>

#define RCC_AHB1ENR  (*(volatile uint32_t *)0x40023830)
#define GPIOA_MODER  (*(volatile uint32_t *)0x40020000)
#define GPIOA_ODR    (*(volatile uint32_t *)0x40020014)

void _start(void) {
    RCC_AHB1ENR |= (1 << 0);
    GPIOA_MODER |= (1 << 10);

    while (1) {
        GPIOA_ODR ^= (1 << 5);
        for (volatile int i = 0; i < 100000; i++);
    }
}
```

Compile and link to ELF: `/app/test/blink.elf`
Convert to binary: `/app/test/blink.bin`

Use flags: `-mcpu=cortex-m4 -mthumb -nostdlib -T /app/test/cortexm4.ld`

**Test 4: Standard C library usage**

Create `/app/test/stdlib_test.c`:
```c
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(void) {
    char *buf = (char *)malloc(64);
    if (buf) {
        snprintf(buf, 64, "Toolchain works: %d + %d = %d", 17, 25, 17 + 25);
        free(buf);
    }
    return 0;
}
```

Compile to ELF using newlib specs: `/app/test/stdlib_test.elf`

Use flags: `-mcpu=cortex-m4 -mthumb --specs=nosys.specs`

### Output Verification Summary

After completion, the following files must exist and be valid:

| File | Type |
|---|---|
| `/app/toolchain/bin/arm-none-eabi-gcc` | executable |
| `/app/toolchain/bin/arm-none-eabi-g++` | executable |
| `/app/toolchain/bin/arm-none-eabi-as` | executable |
| `/app/toolchain/bin/arm-none-eabi-ld` | executable |
| `/app/toolchain/bin/arm-none-eabi-objcopy` | executable |
| `/app/toolchain/bin/arm-none-eabi-objdump` | executable |
| `/app/toolchain/arm-none-eabi/lib/libc.a` | static library |
| `/app/toolchain/arm-none-eabi/lib/libm.a` | static library |
| `/app/test/cortexm4.ld` | linker script |
| `/app/test/hello_bare.elf` | ARM ELF binary |
| `/app/test/hello_bare.bin` | raw binary |
| `/app/test/blink.elf` | ARM ELF binary |
| `/app/test/blink.bin` | raw binary |
| `/app/test/stdlib_test.elf` | ARM ELF binary |

All `.elf` files must be valid 32-bit ARM ELF executables (verifiable via `file` command showing "ELF 32-bit LSB" and "ARM").
