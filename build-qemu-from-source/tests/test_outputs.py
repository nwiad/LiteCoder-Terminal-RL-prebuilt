"""
Tests for build-qemu-from-source task.

Validates:
1. QEMU source repo cloned correctly at /app/qemu-upstream
2. Out-of-tree build directory at /app/qemu-build
3. Three target binaries installed and executable on PATH
4. Each binary can actually run (smoke test)
5. Build report at /app/qemu-build-report.txt with correct format and valid content
"""

import os
import re
import subprocess
import stat

# ─── Paths ───────────────────────────────────────────────────────────────────

QEMU_SRC = "/app/qemu-upstream"
QEMU_BUILD = "/app/qemu-build"
REPORT_PATH = "/app/qemu-build-report.txt"

EXPECTED_BINARIES = [
    "qemu-system-arm",
    "qemu-system-riscv32",
    "qemu-system-riscv64",
]

EXPECTED_TARGETS = "arm-softmmu,riscv32-softmmu,riscv64-softmmu"


# ─── Helpers ─────────────────────────────────────────────────────────────────

def read_report():
    """Read and parse the build report into a dict."""
    assert os.path.isfile(REPORT_PATH), f"Build report not found at {REPORT_PATH}"
    with open(REPORT_PATH, "r") as f:
        content = f.read().strip()
    assert len(content) > 0, "Build report is empty"
    report = {}
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        assert ":" in line, f"Report line missing colon separator: '{line}'"
        key, value = line.split(":", 1)
        report[key.strip()] = value.strip()
    return report


def run_cmd(cmd, timeout=30):
    """Run a shell command and return stdout."""
    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True, timeout=timeout
    )
    return result


# ─── 1. Source Repository Tests ──────────────────────────────────────────────

class TestSourceRepo:
    def test_source_dir_exists(self):
        assert os.path.isdir(QEMU_SRC), f"Source directory {QEMU_SRC} does not exist"

    def test_source_is_git_repo(self):
        git_dir = os.path.join(QEMU_SRC, ".git")
        assert os.path.exists(git_dir), f"{QEMU_SRC} is not a git repository (no .git)"

    def test_source_has_configure_script(self):
        configure = os.path.join(QEMU_SRC, "configure")
        assert os.path.isfile(configure), "QEMU source missing configure script"

    def test_git_commit_retrievable(self):
        """Verify we can get a valid commit hash from the cloned repo."""
        result = run_cmd(f"git -C {QEMU_SRC} rev-parse HEAD")
        assert result.returncode == 0, "Failed to get git commit from source repo"
        commit = result.stdout.strip()
        assert re.fullmatch(r"[0-9a-f]{40}", commit), (
            f"Git HEAD is not a valid 40-char hex hash: '{commit}'"
        )


# ─── 2. Build Directory Tests ───────────────────────────────────────────────

class TestBuildDirectory:
    def test_build_dir_exists(self):
        assert os.path.isdir(QEMU_BUILD), f"Build directory {QEMU_BUILD} does not exist"

    def test_build_dir_is_not_empty(self):
        contents = os.listdir(QEMU_BUILD)
        assert len(contents) > 0, f"Build directory {QEMU_BUILD} is empty"

    def test_build_dir_has_build_artifacts(self):
        """An actual build should produce a Makefile or build.ninja in the build dir."""
        has_makefile = os.path.isfile(os.path.join(QEMU_BUILD, "Makefile"))
        has_ninja = os.path.isfile(os.path.join(QEMU_BUILD, "build.ninja"))
        assert has_makefile or has_ninja, (
            "Build directory lacks Makefile or build.ninja — build may not have run"
        )


# ─── 3. Binary Installation Tests ───────────────────────────────────────────

class TestBinaryInstallation:
    def test_binaries_on_path(self):
        """All three target binaries must be findable via 'which'."""
        for binary in EXPECTED_BINARIES:
            result = run_cmd(f"which {binary}")
            assert result.returncode == 0, (
                f"Binary '{binary}' not found on PATH"
            )

    def test_binaries_are_executable(self):
        """All three binaries must have the executable permission bit set."""
        for binary in EXPECTED_BINARIES:
            result = run_cmd(f"which {binary}")
            if result.returncode != 0:
                assert False, f"Binary '{binary}' not found on PATH"
            path = result.stdout.strip()
            assert os.access(path, os.X_OK), (
                f"Binary '{binary}' at {path} is not executable"
            )

    def test_binaries_are_real_files(self):
        """Binaries should be real ELF executables, not empty stubs."""
        for binary in EXPECTED_BINARIES:
            result = run_cmd(f"which {binary}")
            if result.returncode != 0:
                assert False, f"Binary '{binary}' not found"
            path = result.stdout.strip()
            size = os.path.getsize(path)
            # A real QEMU binary is at least 1 MB
            assert size > 1_000_000, (
                f"Binary '{binary}' is suspiciously small ({size} bytes) — "
                "may be a stub or empty file"
            )


# ─── 4. Binary Smoke Tests ──────────────────────────────────────────────────

class TestBinarySmokeTests:
    def test_qemu_system_arm_version(self):
        result = run_cmd("qemu-system-arm --version", timeout=15)
        assert result.returncode == 0, "qemu-system-arm --version failed"
        assert "QEMU" in result.stdout, (
            "qemu-system-arm --version output does not contain 'QEMU'"
        )

    def test_qemu_system_riscv32_version(self):
        result = run_cmd("qemu-system-riscv32 --version", timeout=15)
        assert result.returncode == 0, "qemu-system-riscv32 --version failed"
        assert "QEMU" in result.stdout, (
            "qemu-system-riscv32 --version output does not contain 'QEMU'"
        )

    def test_qemu_system_riscv64_version(self):
        result = run_cmd("qemu-system-riscv64 --version", timeout=15)
        assert result.returncode == 0, "qemu-system-riscv64 --version failed"
        assert "QEMU" in result.stdout, (
            "qemu-system-riscv64 --version output does not contain 'QEMU'"
        )

    def test_binaries_version_strings_consistent(self):
        """All three binaries should report the same QEMU version."""
        versions = []
        for binary in EXPECTED_BINARIES:
            result = run_cmd(f"{binary} --version", timeout=15)
            if result.returncode == 0:
                first_line = result.stdout.strip().splitlines()[0]
                versions.append(first_line)
        assert len(versions) == 3, "Could not get version from all three binaries"
        assert versions[0] == versions[1] == versions[2], (
            f"Version mismatch across binaries: {versions}"
        )


# ─── 5. Build Report Tests ──────────────────────────────────────────────────

class TestBuildReport:
    def test_report_file_exists(self):
        assert os.path.isfile(REPORT_PATH), f"Report file not found at {REPORT_PATH}"

    def test_report_not_empty(self):
        size = os.path.getsize(REPORT_PATH)
        assert size > 0, "Report file is empty"

    def test_report_has_all_required_keys(self):
        report = read_report()
        required_keys = ["git_commit", "configure_flags", "cpu_cores", "qemu_version"]
        for key in required_keys:
            assert key in report, f"Report missing required key: '{key}'"

    def test_report_has_exactly_four_lines(self):
        """The report should have exactly 4 non-empty lines per the spec."""
        with open(REPORT_PATH, "r") as f:
            lines = [l.strip() for l in f.readlines() if l.strip()]
        assert len(lines) == 4, (
            f"Report should have exactly 4 lines, found {len(lines)}"
        )

    def test_git_commit_is_valid_hash(self):
        report = read_report()
        commit = report.get("git_commit", "")
        assert re.fullmatch(r"[0-9a-f]{40}", commit), (
            f"git_commit is not a valid 40-char lowercase hex hash: '{commit}'"
        )

    def test_git_commit_matches_repo(self):
        """The reported commit must match the actual HEAD of the cloned repo."""
        report = read_report()
        reported_commit = report.get("git_commit", "")
        result = run_cmd(f"git -C {QEMU_SRC} rev-parse HEAD")
        if result.returncode == 0:
            actual_commit = result.stdout.strip()
            assert reported_commit == actual_commit, (
                f"Report git_commit ({reported_commit}) does not match "
                f"repo HEAD ({actual_commit})"
            )

    def test_configure_flags_correct(self):
        report = read_report()
        flags = report.get("configure_flags", "")
        assert EXPECTED_TARGETS in flags, (
            f"configure_flags should contain '{EXPECTED_TARGETS}', got: '{flags}'"
        )
        # Must include --target-list
        assert "--target-list=" in flags, (
            f"configure_flags missing '--target-list=': '{flags}'"
        )

    def test_cpu_cores_is_positive_integer(self):
        report = read_report()
        cores = report.get("cpu_cores", "")
        assert cores.isdigit(), f"cpu_cores is not a positive integer: '{cores}'"
        assert int(cores) >= 1, f"cpu_cores must be >= 1, got: {cores}"

    def test_qemu_version_contains_qemu(self):
        report = read_report()
        version = report.get("qemu_version", "")
        assert "QEMU" in version.upper(), (
            f"qemu_version does not mention QEMU: '{version}'"
        )

    def test_qemu_version_has_version_number(self):
        """Version string should contain a version number like X.Y.Z or X.Y."""
        report = read_report()
        version = report.get("qemu_version", "")
        assert re.search(r"\d+\.\d+", version), (
            f"qemu_version does not contain a version number (X.Y): '{version}'"
        )

    def test_qemu_version_matches_binary(self):
        """The reported version must match what qemu-system-arm --version outputs."""
        report = read_report()
        reported_version = report.get("qemu_version", "").strip()
        result = run_cmd("qemu-system-arm --version", timeout=15)
        if result.returncode == 0:
            actual_first_line = result.stdout.strip().splitlines()[0].strip()
            assert reported_version == actual_first_line, (
                f"Report qemu_version ('{reported_version}') does not match "
                f"qemu-system-arm --version first line ('{actual_first_line}')"
            )
