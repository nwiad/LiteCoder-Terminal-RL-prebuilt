## Embedded Rust Build System with Cargo Integration

Set up a complete embedded Rust build system for an ARM Cortex-M4 (STM32F4) microcontroller project under `/app/firmware/`, including cargo configuration, custom linker scripts, build profiles, C library integration via build.rs, conditional compilation features, and build automation scripts.

### Technical Requirements

- Language: Rust (with a `build.rs` build script in Rust)
- Shell scripts: Bash
- All project files must be created under `/app/firmware/`

### Project Structure

Create the following directory layout and files:

```
/app/firmware/
├── Cargo.toml
├── build.rs
├── memory.x
├── .cargo/
│   └── config.toml
├── src/
│   ├── main.rs
│   └── lib.rs
├── vendor/
│   └── stm32f4_hal.h
├── openocd.cfg
└── scripts/
    ├── build.sh
    ├── flash.sh
    └── clean.sh
```

### File Specifications

#### 1. `Cargo.toml`

- Package name: `stm32f4-firmware`
- Edition: `2021`
- Must define two profiles:
  - `[profile.dev]`: set `opt-level = 1` and `debug = true`
  - `[profile.release]`: set `opt-level = "z"`, `lto = true`, and `debug = false`
- Must define a `[features]` section with at least these features:
  - `default = ["logging"]`
  - `logging` (no dependencies)
  - `dma` (no dependencies)
- Must include a `[[bin]]` entry with name `stm32f4-firmware` and path `src/main.rs`
- Must include a `[dependencies]` section (may be empty or contain embedded crates)
- Must include a `[build-dependencies]` section containing `cc` with version `"1"` (i.e., `cc = "1"`)

#### 2. `.cargo/config.toml`

- Must set the default build target to `thumbv7em-none-eabihf` under `[build]`
- Must define a runner under `[target.thumbv7em-none-eabihf]` section with a runner command string that references `openocd`
- Must include `[target.thumbv7em-none-eabihf]` section with rustflags that include at minimum:
  - `-C link-arg=-Tmemory.x`

#### 3. `memory.x` (Linker Script)

- Must define a `MEMORY` block with at least two regions:
  - `FLASH`: origin `0x08000000`, length `1024K`
  - `RAM`: origin `0x20000000`, length `128K`
- Must define a `SECTIONS` block that includes at minimum:
  - `.text` section placed in `FLASH`
  - `.data` section placed in `RAM` (with load address in `FLASH`, i.e., `AT>FLASH` or equivalent)
  - `.bss` section placed in `RAM`
- Must define the `_stack_start` symbol set to the end of RAM (`0x20000000 + 128K = 0x20020000`)

#### 4. `build.rs`

- Must use the `cc` crate to compile a C source file
- Must call `println!("cargo:rerun-if-changed=vendor/stm32f4_hal.h");`
- Must call `println!("cargo:rerun-if-changed=build.rs");`
- Must add the `vendor/` directory as an include path for the C compilation

#### 5. `vendor/stm32f4_hal.h`

- A C header file with at least:
  - An include guard (`#ifndef` / `#define` / `#endif`)
  - A `#define` for `STM32F4_CLOCK_FREQ` set to `168000000`
  - A function declaration: `void hal_init(void);`
  - A function declaration: `uint32_t hal_get_tick(void);`

#### 6. `src/main.rs`

- Must include `#![no_std]` and `#![no_main]` attributes
- Must use conditional compilation: a block gated on `#[cfg(feature = "logging")]`
- Must define a panic handler function (annotated with `#[panic_handler]`)
- Must define an entry point function (e.g., `main` or a function annotated with an entry attribute)

#### 7. `src/lib.rs`

- Must include `#![no_std]`
- Must contain a public function `pub fn init()`
- Must contain a public module or public function gated on `#[cfg(feature = "dma")]`

#### 8. `openocd.cfg`

- Must specify an interface (e.g., `source [find interface/stlink.cfg]` or similar)
- Must specify a target (e.g., `source [find target/stm32f4x.cfg]` or similar)
- Must include a `program` or `flash write_image` command sequence for flashing firmware
- Must include a `reset` command

#### 9. `scripts/build.sh`

- Must be executable (or at minimum start with `#!/bin/bash` or `#!/usr/bin/env bash`)
- Must support at least two modes invoked via a command-line argument:
  - `debug` — runs `cargo build`
  - `release` — runs `cargo build --release`
- Must print a usage message if called with no arguments or an unrecognized argument

#### 10. `scripts/flash.sh`

- Must be executable (shebang line required)
- Must invoke `openocd` with a reference to `openocd.cfg`
- Must accept an optional argument to choose between debug and release binary paths

#### 11. `scripts/clean.sh`

- Must be executable (shebang line required)
- Must run `cargo clean`
- Must print a confirmation message after cleaning (e.g., "Clean complete" or similar)
