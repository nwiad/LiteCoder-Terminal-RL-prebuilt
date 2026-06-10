"""
Tests for the static C TCP echo server task.

Verifies:
- File existence and structure under /app/
- Binary is a valid ELF 64-bit statically-linked executable
- Makefile has correct targets and uses -static
- build_flags.txt contains the correct GCC command
- Echo server actually echoes data back verbatim
- Server handles empty connections gracefully
- Server exits cleanly on SIGTERM
"""

import os
import subprocess
import time
import signal
import socket
import stat

APP_DIR = "/app"
BINARY = os.path.join(APP_DIR, "echo_server")
SOURCE = os.path.join(APP_DIR, "echo_server.c")
MAKEFILE = os.path.join(APP_DIR, "Makefile")
BUILD_FLAGS = os.path.join(APP_DIR, "build_flags.txt")

# Use a high port to avoid permission issues
TEST_PORT = 17321


# ============================================================
# Helper functions
# ============================================================

def start_server(port=TEST_PORT, timeout=3):
    """Start the echo server in the background and wait for it to be ready."""
    proc = subprocess.Popen(
        [BINARY, str(port)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    # Wait for the server to start listening
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.5)
            s.connect(("127.0.0.1", port))
            s.close()
            return proc
        except (ConnectionRefusedError, OSError):
            time.sleep(0.1)
    # If we get here, server didn't start
    proc.kill()
    proc.wait()
    raise RuntimeError(f"Server did not start on port {port} within {timeout}s")


def stop_server(proc, sig=signal.SIGTERM, timeout=3):
    """Stop the server process."""
    if proc.poll() is None:
        proc.send_signal(sig)
        try:
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()


def send_tcp(data: bytes, port=TEST_PORT, timeout=3) -> bytes:
    """Send data to the echo server and return the response."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    s.connect(("127.0.0.1", port))
    s.sendall(data)
    # Shutdown write side so server sees EOF and echoes back
    s.shutdown(socket.SHUT_WR)
    chunks = []
    while True:
        try:
            chunk = s.recv(4096)
            if not chunk:
                break
            chunks.append(chunk)
        except socket.timeout:
            break
    s.close()
    return b"".join(chunks)


# ============================================================
# 1. File existence tests
# ============================================================

class TestFileExistence:
    def test_source_file_exists(self):
        assert os.path.isfile(SOURCE), f"Source file {SOURCE} does not exist"

    def test_binary_exists(self):
        assert os.path.isfile(BINARY), f"Binary {BINARY} does not exist"

    def test_makefile_exists(self):
        assert os.path.isfile(MAKEFILE), f"Makefile {MAKEFILE} does not exist"

    def test_build_flags_exists(self):
        assert os.path.isfile(BUILD_FLAGS), f"build_flags.txt {BUILD_FLAGS} does not exist"

    def test_source_file_not_empty(self):
        assert os.path.getsize(SOURCE) > 50, "echo_server.c is suspiciously small"

    def test_binary_not_empty(self):
        assert os.path.getsize(BINARY) > 1000, "echo_server binary is suspiciously small"


# ============================================================
# 2. Binary property tests
# ============================================================

class TestBinaryProperties:
    def test_binary_is_elf_64bit(self):
        """Binary must be a valid ELF 64-bit executable for x86-64."""
        result = subprocess.run(
            ["file", BINARY], capture_output=True, text=True
        )
        output = result.stdout.lower()
        assert "elf" in output, f"Binary is not an ELF file: {result.stdout}"
        assert "64-bit" in output, f"Binary is not 64-bit: {result.stdout}"

    def test_binary_is_executable(self):
        """Binary must have executable permission bit set."""
        mode = os.stat(BINARY).st_mode
        assert mode & stat.S_IXUSR, "Binary does not have user execute permission"

    def test_binary_is_statically_linked_ldd(self):
        """ldd must report 'not a dynamic executable' or 'statically linked'."""
        result = subprocess.run(
            ["ldd", BINARY], capture_output=True, text=True
        )
        combined = (result.stdout + result.stderr).lower()
        assert (
            "not a dynamic executable" in combined
            or "statically linked" in combined
            or "not a dynamic" in combined  # some ldd versions
        ), f"Binary appears to be dynamically linked: {combined}"

    def test_binary_no_needed_entries(self):
        """readelf -d must show no NEEDED entries (no shared lib deps)."""
        result = subprocess.run(
            ["readelf", "-d", BINARY], capture_output=True, text=True
        )
        combined = (result.stdout + result.stderr).lower()
        # A fully static binary either has no dynamic section or no NEEDED
        has_no_dynamic = (
            "there is no dynamic section" in combined
            or "not a dynamic" in combined
        )
        has_needed = "needed" in combined
        assert has_no_dynamic or not has_needed, (
            f"Binary has NEEDED entries (dynamic deps): {result.stdout}"
        )


# ============================================================
# 3. Source code tests
# ============================================================

class TestSourceCode:
    def test_source_includes_socket(self):
        """Source must include socket-related headers."""
        with open(SOURCE, "r") as f:
            content = f.read()
        assert "socket" in content.lower(), "Source doesn't reference sockets"

    def test_source_includes_main(self):
        """Source must have a main function."""
        with open(SOURCE, "r") as f:
            content = f.read()
        assert "main" in content, "Source doesn't contain a main function"

    def test_source_has_echo_logic(self):
        """Source must have read/write or recv/send for echo logic."""
        with open(SOURCE, "r") as f:
            content = f.read().lower()
        has_rw = "read" in content and "write" in content
        has_rs = "recv" in content and "send" in content
        assert has_rw or has_rs, "Source doesn't contain read/write or recv/send"


# ============================================================
# 4. Makefile tests
# ============================================================

class TestMakefile:
    def test_makefile_has_static_flag(self):
        """Makefile must use -static flag."""
        with open(MAKEFILE, "r") as f:
            content = f.read()
        assert "-static" in content, "Makefile does not contain -static flag"

    def test_makefile_has_all_target(self):
        """Makefile must have an 'all' target."""
        with open(MAKEFILE, "r") as f:
            content = f.read()
        assert "all" in content, "Makefile does not have 'all' target"

    def test_makefile_has_clean_target(self):
        """Makefile must have a 'clean' target."""
        with open(MAKEFILE, "r") as f:
            content = f.read()
        assert "clean" in content, "Makefile does not have 'clean' target"

    def test_make_clean_removes_binary(self):
        """'make clean' must remove the binary, 'make all' must rebuild it."""
        # Run make clean
        result = subprocess.run(
            ["make", "clean"], capture_output=True, text=True, cwd=APP_DIR
        )
        assert result.returncode == 0, f"make clean failed: {result.stderr}"
        assert not os.path.isfile(BINARY), "Binary still exists after make clean"

        # Rebuild
        result = subprocess.run(
            ["make", "all"], capture_output=True, text=True, cwd=APP_DIR
        )
        assert result.returncode == 0, f"make all failed: {result.stderr}"
        assert os.path.isfile(BINARY), "Binary not created after make all"

# ============================================================
# 5. build_flags.txt tests
# ============================================================

class TestBuildFlags:
    def test_build_flags_contains_static(self):
        """build_flags.txt must contain -static."""
        with open(BUILD_FLAGS, "r") as f:
            content = f.read().strip()
        assert "-static" in content, "build_flags.txt does not contain -static"

    def test_build_flags_contains_gcc(self):
        """build_flags.txt must reference gcc."""
        with open(BUILD_FLAGS, "r") as f:
            content = f.read().strip().lower()
        assert "gcc" in content, "build_flags.txt does not reference gcc"

    def test_build_flags_references_source(self):
        """build_flags.txt must reference the source file."""
        with open(BUILD_FLAGS, "r") as f:
            content = f.read().strip()
        assert "echo_server.c" in content, (
            "build_flags.txt does not reference echo_server.c"
        )

    def test_build_flags_references_output(self):
        """build_flags.txt must reference the output binary name."""
        with open(BUILD_FLAGS, "r") as f:
            content = f.read().strip()
        # Should contain -o echo_server or -o ./echo_server
        assert "echo_server" in content, (
            "build_flags.txt does not reference echo_server output"
        )

    def test_build_flags_is_single_line(self):
        """build_flags.txt should be a single command line."""
        with open(BUILD_FLAGS, "r") as f:
            lines = [l for l in f.read().strip().splitlines() if l.strip()]
        assert len(lines) >= 1, "build_flags.txt is empty"
        # Allow 1-2 lines (some may add a trailing newline or comment)
        assert len(lines) <= 3, (
            f"build_flags.txt has too many lines ({len(lines)}), expected a single command"
        )


# ============================================================
# 6. Echo server functional tests
# ============================================================

class TestEchoFunctionality:
    """Functional tests that start the server and verify echo behavior."""

    @classmethod
    def setup_class(cls):
        """Start the echo server once for all tests in this class."""
        cls.proc = start_server(port=TEST_PORT)

    @classmethod
    def teardown_class(cls):
        """Stop the echo server."""
        stop_server(cls.proc)

    def test_echo_simple_string(self):
        """Sending 'hello\\n' must return 'hello\\n' exactly."""
        response = send_tcp(b"hello\n")
        assert response == b"hello\n", (
            f"Expected b'hello\\n', got {response!r}"
        )

    def test_echo_multiple_lines(self):
        """Sending multiple lines must return them all echoed in order."""
        data = b"line1\nline2\nline3\n"
        response = send_tcp(data)
        assert response == data, (
            f"Multi-line echo mismatch.\nExpected: {data!r}\nGot: {response!r}"
        )

    def test_echo_large_payload(self):
        """Sending a larger payload must be echoed back verbatim."""
        data = b"A" * 2048 + b"\n"
        response = send_tcp(data)
        assert response == data, (
            f"Large payload echo mismatch. "
            f"Expected {len(data)} bytes, got {len(response)} bytes"
        )

    def test_echo_binary_data(self):
        """Sending binary (non-text) data must be echoed back verbatim."""
        data = bytes(range(256))
        response = send_tcp(data)
        assert response == data, (
            f"Binary echo mismatch. "
            f"Expected {len(data)} bytes, got {len(response)} bytes"
        )

    def test_echo_empty_string(self):
        """Sending empty data (connect then disconnect) must not crash server."""
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        s.connect(("127.0.0.1", TEST_PORT))
        s.close()
        # Server should still be alive — verify by sending another message
        time.sleep(0.2)
        response = send_tcp(b"still alive\n")
        assert response == b"still alive\n", (
            f"Server crashed after empty connection. Got: {response!r}"
        )

    def test_echo_no_trailing_newline(self):
        """Sending data without trailing newline must echo it back exactly."""
        data = b"no newline at end"
        response = send_tcp(data)
        assert response == data, (
            f"Expected {data!r}, got {response!r}"
        )


# ============================================================
# 7. Server signal handling test
# ============================================================

class TestServerSignalHandling:
    def test_server_exits_on_sigterm(self):
        """Server must exit cleanly on SIGTERM."""
        port = TEST_PORT + 1
        proc = start_server(port=port)
        proc.send_signal(signal.SIGTERM)
        try:
            retcode = proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
            assert False, "Server did not exit within 5s after SIGTERM"
        # Clean exit means return code 0 or killed by signal (negative)
        assert retcode == 0 or retcode == -signal.SIGTERM, (
            f"Server exited with unexpected code {retcode} after SIGTERM"
        )

    def test_server_accepts_port_argument(self):
        """Server must accept a port number as first argument."""
        port = TEST_PORT + 2
        proc = start_server(port=port)
        try:
            response = send_tcp(b"port test\n", port=port)
            assert response == b"port test\n", (
                f"Echo on custom port failed. Got: {response!r}"
            )
        finally:
            stop_server(proc)
