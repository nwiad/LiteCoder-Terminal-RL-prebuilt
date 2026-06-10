"""
Tests for Fix Broken Python 3 Environment task.

Verifies that the agent has successfully restored a broken system Python 3
environment by checking:
  - python3 binary availability and version
  - Core package health (python3-minimal, python3, python3-apt)
  - apt/dpkg integrity
  - Standard library module imports
  - python3-apt integration
  - Recovery report file format and content
"""

import os
import re
import subprocess


RECOVERY_REPORT_PATH = "/app/recovery_report.txt"

REQUIRED_PACKAGES = {"python3-minimal", "python3", "python3-apt"}

REQUIRED_STDLIB_MODULES = ["sys", "os", "json", "subprocess"]


def run_cmd(cmd, timeout=30):
    """Run a shell command and return the CompletedProcess."""
    return subprocess.run(
        cmd, shell=True, capture_output=True, text=True, timeout=timeout
    )


# ──────────────────────────────────────────────────────────────────────
# 1. Python 3 binary restored
# ──────────────────────────────────────────────────────────────────────

class TestPython3Binary:
    def test_python3_exists_on_path(self):
        """python3 must be findable on PATH."""
        result = run_cmd("which python3")
        assert result.returncode == 0, (
            "python3 binary not found on PATH"
        )

    def test_python3_version_output(self):
        """python3 --version must return a valid 'Python 3.x.y' string."""
        result = run_cmd("python3 --version")
        assert result.returncode == 0, (
            f"python3 --version failed: {result.stderr}"
        )
        version_out = (result.stdout + result.stderr).strip()
        assert re.match(r"Python 3\.\d+\.\d+", version_out), (
            f"Unexpected python3 version output: '{version_out}'"
        )

    def test_python3_can_execute_code(self):
        """python3 must be able to execute a trivial expression."""
        result = run_cmd('python3 -c "print(1+1)"')
        assert result.returncode == 0, (
            f"python3 cannot execute code: {result.stderr}"
        )
        assert result.stdout.strip() == "2", (
            f"python3 produced wrong output: '{result.stdout.strip()}'"
        )


# ──────────────────────────────────────────────────────────────────────
# 2. Standard library modules accessible
# ──────────────────────────────────────────────────────────────────────

class TestStdlibModules:
    def test_import_sys(self):
        result = run_cmd('python3 -c "import sys; print(sys.version)"')
        assert result.returncode == 0, f"import sys failed: {result.stderr}"

    def test_import_os(self):
        result = run_cmd('python3 -c "import os; print(os.name)"')
        assert result.returncode == 0, f"import os failed: {result.stderr}"

    def test_import_json(self):
        result = run_cmd('python3 -c "import json; print(json.dumps({}))"')
        assert result.returncode == 0, f"import json failed: {result.stderr}"

    def test_import_subprocess(self):
        result = run_cmd('python3 -c "import subprocess; print(subprocess.__name__)"')
        assert result.returncode == 0, f"import subprocess failed: {result.stderr}"

    def test_stdlib_modules_functional(self):
        """Verify modules are not just importable but actually work."""
        code = (
            "import json, os, subprocess; "
            "d = json.loads('{\"a\": 1}'); "
            "assert d['a'] == 1; "
            "assert os.path.exists('/'); "
            "r = subprocess.run(['echo', 'ok'], capture_output=True, text=True); "
            "assert r.stdout.strip() == 'ok'; "
            "print('ALL_OK')"
        )
        result = run_cmd(f'python3 -c "{code}"')
        assert result.returncode == 0, (
            f"Stdlib functional test failed: {result.stderr}"
        )
        assert "ALL_OK" in result.stdout


# ──────────────────────────────────────────────────────────────────────
# 3. python3-apt integration
# ──────────────────────────────────────────────────────────────────────

class TestPython3Apt:
    def test_import_apt(self):
        """python3 -c 'import apt' must succeed."""
        result = run_cmd('python3 -c "import apt; print(apt.__name__)"')
        assert result.returncode == 0, (
            f"import apt failed: {result.stderr}"
        )
        assert "apt" in result.stdout.strip()


# ──────────────────────────────────────────────────────────────────────
# 4. Package health via dpkg
# ──────────────────────────────────────────────────────────────────────

class TestPackageHealth:
    def test_python3_minimal_installed(self):
        result = run_cmd("dpkg -s python3-minimal")
        assert result.returncode == 0, "python3-minimal not installed"
        assert "Status: install ok installed" in result.stdout, (
            f"python3-minimal not in healthy state: {result.stdout}"
        )

    def test_python3_installed(self):
        result = run_cmd("dpkg -s python3")
        assert result.returncode == 0, "python3 package not installed"
        assert "Status: install ok installed" in result.stdout, (
            f"python3 not in healthy state: {result.stdout}"
        )

    def test_python3_apt_installed(self):
        result = run_cmd("dpkg -s python3-apt")
        assert result.returncode == 0, "python3-apt not installed"
        assert "Status: install ok installed" in result.stdout, (
            f"python3-apt not in healthy state: {result.stdout}"
        )

    def test_no_half_installed_packages(self):
        """dpkg status must not contain any half-installed python3 packages."""
        result = run_cmd("dpkg -l 'python3*' 2>/dev/null || true")
        # Lines starting with 'iH' or 'rH' indicate half-installed
        for line in result.stdout.splitlines():
            if line.startswith(("iH", "rH", "pH", "uH")):
                assert False, f"Half-installed package found: {line}"


# ──────────────────────────────────────────────────────────────────────
# 5. apt / dpkg integrity
# ──────────────────────────────────────────────────────────────────────

class TestAptDpkgIntegrity:
    def test_apt_get_check(self):
        """apt-get check must complete without errors."""
        result = run_cmd("apt-get check 2>&1")
        assert result.returncode == 0, (
            f"apt-get check failed: {result.stdout} {result.stderr}"
        )

    def test_dpkg_audit(self):
        """dpkg --audit must report no issues."""
        result = run_cmd("dpkg --audit")
        assert result.returncode == 0, (
            f"dpkg --audit failed: {result.stderr}"
        )
        # dpkg --audit prints nothing when everything is fine
        audit_output = result.stdout.strip()
        assert audit_output == "", (
            f"dpkg --audit reported issues: {audit_output}"
        )

    def test_no_broken_dependencies(self):
        """apt-get -f install should have nothing to fix."""
        result = run_cmd(
            "apt-get -f install --dry-run 2>&1"
        )
        assert result.returncode == 0, (
            f"Broken dependencies remain: {result.stdout}"
        )


# ──────────────────────────────────────────────────────────────────────
# 6. Recovery report file
# ──────────────────────────────────────────────────────────────────────

class TestRecoveryReport:
    def test_report_file_exists(self):
        assert os.path.isfile(RECOVERY_REPORT_PATH), (
            f"Recovery report not found at {RECOVERY_REPORT_PATH}"
        )

    def test_report_not_empty(self):
        assert os.path.isfile(RECOVERY_REPORT_PATH), "Report file missing"
        size = os.path.getsize(RECOVERY_REPORT_PATH)
        assert size > 0, "Recovery report is empty"

    def test_report_line1_python_version(self):
        """Line 1 must contain a valid Python 3.x.x version string."""
        lines = _read_report_lines()
        assert len(lines) >= 1, "Report has no lines"
        line1 = lines[0].strip()
        assert re.match(r"Python 3\.\d+\.\d+", line1), (
            f"Line 1 is not a valid Python version: '{line1}'"
        )

    def test_report_line1_matches_actual_version(self):
        """Line 1 must match the actual installed python3 --version."""
        lines = _read_report_lines()
        assert len(lines) >= 1, "Report has no lines"
        reported_version = lines[0].strip()

        result = run_cmd("python3 --version")
        actual_version = (result.stdout + result.stderr).strip()

        assert reported_version == actual_version, (
            f"Report version '{reported_version}' != actual '{actual_version}'"
        )

    def test_report_line2_package_count(self):
        """Line 2 must be a positive integer (number of packages fixed)."""
        lines = _read_report_lines()
        assert len(lines) >= 2, "Report has fewer than 2 lines"
        line2 = lines[1].strip()
        assert line2.isdigit(), (
            f"Line 2 is not an integer: '{line2}'"
        )
        count = int(line2)
        assert count >= 3, (
            f"At least 3 packages should have been fixed, got {count}"
        )

    def test_report_package_count_matches_listed(self):
        """The count on line 2 must match the number of package lines that follow."""
        lines = _read_report_lines()
        assert len(lines) >= 3, "Report has fewer than 3 lines"
        count = int(lines[1].strip())
        package_lines = [l.strip() for l in lines[2:] if l.strip()]
        assert len(package_lines) == count, (
            f"Line 2 says {count} packages but {len(package_lines)} listed: {package_lines}"
        )

    def test_report_contains_required_packages(self):
        """The report must list at least the 3 required packages."""
        lines = _read_report_lines()
        assert len(lines) >= 3, "Report has fewer than 3 lines"
        package_lines = {l.strip() for l in lines[2:] if l.strip()}
        for pkg in REQUIRED_PACKAGES:
            assert pkg in package_lines, (
                f"Required package '{pkg}' not listed in report. "
                f"Found: {package_lines}"
            )

    def test_report_packages_are_valid_dpkg_names(self):
        """Each listed package name should be a valid dpkg package name."""
        lines = _read_report_lines()
        if len(lines) < 3:
            return  # Other tests will catch this
        for line in lines[2:]:
            pkg = line.strip()
            if not pkg:
                continue
            # dpkg package names: lowercase alphanumeric, plus -, ., +
            assert re.match(r"^[a-z0-9][a-z0-9.+\-]+$", pkg), (
                f"Invalid package name in report: '{pkg}'"
            )


# ──────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────

def _read_report_lines():
    """Read recovery report and return list of lines."""
    assert os.path.isfile(RECOVERY_REPORT_PATH), (
        f"Recovery report not found at {RECOVERY_REPORT_PATH}"
    )
    with open(RECOVERY_REPORT_PATH, "r") as f:
        return f.readlines()
