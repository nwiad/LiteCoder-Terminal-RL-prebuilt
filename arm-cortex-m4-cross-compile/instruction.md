## Cross-Compiler Symphony

Set up an ARM Cortex-M4F (hard-float) cross-compilation environment on x86_64 Linux using the `arm-none-eabi-gcc` toolchain, then write and cross-compile a minimal STM32F407 "blinky" firmware to prove the toolchain works.

### Technical Requirements

- Platform: x86_64 Linux
- Toolchain: `arm-none-eabi-gcc` (install via system package manager, e.g. `gcc-arm-none-eabi` and `binutils-arm-none-eabi`, or download the official ARM GNU Toolchain)
- Language: C (C99 or later)
- All project files must reside under `/app/`

### Step 1: Workspace Layout

Create the following directory structure:

```
/app/
├── toolchain/          # Symlinks or notes about the installed toolchain
│   └── info.txt        # Toolchain version info (output of arm-none-eabi-gcc --version)
├── firmware/
│   ├── src/
│   │   └── main.c      # Blinky firmware source
│   ├── include/
│   │   └── stm32f407.h # Minimal register definitions header
│   ├── linker.ld       # Linker script for STM32F407
│   └── Makefile        # Build rules
└── build/
    └── (build artifacts go here)
```

### Step 2: Toolchain Verification

- The `arm-none-eabi-gcc` compiler must be callable from PATH.
- `/app/toolchain/info.txt` must contain the output of `arm-none-eabi-gcc --version` (first line must contain the string `arm-none-eabi-gcc`).

### Step 3: Minimal Register Definitions Header

Create `/app/firmware/include/stm32f407.h` with at minimum:

- Base addresses for RCC and GPIOD peripherals (as used on STM32F407 Discovery board)
- Register definitions needed to enable the GPIOD clock and configure/toggle at least one pin (PD12–PD15 are the onboard LEDs)
- Use `volatile uint32_t *` or a register struct approach
- Include a standard include guard

### Step 4: Blinky Firmware (`/app/firmware/src/main.c`)

Write a bare-metal C program that:

1. Defines a vector table with at least the initial stack pointer and reset handler entries
2. Implements a `Reset_Handler` function as the entry point
3. Enables the GPIOD peripheral clock via RCC->AHB1ENR
4. Configures at least one of PD12–PD15 as a general-purpose push-pull output
5. Enters an infinite loop that toggles the configured LED pin(s) with a software delay
6. The initial stack pointer must be set to the end of SRAM (0x20020000 for STM32F407 with 128KB SRAM)

### Step 5: Linker Script (`/app/firmware/linker.ld`)

The linker script must define:

- MEMORY regions for FLASH (origin 0x08000000, length 1024K) and RAM (origin 0x20000000, length 128K)
- SECTIONS placing `.isr_vector` at the start of FLASH
- `.text`, `.rodata` in FLASH
- `.data` (with load address in FLASH, VMA in RAM) and `.bss` in RAM
- An ENTRY point symbol (e.g., `Reset_Handler`)

### Step 6: Makefile (`/app/firmware/Makefile`)

The Makefile must:

- Use `arm-none-eabi-gcc` as the compiler and `arm-none-eabi-objcopy` / `arm-none-eabi-objdump` / `arm-none-eabi-size` as needed
- Set compiler flags that target Cortex-M4 with hardware FPU: `-mcpu=cortex-m4 -mthumb -mfloat-abi=hard -mfpu=fpv4-sp-d16`
- Have a default target that produces the ELF at `/app/build/blinky.elf`
- Have a `bin` target that produces `/app/build/blinky.bin` (raw binary via objcopy)
- Have a `size` target that prints section sizes
- Have a `clean` target
- Use the linker script at `/app/firmware/linker.ld` via `-T`

### Step 7: Build and Validate

Run `make` from `/app/firmware/` so that:

- `/app/build/blinky.elf` is produced without errors
- `/app/build/blinky.bin` is produced (run the `bin` target)
- The ELF file passes these checks:
  - `arm-none-eabi-readelf -h /app/build/blinky.elf` shows `Machine: ARM`
  - `arm-none-eabi-readelf -A /app/build/blinky.elf` shows attributes indicating Cortex-M4 and hard-float (Tag_CPU_name: Cortex-M4, Tag_FP_arch or Tag_ABI_VFP_args present)
  - `arm-none-eabi-objdump -d /app/build/blinky.elf` contains at least one VFP/FPU-related instruction or the `.text` section is non-empty with Thumb instructions
  - The `.isr_vector` section exists and starts at address 0x08000000
  - The ELF entry point is the address of `Reset_Handler`
- Save the output of `arm-none-eabi-readelf -A /app/build/blinky.elf` to `/app/build/readelf_attributes.txt`
- Save the output of `arm-none-eabi-size /app/build/blinky.elf` to `/app/build/size_output.txt`
