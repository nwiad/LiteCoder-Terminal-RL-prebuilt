"""
Tests for cross-compile-arm-busybox task.

Validates that /app/output/busybox-armv7 is a fully-static, ELF 32-bit ARM
binary that runs correctly under QEMU user-mode emulation with the required
applets present.
"""

import os
import stat
import subprocess
import shutil

BINARY_PATH = "/app/output/busybox-armv7"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_qemu_arm():
    """Return the path to a working qemu-arm binary, or None."""
    for name in ("qemu-arm-static", "qemu-arm"):
        path = shutil.which(name)
        if path:
            return path
    return None


def _file_output(path):
    """Return the output of `file <path>` as a string."""
    result = subprocess.run(
        ["file", path],
        capture_output=True,
        text=True,
        timeout=30,
    )
    return result.stdout + result.stderr


def _run_qemu(qemu_bin, binary, *args, timeout=30):
    """Run the binary under QEMU and return combined stdout+stderr."""
    result = subprocess.run(
        [qemu_bin, binary, *args],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return result.stdout + result.stderr


# ---------------------------------------------------------------------------
# Test 0: File existence and non-trivial size
# ---------------------------------------------------------------------------

class TestBinaryExists:
    def test_file_exists(self):
        """The output binary must exist at the specified path."""
        assert os.path.isfile(BINARY_PATH), (
            f"Binary not found at {BINARY_PATH}"
        )

    def test_file_not_empty(self):
        """The binary must not be an empty file."""
        assert os.path.isfile(BINARY_PATH), f"Binary not found at {BINARY_PATH}"
        size = os.path.getsize(BINARY_PATH)
        assert size > 0, "Binary file is empty (0 bytes)"

    def test_file_minimum_size(self):
        """A real BusyBox static ARM binary should be at least 100 KB."""
        assert os.path.isfile(BINARY_PATH), f"Binary not found at {BINARY_PATH}"
        size = os.path.getsize(BINARY_PATH)
        min_size = 100 * 1024  # 100 KB
        assert size >= min_size, (
            f"Binary is only {size} bytes; a real static BusyBox should be "
            f"at least {min_size} bytes"
        )


# ---------------------------------------------------------------------------
# Test 1: ELF format for ARM
# ---------------------------------------------------------------------------

class TestELFFormat:
    def test_is_elf(self):
        """file output must indicate an ELF file."""
        output = _file_output(BINARY_PATH)
        assert "ELF" in output, (
            f"Binary is not an ELF file. file output: {output}"
        )

    def test_is_32bit(self):
        """file output must indicate a 32-bit binary."""
        output = _file_output(BINARY_PATH)
        assert "32-bit" in output, (
            f"Binary is not 32-bit. file output: {output}"
        )

    def test_is_arm(self):
        """file output must indicate ARM architecture."""
        output = _file_output(BINARY_PATH)
        assert "ARM" in output, (
            f"Binary does not target ARM. file output: {output}"
        )

    def test_is_executable_elf(self):
        """file output must indicate it is an executable (not shared lib / relocatable)."""
        output = _file_output(BINARY_PATH)
        output_lower = output.lower()
        assert "executable" in output_lower or "exec" in output_lower, (
            f"Binary is not an executable ELF. file output: {output}"
        )


# ---------------------------------------------------------------------------
# Test 2: Statically linked
# ---------------------------------------------------------------------------

class TestStaticLinking:
    def test_statically_linked(self):
        """file output must contain 'statically linked'."""
        output = _file_output(BINARY_PATH)
        assert "statically linked" in output, (
            f"Binary is not statically linked. file output: {output}"
        )

    def test_no_dynamic_section(self):
        """readelf should show no NEEDED (dynamic library) entries."""
        # This is a secondary check — if readelf is available
        readelf = shutil.which("readelf") or shutil.which("arm-linux-gnueabihf-readelf")
        if readelf is None:
            # Can't run this check without readelf; skip gracefully
            return
        result = subprocess.run(
            [readelf, "-d", BINARY_PATH],
            capture_output=True,
            text=True,
            timeout=30,
        )
        combined = result.stdout + result.stderr
        # A static binary either has no dynamic section or readelf errors out
        assert "NEEDED" not in combined, (
            f"Binary has dynamic library dependencies: {combined[:500]}"
        )


# ---------------------------------------------------------------------------
# Test 3: Executable permission
# ---------------------------------------------------------------------------

class TestPermissions:
    def test_executable_bit_set(self):
        """The file must have the executable bit set for at least one of u/g/o."""
        st = os.stat(BINARY_PATH)
        mode = st.st_mode
        is_exec = bool(mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH))
        assert is_exec, (
            f"Binary does not have executable permission. Mode: {oct(mode)}"
        )


# ---------------------------------------------------------------------------
# Test 4: Functional under QEMU — --help output
# ---------------------------------------------------------------------------

class TestQemuHelp:
    def test_help_contains_busybox(self):
        """Running the binary with --help under QEMU must produce output containing 'BusyBox'."""
        qemu = _find_qemu_arm()
        assert qemu is not None, (
            "No qemu-arm-static or qemu-arm binary found on PATH"
        )
        output = _run_qemu(qemu, BINARY_PATH, "--help", timeout=60)
        assert "BusyBox" in output, (
            f"--help output does not contain 'BusyBox'. Got:\n{output[:1000]}"
        )

    def test_help_produces_substantial_output(self):
        """--help should produce meaningful output (not just a single line)."""
        qemu = _find_qemu_arm()
        assert qemu is not None, "No qemu-arm binary found"
        output = _run_qemu(qemu, BINARY_PATH, "--help", timeout=60)
        lines = [l for l in output.strip().splitlines() if l.strip()]
        assert len(lines) >= 3, (
            f"--help output is suspiciously short ({len(lines)} lines). "
            f"Got:\n{output[:500]}"
        )


# ---------------------------------------------------------------------------
# Test 5: Core applets present
# ---------------------------------------------------------------------------

REQUIRED_APPLETS = ["sh", "ls", "cat", "echo", "mkdir", "rm", "cp", "mv", "grep", "sed"]


class TestApplets:
    def test_list_returns_applets(self):
        """--list must return a non-empty list of applet names."""
        qemu = _find_qemu_arm()
        assert qemu is not None, "No qemu-arm binary found"
        output = _run_qemu(qemu, BINARY_PATH, "--list", timeout=60)
        applets = [line.strip() for line in output.strip().splitlines() if line.strip()]
        assert len(applets) >= 10, (
            f"--list returned only {len(applets)} applets; expected at least 10. "
            f"Output:\n{output[:500]}"
        )

    def test_required_applet_sh(self):
        self._check_applet("sh")

    def test_required_applet_ls(self):
        self._check_applet("ls")

    def test_required_applet_cat(self):
        self._check_applet("cat")

    def test_required_applet_echo(self):
        self._check_applet("echo")

    def test_required_applet_mkdir(self):
        self._check_applet("mkdir")

    def test_required_applet_rm(self):
        self._check_applet("rm")

    def test_required_applet_cp(self):
        self._check_applet("cp")

    def test_required_applet_mv(self):
        self._check_applet("mv")

    def test_required_applet_grep(self):
        self._check_applet("grep")

    def test_required_applet_sed(self):
        self._check_applet("sed")

    # -- helper --

    def _check_applet(self, applet_name):
        qemu = _find_qemu_arm()
        assert qemu is not None, "No qemu-arm binary found"
        output = _run_qemu(qemu, BINARY_PATH, "--list", timeout=60)
        # Each applet should appear as its own line (exact match per line)
        applet_set = {line.strip() for line in output.strip().splitlines()}
        assert applet_name in applet_set, (
            f"Required applet '{applet_name}' not found in --list output. "
            f"Available applets ({len(applet_set)}): "
            f"{sorted(list(applet_set))[:30]}..."
        )
