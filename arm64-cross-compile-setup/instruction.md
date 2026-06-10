## Cross-Compilation Toolchain Setup for ARM64 on x86_64

Set up a cross-compilation environment on an x86_64 host to build ARM64 (AArch64) binaries, then compile multiple C programs and verify they target the correct architecture.

### Technical Requirements

- Language: C (compiled with an aarch64 cross-compiler, e.g., `aarch64-linux-gnu-gcc`)
- Host: x86_64 Linux
- Target: AArch64 (ARM64) Linux
- Install any necessary cross-compilation packages (e.g., `gcc-aarch64-linux-gnu`, `binutils-aarch64-linux-gnu`)

### Directory Structure

Create the following directory layout under `/app`:

```
/app/
├── toolchain_env.sh
├── src/
│   ├── hello.c
│   └── mathlib.c
├── include/
│   └── mathlib.h
├── build/
│   ├── hello_arm64
│   ├── libmathlib.a
│   └── calc_arm64
└── report.json
```

### Step-by-Step Tasks

1. **Install cross-compilation tools**: Install the aarch64-linux-gnu cross-compiler and associated binutils on the x86_64 host.

2. **Create `/app/toolchain_env.sh`**: A shell script that exports the following environment variables:
   - `CROSS_COMPILE` — set to the cross-compiler prefix (e.g., `aarch64-linux-gnu-`)
   - `CC` — set to the full cross-compiler command (e.g., `aarch64-linux-gnu-gcc`)
   - `AR` — set to the cross-archiver (e.g., `aarch64-linux-gnu-ar`)
   - `ARCH` — set to `arm64`
   - `TARGET_TRIPLE` — set to `aarch64-unknown-linux-gnu`

   The script must be sourceable (i.e., `source /app/toolchain_env.sh` sets the variables in the current shell).

3. **Create `/app/src/hello.c`**: A simple C program that prints exactly `Hello from ARM64 cross-compilation!` to stdout (followed by a newline) and returns 0.

4. **Create `/app/include/mathlib.h` and `/app/src/mathlib.c`**: A small static math library:
   - `mathlib.h` declares two functions:
     - `int math_add(int a, int b);`
     - `int math_multiply(int a, int b);`
   - `mathlib.c` implements these functions (addition and multiplication respectively).

5. **Cross-compile `/app/build/hello_arm64`**: Compile `hello.c` into an ARM64 ELF binary at `/app/build/hello_arm64`.

6. **Build static library `/app/build/libmathlib.a`**: Cross-compile `mathlib.c` into an object file, then archive it into a static library at `/app/build/libmathlib.a` using the cross-archiver.

7. **Create and cross-compile a calculator program `/app/build/calc_arm64`**: Write a program (source location is up to you) that uses `mathlib.h`, calls `math_add(3, 4)` and `math_multiply(5, 6)`, prints the results in the exact format below, and returns 0:
   ```
   add(3,4) = 7
   multiply(5,6) = 30
   ```
   Link it against `libmathlib.a` and output the binary at `/app/build/calc_arm64`.

8. **Generate `/app/report.json`**: A JSON file containing verification results with the following structure:
   ```json
   {
     "host_arch": "<output of uname -m>",
     "cross_compiler": "<full path to the cross-compiler binary>",
     "cross_compiler_version": "<first line of the cross-compiler --version output>",
     "hello_arm64": {
       "file_type": "<output of file command on hello_arm64>",
       "is_aarch64": true
     },
     "libmathlib": {
       "file_type": "<output of file command on libmathlib.a>",
       "contents": "<output of ar t on libmathlib.a>"
     },
     "calc_arm64": {
       "file_type": "<output of file command on calc_arm64>",
       "is_aarch64": true
     }
   }
   ```
   - `is_aarch64` must be `true` (boolean) if the corresponding `file_type` string contains `aarch64` or `ARM aarch64`.
   - All string values must be actual command outputs, not placeholders.
