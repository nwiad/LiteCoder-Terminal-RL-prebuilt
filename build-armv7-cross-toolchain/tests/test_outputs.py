"""
Tests for the ARMv7 cross-compilation toolchain task.

Verifies all 7 deliverables specified in instruction.md:
1. /app/build_toolchain.sh - automation script
2. /opt/armv7-toolchain - toolchain directory with binaries
3. /app/hello_arm.c - test C source
4. /app/hello_arm - cross-compiled ARM ELF binary
5. /app/elf_report.txt - ELF inspection report
6. /app/armv7-toolchain.tar.gz - distribution tarball
7. /app/ci_command.txt - CI one-liner
"""

import os
import stat
import subprocess
import glob
import tarfile
import gzip


# ---------------------------------------------------------------------------
# Deliverable 1: /app/build_toolchain.sh
# ---------------------------------------------------------------------------

class TestBuildToolchainScript:
    SCRIPT_PATH = "/app/build_toolchain.sh"

    def test_script_exists(self):
        assert os.path.isfile(self.SCRIPT_PATH), (
            f"{self.SCRIPT_PATH} does not exist"
        )

    def test_script_is_executable(self):
        """The script must have the executable bit set."""
        assert os.path.isfile(self.SCRIPT_PATH), f"{self.SCRIPT_PATH} missing"
        mode = os.stat(self.SCRIPT_PATH).st_mode
        assert mode & stat.S_IXUSR, (
            f"{self.SCRIPT_PATH} is not executable (mode={oct(mode)})"
        )

    def test_script_is_not_empty(self):
        assert os.path.getsize(self.SCRIPT_PATH) > 0, (
            f"{self.SCRIPT_PATH} is empty"
        )

    def test_script_has_shebang(self):
        """A proper bash script should start with a shebang line."""
        with open(self.SCRIPT_PATH, "r") as f:
            first_line = f.readline().strip()
        assert first_line.startswith("#!"), (
            f"{self.SCRIPT_PATH} missing shebang line"
        )
        assert "bash" in first_line or "sh" in first_line, (
            f"{self.SCRIPT_PATH} shebang does not reference bash/sh: {first_line}"
        )

    def test_script_references_crosstool_ng(self):
        """The script must use crosstool-NG to build the toolchain."""
        with open(self.SCRIPT_PATH, "r") as f:
            content = f.read().lower()
        assert "crosstool" in content or "ct-ng" in content or "ct_" in content, (
            "build_toolchain.sh does not reference crosstool-NG"
        )

    def test_script_references_toolchain_prefix(self):
        """The script must target /opt/armv7-toolchain."""
        with open(self.SCRIPT_PATH, "r") as f:
            content = f.read()
        assert "/opt/armv7-toolchain" in content, (
            "build_toolchain.sh does not reference /opt/armv7-toolchain"
        )


# ---------------------------------------------------------------------------
# Deliverable 2: /opt/armv7-toolchain  (toolchain directory)
# ---------------------------------------------------------------------------

class TestToolchainDirectory:
    TOOLCHAIN_BIN = "/opt/armv7-toolchain/bin"

    def test_toolchain_bin_dir_exists(self):
        assert os.path.isdir(self.TOOLCHAIN_BIN), (
            f"{self.TOOLCHAIN_BIN} directory does not exist"
        )

    def test_arm_gcc_binary_exists(self):
        """bin/ must contain at least one executable matching arm-*-gcc."""
        matches = glob.glob(os.path.join(self.TOOLCHAIN_BIN, "arm-*-gcc"))
        # Filter out versioned variants like arm-*-gcc-12.3.0
        matches = [m for m in matches if not m.split("gcc")[-1].startswith("-")]
        assert len(matches) >= 1, (
            f"No arm-*-gcc found in {self.TOOLCHAIN_BIN}. "
            f"Contents: {os.listdir(self.TOOLCHAIN_BIN) if os.path.isdir(self.TOOLCHAIN_BIN) else 'N/A'}"
        )

    def test_arm_gcc_is_executable(self):
        """The cross-compiler binary must be executable."""
        matches = glob.glob(os.path.join(self.TOOLCHAIN_BIN, "arm-*-gcc"))
        matches = [m for m in matches if not m.split("gcc")[-1].startswith("-")]
        assert len(matches) >= 1, "No arm-*-gcc found"
        gcc_path = matches[0]
        mode = os.stat(gcc_path).st_mode
        assert mode & stat.S_IXUSR, (
            f"{gcc_path} is not executable"
        )

    def test_arm_gpp_binary_exists(self):
        """bin/ should also contain arm-*-g++."""
        matches = glob.glob(os.path.join(self.TOOLCHAIN_BIN, "arm-*-g++"))
        assert len(matches) >= 1, (
            f"No arm-*-g++ found in {self.TOOLCHAIN_BIN}"
        )

    def test_arm_ld_binary_exists(self):
        """bin/ should also contain arm-*-ld."""
        matches = glob.glob(os.path.join(self.TOOLCHAIN_BIN, "arm-*-ld"))
        assert len(matches) >= 1, (
            f"No arm-*-ld found in {self.TOOLCHAIN_BIN}"
        )


# ---------------------------------------------------------------------------
# Deliverable 3: /app/hello_arm.c
# ---------------------------------------------------------------------------

class TestHelloArmSource:
    SOURCE_PATH = "/app/hello_arm.c"

    def test_source_exists(self):
        assert os.path.isfile(self.SOURCE_PATH), (
            f"{self.SOURCE_PATH} does not exist"
        )

    def test_source_contains_main(self):
        with open(self.SOURCE_PATH, "r") as f:
            content = f.read()
        assert "main" in content, (
            f"{self.SOURCE_PATH} does not contain a main function"
        )

    def test_source_prints_hello_arm(self):
        """The source must contain the exact string 'Hello, ARM'."""
        with open(self.SOURCE_PATH, "r") as f:
            content = f.read()
        assert "Hello, ARM" in content, (
            f"{self.SOURCE_PATH} does not contain 'Hello, ARM'"
        )


# ---------------------------------------------------------------------------
# Deliverable 4: /app/hello_arm  (cross-compiled ARM ELF binary)
# ---------------------------------------------------------------------------

class TestHelloArmBinary:
    BINARY_PATH = "/app/hello_arm"

    def test_binary_exists(self):
        assert os.path.isfile(self.BINARY_PATH), (
            f"{self.BINARY_PATH} does not exist"
        )

    def test_binary_is_not_empty(self):
        assert os.path.getsize(self.BINARY_PATH) > 0, (
            f"{self.BINARY_PATH} is empty"
        )

    def test_binary_is_elf(self):
        """The file must be an ELF binary (magic bytes)."""
        with open(self.BINARY_PATH, "rb") as f:
            magic = f.read(4)
        assert magic == b"\x7fELF", (
            f"{self.BINARY_PATH} is not an ELF binary (magic={magic!r})"
        )

    def test_file_command_shows_arm(self):
        """'file' output must contain 'ARM'."""
        result = subprocess.run(
            ["file", self.BINARY_PATH],
            capture_output=True, text=True, timeout=10
        )
        output = result.stdout
        assert "ARM" in output, (
            f"'file {self.BINARY_PATH}' does not contain 'ARM'. Output: {output}"
        )

    def test_file_command_shows_elf_32bit(self):
        """The binary should be a 32-bit ELF (ARM is 32-bit)."""
        result = subprocess.run(
            ["file", self.BINARY_PATH],
            capture_output=True, text=True, timeout=10
        )
        output = result.stdout
        assert "ELF" in output, f"Not an ELF: {output}"
        assert "32-bit" in output, (
            f"Expected 32-bit ELF for ARM. Output: {output}"
        )

    def test_binary_is_statically_linked(self):
        """'file' output must contain 'statically linked'."""
        result = subprocess.run(
            ["file", self.BINARY_PATH],
            capture_output=True, text=True, timeout=10
        )
        output = result.stdout
        assert "statically linked" in output, (
            f"Binary is not statically linked. file output: {output}"
        )

    def test_readelf_shows_arm_machine(self):
        """readelf -h must show Machine: ARM."""
        result = subprocess.run(
            ["readelf", "-h", self.BINARY_PATH],
            capture_output=True, text=True, timeout=10
        )
        output = result.stdout
        # Look for the Machine field containing ARM
        found_arm = False
        for line in output.splitlines():
            if "Machine:" in line and "ARM" in line:
                found_arm = True
                break
        assert found_arm, (
            f"readelf -h does not show Machine: ARM. Output:\n{output}"
        )


# ---------------------------------------------------------------------------
# Deliverable 5: /app/elf_report.txt
# ---------------------------------------------------------------------------

class TestElfReport:
    REPORT_PATH = "/app/elf_report.txt"

    def test_report_exists(self):
        assert os.path.isfile(self.REPORT_PATH), (
            f"{self.REPORT_PATH} does not exist"
        )

    def test_report_is_not_empty(self):
        assert os.path.getsize(self.REPORT_PATH) > 0, (
            f"{self.REPORT_PATH} is empty"
        )

    def test_report_contains_elf_header_marker(self):
        """Report should contain readelf -h output markers."""
        with open(self.REPORT_PATH, "r") as f:
            content = f.read()
        assert "ELF" in content, (
            f"{self.REPORT_PATH} does not contain 'ELF'"
        )

    def test_report_machine_field_is_arm(self):
        """The Machine field in the report must contain ARM."""
        with open(self.REPORT_PATH, "r") as f:
            content = f.read()
        found_arm_machine = False
        for line in content.splitlines():
            if "Machine:" in line and "ARM" in line:
                found_arm_machine = True
                break
        assert found_arm_machine, (
            f"elf_report.txt does not show Machine: ARM. Content:\n{content[:500]}"
        )

    def test_report_contains_class_field(self):
        """readelf -h output should contain a Class field (ELF32)."""
        with open(self.REPORT_PATH, "r") as f:
            content = f.read()
        assert "Class:" in content, (
            f"elf_report.txt missing 'Class:' field — may not be readelf -h output"
        )

    def test_report_contains_entry_point(self):
        """readelf -h output should contain an entry point address."""
        with open(self.REPORT_PATH, "r") as f:
            content = f.read()
        assert "Entry point address:" in content, (
            f"elf_report.txt missing 'Entry point address:' — may not be readelf -h output"
        )


# ---------------------------------------------------------------------------
# Deliverable 6: /app/armv7-toolchain.tar.gz
# ---------------------------------------------------------------------------

class TestDistributionTarball:
    TARBALL_PATH = "/app/armv7-toolchain.tar.gz"

    def test_tarball_exists(self):
        assert os.path.isfile(self.TARBALL_PATH), (
            f"{self.TARBALL_PATH} does not exist"
        )

    def test_tarball_is_not_empty(self):
        assert os.path.getsize(self.TARBALL_PATH) > 0, (
            f"{self.TARBALL_PATH} is empty"
        )

    def test_tarball_is_valid_gzip(self):
        """Must be a valid gzip file (check magic bytes)."""
        with open(self.TARBALL_PATH, "rb") as f:
            magic = f.read(2)
        assert magic == b"\x1f\x8b", (
            f"{self.TARBALL_PATH} is not a valid gzip file (magic={magic!r})"
        )

    def test_tarball_is_extractable(self):
        """tar tzf must succeed without errors."""
        result = subprocess.run(
            ["tar", "tzf", self.TARBALL_PATH],
            capture_output=True, text=True, timeout=120
        )
        assert result.returncode == 0, (
            f"tar tzf failed: {result.stderr}"
        )

    def test_tarball_contains_bin_directory(self):
        """Extracted archive must contain a bin/ directory."""
        result = subprocess.run(
            ["tar", "tzf", self.TARBALL_PATH],
            capture_output=True, text=True, timeout=120
        )
        entries = result.stdout
        assert "bin/" in entries, (
            f"Tarball does not contain bin/ directory. First entries:\n"
            f"{chr(10).join(entries.splitlines()[:20])}"
        )

    def test_tarball_contains_arm_gcc(self):
        """Extracted archive must contain an arm-*-gcc binary."""
        result = subprocess.run(
            ["tar", "tzf", self.TARBALL_PATH],
            capture_output=True, text=True, timeout=120
        )
        entries = result.stdout
        found_gcc = any(
            "arm-" in line and "gcc" in line and "bin/" in line
            for line in entries.splitlines()
        )
        assert found_gcc, (
            f"Tarball does not contain arm-*-gcc in bin/. "
            f"Sample entries:\n{chr(10).join(entries.splitlines()[:30])}"
        )


# ---------------------------------------------------------------------------
# Deliverable 7: /app/ci_command.txt
# ---------------------------------------------------------------------------

class TestCiCommand:
    CI_PATH = "/app/ci_command.txt"

    def test_ci_command_exists(self):
        assert os.path.isfile(self.CI_PATH), (
            f"{self.CI_PATH} does not exist"
        )

    def test_ci_command_is_not_empty(self):
        assert os.path.getsize(self.CI_PATH) > 0, (
            f"{self.CI_PATH} is empty"
        )

    def test_ci_command_references_build_script(self):
        """The CI one-liner must reference /app/build_toolchain.sh."""
        with open(self.CI_PATH, "r") as f:
            content = f.read().strip()
        assert "build_toolchain.sh" in content, (
            f"ci_command.txt does not reference build_toolchain.sh. "
            f"Content: {content[:200]}"
        )

    def test_ci_command_is_single_line(self):
        """The CI command should be a single-line command."""
        with open(self.CI_PATH, "r") as f:
            content = f.read().strip()
        # Allow for trailing newline but the actual command should be one line
        lines = [l for l in content.splitlines() if l.strip()]
        assert len(lines) == 1, (
            f"ci_command.txt should be a single-line command, "
            f"but has {len(lines)} non-empty lines"
        )


# ---------------------------------------------------------------------------
# Cross-deliverable consistency checks
# ---------------------------------------------------------------------------

class TestCrossDeliverableConsistency:
    """Verify that deliverables are consistent with each other."""

    def test_elf_report_matches_actual_binary(self):
        """The elf_report.txt should match what readelf -h actually produces
        for /app/hello_arm (both should show ARM)."""
        report_path = "/app/elf_report.txt"
        binary_path = "/app/hello_arm"
        if not os.path.isfile(report_path) or not os.path.isfile(binary_path):
            return  # Other tests will catch missing files

        with open(report_path, "r") as f:
            report_content = f.read()

        result = subprocess.run(
            ["readelf", "-h", binary_path],
            capture_output=True, text=True, timeout=10
        )
        actual_output = result.stdout

        # Both should agree on Machine: ARM
        report_has_arm = any(
            "Machine:" in l and "ARM" in l
            for l in report_content.splitlines()
        )
        actual_has_arm = any(
            "Machine:" in l and "ARM" in l
            for l in actual_output.splitlines()
        )
        assert report_has_arm and actual_has_arm, (
            "elf_report.txt and actual readelf -h disagree on ARM architecture"
        )

    def test_binary_was_compiled_from_source(self):
        """Sanity check: the source file and binary should both exist
        and the binary should be a real ARM ELF, not a dummy."""
        source_path = "/app/hello_arm.c"
        binary_path = "/app/hello_arm"
        if not os.path.isfile(source_path) or not os.path.isfile(binary_path):
            return

        # Binary must be significantly larger than source (compiled binary)
        src_size = os.path.getsize(source_path)
        bin_size = os.path.getsize(binary_path)
        assert bin_size > src_size * 5, (
            f"Binary ({bin_size} bytes) seems too small relative to source "
            f"({src_size} bytes) — may not be a real compiled binary"
        )
