## Build and Static-Link a Minimal C TCP Echo Server

Create a statically-linked, self-contained TCP echo server in C for x86-64 Linux. The server listens on a configurable port, echoes back any data received from a client, and can run on any Linux host without shared library dependencies.

### Technical Requirements

- Language: C (compiled with GCC)
- Target: x86-64 Linux ELF executable
- Linking: Fully static (no dynamic library dependencies)

### File Structure

All files must be located under `/app/`:

- `/app/echo_server.c` — The C source file for the TCP echo server.
- `/app/echo_server` — The compiled, statically-linked ELF binary.
- `/app/Makefile` — A Makefile that builds `echo_server` from `echo_server.c` with a default `all` target. The Makefile must also include a `clean` target that removes the binary.
- `/app/build_flags.txt` — A plain text file containing the exact GCC compilation command used to produce the binary (a single line, e.g., `gcc -static -o echo_server echo_server.c ...`).

### Server Behavior

1. The server must accept a port number as its first command-line argument (e.g., `./echo_server 7777`). If no argument is provided, it must default to port `7`.
2. The server must listen on `0.0.0.0` (all interfaces) using TCP over IPv4.
3. For each accepted client connection, the server must read data and echo it back verbatim until the client closes the connection.
4. The server must handle at least one concurrent client connection. It is acceptable (but not required) to handle multiple clients simultaneously.
5. The server must run in the foreground by default. It should exit cleanly on `SIGINT` or `SIGTERM`.

### Binary Requirements

1. The compiled binary `/app/echo_server` must be a valid ELF 64-bit executable for x86-64.
2. The binary must be fully statically linked:
   - `ldd echo_server` must report "not a dynamic executable" (or "statically linked").
   - `readelf -d echo_server` must show no `NEEDED` entries (no shared library dependencies).
3. The binary must have its executable permission bit set.

### Makefile Requirements

- Running `make` (or `make all`) inside `/app/` must compile `echo_server.c` into the static binary `/app/echo_server`.
- Running `make clean` must remove `/app/echo_server`.
- The Makefile must use the `-static` flag for GCC linking.

### Echo Verification

When the server is running on a given port (e.g., 7777):
- Sending the string `hello\n` via a TCP client (e.g., `echo "hello" | nc localhost 7777`) must return `hello\n` exactly.
- Sending multiple lines must return each line echoed back in order.
- Sending an empty connection (connect then immediately disconnect) must not crash the server.
