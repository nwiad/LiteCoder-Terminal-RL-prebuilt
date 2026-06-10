"""
Tests for Build Static FFmpeg with FDK-AAC Encoder task.

Validates:
1. /app/ffmpeg binary exists, is ELF, statically linked, stripped, functional
2. /app/ffmpeg has libfdk_aac encoder support
3. /app/build_report.json exists with correct structure and truthful values
4. Cross-validation: report values match actual binary properties
"""

import json
import os
import stat
import subprocess

FFMPEG_PATH = "/app/ffmpeg"
REPORT_PATH = "/app/build_report.json"


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def run_cmd(cmd, timeout=30):
    """Run a shell command and return (returncode, stdout, stderr)."""
    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True, timeout=timeout
    )
    return result.returncode, result.stdout, result.stderr


def get_file_output():
    """Return the output of `file /app/ffmpeg`."""
    rc, stdout, _ = run_cmd(f"file {FFMPEG_PATH}")
    assert rc == 0, f"`file {FFMPEG_PATH}` failed with rc={rc}"
    return stdout.strip()


# ===========================================================================
# 1. Binary existence and basic properties
# ===========================================================================

class TestBinaryExists:
    """Verify the ffmpeg binary exists and has basic file properties."""

    def test_ffmpeg_file_exists(self):
        assert os.path.exists(FFMPEG_PATH), f"{FFMPEG_PATH} does not exist"

    def test_ffmpeg_is_regular_file(self):
        """Must be a regular file, not a symlink or directory."""
        assert os.path.isfile(FFMPEG_PATH), f"{FFMPEG_PATH} is not a regular file"
        assert not os.path.islink(FFMPEG_PATH), f"{FFMPEG_PATH} is a symlink"

    def test_ffmpeg_is_executable(self):
        """The file must have executable permission."""
        st = os.stat(FFMPEG_PATH)
        assert st.st_mode & stat.S_IXUSR, f"{FFMPEG_PATH} is not executable"

    def test_ffmpeg_nonzero_size(self):
        """Guard against empty placeholder files."""
        size = os.path.getsize(FFMPEG_PATH)
        # A real static ffmpeg binary is at least a few MB
        assert size > 1_000_000, (
            f"{FFMPEG_PATH} is suspiciously small ({size} bytes). "
            "Expected a multi-MB statically linked binary."
        )


# ===========================================================================
# 2. ELF binary checks
# ===========================================================================

class TestBinaryFormat:
    """Verify the binary is a proper ELF executable."""

    def test_is_elf_binary(self):
        """The file command must report ELF."""
        file_out = get_file_output()
        assert "ELF" in file_out, (
            f"{FFMPEG_PATH} is not an ELF binary. `file` output: {file_out}"
        )

    def test_statically_linked(self):
        """The binary must be statically linked (no dynamic library deps)."""
        file_out = get_file_output()
        assert "statically linked" in file_out, (
            f"{FFMPEG_PATH} is not statically linked. `file` output: {file_out}"
        )

    def test_stripped(self):
        """The binary must be stripped of debug symbols."""
        file_out = get_file_output()
        assert "stripped" in file_out, (
            f"{FFMPEG_PATH} is not stripped. `file` output: {file_out}"
        )
        # Make sure it's not "not stripped"
        assert "not stripped" not in file_out, (
            f"{FFMPEG_PATH} contains debug symbols (not stripped). "
            f"`file` output: {file_out}"
        )


# ===========================================================================
# 3. FFmpeg functionality
# ===========================================================================

class TestFfmpegFunctionality:
    """Verify the ffmpeg binary actually works."""

    def test_version_exits_zero(self):
        """`ffmpeg -version` must exit with code 0."""
        rc, stdout, stderr = run_cmd(f"{FFMPEG_PATH} -version")
        assert rc == 0, (
            f"`{FFMPEG_PATH} -version` exited with code {rc}. "
            f"stdout: {stdout[:500]}, stderr: {stderr[:500]}"
        )

    def test_version_prints_string(self):
        """`ffmpeg -version` must print a version string containing 'ffmpeg'."""
        rc, stdout, _ = run_cmd(f"{FFMPEG_PATH} -version")
        assert rc == 0
        first_line = stdout.strip().split("\n")[0].lower()
        assert "ffmpeg" in first_line, (
            f"First line of version output does not contain 'ffmpeg': {first_line}"
        )

    def test_has_libfdk_aac_encoder(self):
        """The encoder list must include libfdk_aac."""
        rc, stdout, stderr = run_cmd(f"{FFMPEG_PATH} -encoders 2>/dev/null")
        # -encoders may exit 0 or 1 depending on version; check stdout
        combined = stdout + stderr
        assert "libfdk_aac" in combined, (
            f"libfdk_aac encoder not found in encoder list. "
            f"Output (first 1000 chars): {combined[:1000]}"
        )


# ===========================================================================
# 4. Build report JSON
# ===========================================================================

class TestBuildReport:
    """Verify /app/build_report.json exists and has correct structure."""

    def _load_report(self):
        assert os.path.exists(REPORT_PATH), f"{REPORT_PATH} does not exist"
        with open(REPORT_PATH, "r") as f:
            content = f.read().strip()
        assert len(content) > 2, f"{REPORT_PATH} is empty or trivial"
        report = json.loads(content)
        return report

    def test_report_file_exists(self):
        assert os.path.exists(REPORT_PATH), f"{REPORT_PATH} does not exist"

    def test_report_is_valid_json(self):
        self._load_report()

    def test_report_has_required_keys(self):
        report = self._load_report()
        required_keys = [
            "ffmpeg_version",
            "is_static",
            "is_stripped",
            "has_libfdk_aac",
            "binary_size_bytes",
            "binary_path",
        ]
        for key in required_keys:
            assert key in report, f"Missing required key '{key}' in build report"

    def test_report_boolean_fields_are_true(self):
        """All boolean fields must be true for a successful build."""
        report = self._load_report()
        assert report["is_static"] is True, (
            f"is_static should be true, got {report['is_static']}"
        )
        assert report["is_stripped"] is True, (
            f"is_stripped should be true, got {report['is_stripped']}"
        )
        assert report["has_libfdk_aac"] is True, (
            f"has_libfdk_aac should be true, got {report['has_libfdk_aac']}"
        )

    def test_report_binary_path(self):
        report = self._load_report()
        assert report["binary_path"] == "/app/ffmpeg", (
            f"binary_path should be '/app/ffmpeg', got '{report['binary_path']}'"
        )

    def test_report_ffmpeg_version_nonempty(self):
        report = self._load_report()
        ver = report["ffmpeg_version"]
        assert isinstance(ver, str), f"ffmpeg_version should be a string, got {type(ver)}"
        assert len(ver.strip()) > 0, "ffmpeg_version is empty"
        assert "ffmpeg" in ver.lower(), (
            f"ffmpeg_version doesn't look like a version string: '{ver}'"
        )

    def test_report_binary_size_is_positive_int(self):
        report = self._load_report()
        size = report["binary_size_bytes"]
        assert isinstance(size, int), (
            f"binary_size_bytes should be an integer, got {type(size)}"
        )
        assert size > 1_000_000, (
            f"binary_size_bytes is suspiciously small ({size}). "
            "A static ffmpeg binary should be several MB."
        )


# ===========================================================================
# 5. Cross-validation: report vs actual binary
# ===========================================================================

class TestCrossValidation:
    """Ensure the report accurately reflects the actual binary."""

    def _load_report(self):
        with open(REPORT_PATH, "r") as f:
            return json.loads(f.read())

    def test_report_size_matches_actual(self):
        """binary_size_bytes in report must match actual file size."""
        report = self._load_report()
        actual_size = os.path.getsize(FFMPEG_PATH)
        reported_size = report["binary_size_bytes"]
        assert reported_size == actual_size, (
            f"Report says {reported_size} bytes but actual file is {actual_size} bytes"
        )

    def test_report_version_matches_actual(self):
        """ffmpeg_version in report must match actual -version output."""
        report = self._load_report()
        rc, stdout, _ = run_cmd(f"{FFMPEG_PATH} -version")
        assert rc == 0
        actual_first_line = stdout.strip().split("\n")[0]
        reported_version = report["ffmpeg_version"].strip()
        assert reported_version == actual_first_line, (
            f"Report version '{reported_version}' does not match "
            f"actual first line '{actual_first_line}'"
        )

    def test_report_static_matches_actual(self):
        """is_static in report must match actual `file` output."""
        report = self._load_report()
        file_out = get_file_output()
        actual_static = "statically linked" in file_out
        assert report["is_static"] == actual_static, (
            f"Report is_static={report['is_static']} but "
            f"actual static={actual_static}. file output: {file_out}"
        )

    def test_report_stripped_matches_actual(self):
        """is_stripped in report must match actual `file` output."""
        report = self._load_report()
        file_out = get_file_output()
        actual_stripped = "stripped" in file_out and "not stripped" not in file_out
        assert report["is_stripped"] == actual_stripped, (
            f"Report is_stripped={report['is_stripped']} but "
            f"actual stripped={actual_stripped}. file output: {file_out}"
        )

    def test_report_fdk_matches_actual(self):
        """has_libfdk_aac in report must match actual encoder list."""
        report = self._load_report()
        rc, stdout, stderr = run_cmd(f"{FFMPEG_PATH} -encoders 2>/dev/null")
        actual_fdk = "libfdk_aac" in (stdout + stderr)
        assert report["has_libfdk_aac"] == actual_fdk, (
            f"Report has_libfdk_aac={report['has_libfdk_aac']} but "
            f"actual fdk presence={actual_fdk}"
        )
