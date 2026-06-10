## Build and Statically Link musl libc

Build musl libc from source, install it to a local prefix, and compile a statically-linked "Hello World" C program using the musl toolchain.

### Requirements

1. **Download and build musl libc from source:**
   - Download a stable musl libc source release (version 1.2.x or later) from https://musl.libc.org/.
   - Configure musl with the install prefix set to `/app/musl-install`.
   - Compile and install musl to that prefix. After installation, the musl-gcc wrapper script must exist at `/app/musl-install/bin/musl-gcc`.

2. **Write a Hello World C program:**
   - Create the file `/app/hello.c`.
   - The program must print exactly `Hello, musl!` followed by a newline to stdout and exit with code 0.

3. **Compile a statically-linked binary:**
   - Using the musl-gcc wrapper from the local install, compile `/app/hello.c` into a statically-linked ELF binary at `/app/hello`.
   - The binary must be linked with the `-static` flag.

4. **Verification artifacts:**
   - The compiled binary `/app/hello` must execute successfully and produce the exact output: `Hello, musl!\n` (a single line with a trailing newline).
   - The binary must be a statically-linked ELF executable (i.e., `file /app/hello` should report "statically linked" and `ldd /app/hello` should report "not a dynamic executable" or similar).

### Expected File Layout

After completion, the following paths must exist:

- `/app/musl-install/bin/musl-gcc` — the musl-gcc compiler wrapper
- `/app/musl-install/lib/libc.a` — the built musl static C library
- `/app/hello.c` — the C source file
- `/app/hello` — the statically-linked ELF binary

### Output Specification

Running `/app/hello` must produce exactly:
```
Hello, musl!
```
