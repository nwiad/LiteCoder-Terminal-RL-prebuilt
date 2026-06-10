## Custom Linker Script Creation for ARM Cortex-M4

Create a custom GNU LD linker script and a companion C test program for an ARM Cortex-M4 microcontroller board. The linker script must correctly define memory regions, place code/data sections, define peripheral mappings, and export symbols needed for runtime initialization.

### Technical Requirements

- Toolchain: `arm-none-eabi-gcc` / `arm-none-eabi-ld`
- Linker script file: `/app/linker.ld`
- Test C program file: `/app/test_program.c`

### Memory Layout

The linker script must define a `MEMORY` block with the following regions:

| Region  | Origin       | Length  |
|---------|-------------|---------|
| FLASH   | 0x08000000  | 512K    |
| RAM     | 0x20000000  | 128K    |

### Peripheral Memory-Mapped Regions

Define the following peripheral base addresses as symbols in the linker script (outside of MEMORY, using `PROVIDE` or direct symbol assignment):

| Peripheral | Base Address | Size   |
|------------|-------------|--------|
| GPIO       | 0x40020000  | 0x400  |
| UART       | 0x40011000  | 0x400  |
| TIMER      | 0x40000400  | 0x400  |

The symbols must be named exactly: `_GPIO_BASE`, `_UART_BASE`, `_TIMER_BASE`.

### Section Requirements

The `SECTIONS` block must define the following sections in this order, placed into the correct memory regions:

1. `.isr_vector` — Placed at the very beginning of FLASH. Must contain the vector table. Aligned to 4 bytes.
2. `.text` — Code section, placed in FLASH after `.isr_vector`. Aligned to 4 bytes.
3. `.rodata` — Read-only data, placed in FLASH after `.text`. Aligned to 4 bytes.
4. `.data` — Initialized data. Load address (LMA) in FLASH, virtual address (VMA) in RAM. Aligned to 4 bytes.
5. `.bss` — Uninitialized data, placed in RAM after `.data`. Aligned to 4 bytes.

### Required Linker Symbols

The linker script must define (via `. =` or `PROVIDE`) the following symbols for use by startup code:

- `_stext` — Start of `.text`
- `_etext` — End of `.text`
- `_sdata` — Start of `.data` (VMA in RAM)
- `_edata` — End of `.data` (VMA in RAM)
- `_sidata` — Load address of `.data` (LMA in FLASH)
- `_sbss` — Start of `.bss`
- `_ebss` — End of `.bss`
- `_estack` — Initial stack pointer, set to the end of RAM (0x20000000 + 128K = 0x20020000)

### Test Program (`test_program.c`)

Create a minimal C file that exercises the linker script. It must include:

- A vector table array placed in the `.isr_vector` section (using `__attribute__((section(".isr_vector")))`). The first entry must be the stack pointer (`&_estack`), and the second entry must be the `Reset_Handler` function pointer.
- A `Reset_Handler` function (can be minimal/empty loop).
- At least one initialized global variable (to populate `.data`).
- At least one uninitialized global variable (to populate `.bss`).
- `extern` declarations referencing the peripheral base symbols (`_GPIO_BASE`, `_UART_BASE`, `_TIMER_BASE`).

### Compilation Verification

The following command must succeed without errors:

```
arm-none-eabi-gcc -nostdlib -T linker.ld -o test_program.elf test_program.c
```

After compilation, the resulting ELF must satisfy:

- `.isr_vector` starts at address `0x08000000`.
- `.text` resides within FLASH (between `0x08000000` and `0x08080000`).
- `.data` VMA resides within RAM (between `0x20000000` and `0x20020000`).
- `.bss` VMA resides within RAM.
- The symbol `_estack` equals `0x20020000`.
- The symbols `_GPIO_BASE`, `_UART_BASE`, `_TIMER_BASE` equal `0x40020000`, `0x40011000`, `0x40000400` respectively.
