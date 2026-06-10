## Cross-Architecture Docker-Static Binary Builder

Use a minimal Alpine container to build a statically-linked, stripped Linux x86-64 executable, then extract it and verify its portability on the host.

### Technical Requirements

- Language: C
- Build environment: Docker with Alpine Linux (version-pinned tag)
- Target: x86-64 Linux static ELF binary
- Working directory: `/app`

### File Structure

Create the following files under `/app`:

1. **`/app/main.c`** — A C source file that:
   - Prints exactly `Hello static world!` as the first line to stdout (followed by a newline)
   - Prints the build timestamp on a second line (format is flexible, but must include a compile-time timestamp such as `__DATE__` or `__TIME__`)

2. **`/app/Dockerfile`** — A multi-stage Dockerfile that:
   - Uses a version-pinned Alpine image as the build stage (e.g., `alpine:3.XX`, not `alpine:latest`)
   - Installs a C compiler (e.g., `gcc`, `musl-dev`) in the build stage
   - Compiles `main.c` into a statically-linked, stripped binary named `hello_static`
   - Uses a minimal final stage (e.g., `scratch` or pinned Alpine) and copies only the `hello_static` binary into it

3. **`/app/hello_static`** — The final extracted binary, copied out of the Docker image onto the host filesystem. This binary must satisfy all of the following:
   - It is a valid ELF 64-bit x86-64 executable (verifiable via `file hello_static`)
   - It is statically linked (`ldd hello_static` must report "not a dynamic executable" or "statically linked")
   - It is stripped (the `file` output must contain the word `stripped`)
   - When executed (`./hello_static`), the first line of stdout is exactly: `Hello static world!`

4. **`/app/build.sh`** — A shell script that performs the full reproducible pipeline:
   - Builds the Docker image from the Dockerfile
   - Extracts the `hello_static` binary from the built image to `/app/hello_static`
   - Makes the binary executable
   - The script must be executable (`chmod +x build.sh`) and run successfully with `bash build.sh`

### Verification Criteria

- `file /app/hello_static` output contains: `ELF 64-bit`, `x86-64`, and `stripped`
- `ldd /app/hello_static` indicates the binary is not dynamically linked
- `/app/hello_static` runs on the host and its first output line is exactly `Hello static world!`
- `/app/Dockerfile` uses a pinned Alpine version tag (not `latest`)
- `/app/build.sh` exists and is executable
