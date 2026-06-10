## Build GNU libc (glibc) from Source and Run a Custom C Program Against It

Compile GNU libc (glibc) from source, install it to a custom prefix, then write and execute a custom C program that links against this newly built glibc.

### Requirements

1. **Install build dependencies** required to compile glibc (e.g., gcc, make, gawk, bison, etc.).

2. **Download glibc source**: Download glibc version **2.38** source tarball from a GNU mirror (e.g., `https://ftp.gnu.org/gnu/glibc/glibc-2.38.tar.gz`). Extract it under `/app/`.

3. **Build glibc**:
   - Create a separate build directory `/app/glibc-build/`.
   - Configure with prefix `/opt/glibc`, enable minimum kernel version `5.4.0`, and use `-O2` optimization level.
   - Compile using `make` with 4 parallel jobs (`-j4`).
   - Install to `/opt/glibc`.

4. **Write a test C program** at `/app/test_glibc.c` that does all of the following:
   - Uses `malloc` to allocate memory, writes a string into it, and prints it with `printf`.
   - Creates a POSIX thread using `pthread_create` that prints a message from the new thread.
   - The main thread joins the spawned thread before exiting.
   - The program must print the following **exact lines** to stdout (order matters):
     ```
     malloc test: Hello from custom glibc!
     thread test: Hello from pthread!
     all tests passed
     ```

5. **Compile the test program**:
   - Compile `/app/test_glibc.c` to produce the binary `/app/test_glibc`.
   - Link against the custom glibc at `/opt/glibc` — specify the custom dynamic linker (`/opt/glibc/lib/ld-linux-x86-64.so.2`) and library paths so the binary does **not** use the system default glibc.
   - Link with `-lpthread`.

6. **Run the test program**:
   - Execute `/app/test_glibc` using the custom dynamic loader from `/opt/glibc`.
   - Save the program's stdout output to `/app/output.txt`.

7. **Verify linkage**:
   - Run `ldd` (or equivalent) on `/app/test_glibc` and save the output to `/app/ldd_output.txt`.
   - The ldd output must show that `libc.so.6` and `libpthread.so.0` (or equivalent) resolve to paths under `/opt/glibc`, **not** the system default paths (e.g., not `/lib/x86_64-linux-gnu/`).

### Output Files

| File | Description |
|---|---|
| `/app/test_glibc.c` | The C source file |
| `/app/test_glibc` | The compiled binary |
| `/app/output.txt` | Stdout from running the test program |
| `/app/ldd_output.txt` | Output of `ldd /app/test_glibc` |
| `/opt/glibc/` | The custom glibc installation directory |

### Verification Criteria

- `/opt/glibc/lib/libc.so.6` exists.
- `/opt/glibc/lib/ld-linux-x86-64.so.2` (or equivalent loader) exists.
- `/app/test_glibc` is an executable ELF binary.
- `/app/output.txt` contains exactly the three expected lines.
- `/app/ldd_output.txt` shows `libc.so.6` resolving to a path under `/opt/glibc`.
