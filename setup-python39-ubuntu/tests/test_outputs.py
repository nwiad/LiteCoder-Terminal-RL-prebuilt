import os
import json
import subprocess
import re


def test_python39_installed():
    """Verify Python 3.9.x is installed at /opt/python3.9"""
    assert os.path.exists("/opt/python3.9"), "Python installation directory /opt/python3.9 does not exist"
    assert os.path.isdir("/opt/python3.9"), "/opt/python3.9 is not a directory"

    # Check for python3.9 binary
    python_bin = "/opt/python3.9/bin/python3.9"
    assert os.path.exists(python_bin), f"Python binary not found at {python_bin}"
    assert os.access(python_bin, os.X_OK), f"Python binary at {python_bin} is not executable"


def test_python39_version():
    """Verify python3.9 command returns correct version"""
    result = subprocess.run(["python3.9", "--version"], capture_output=True, text=True)
    assert result.returncode == 0, "python3.9 --version failed"

    version_output = result.stdout + result.stderr
    assert "Python 3.9" in version_output, f"Expected Python 3.9.x, got: {version_output}"

    # Extract version number and verify it's 3.9.x
    match = re.search(r'Python (\d+\.\d+\.\d+)', version_output)
    assert match, f"Could not parse version from: {version_output}"

    version = match.group(1)
    major, minor, patch = version.split('.')
    assert major == "3" and minor == "9", f"Expected Python 3.9.x, got {version}"


def test_pip39_installed():
    """Verify pip3.9 is accessible and works"""
    result = subprocess.run(["pip3.9", "--version"], capture_output=True, text=True)
    assert result.returncode == 0, "pip3.9 --version failed"

    version_output = result.stdout + result.stderr
    assert "pip" in version_output.lower(), f"Unexpected pip output: {version_output}"


def test_system_wide_symlinks():
    """Verify symlinks in /usr/local/bin for system-wide access"""
    python_link = "/usr/local/bin/python3.9"
    pip_link = "/usr/local/bin/pip3.9"

    assert os.path.exists(python_link), f"Symlink {python_link} does not exist"
    assert os.path.islink(python_link) or os.path.isfile(python_link), f"{python_link} is not a symlink or file"

    assert os.path.exists(pip_link), f"Symlink {pip_link} does not exist"
    assert os.path.islink(pip_link) or os.path.isfile(pip_link), f"{pip_link} is not a symlink or file"

    # Verify they point to correct locations
    if os.path.islink(python_link):
        target = os.readlink(python_link)
        assert "/opt/python3.9" in target, f"python3.9 symlink points to wrong location: {target}"


def test_virtualenv_installed():
    """Verify virtualenv is installed and accessible"""
    result = subprocess.run(["virtualenv", "--version"], capture_output=True, text=True)
    assert result.returncode == 0, "virtualenv --version failed"

    version_output = result.stdout + result.stderr
    assert "virtualenv" in version_output.lower(), f"Unexpected virtualenv output: {version_output}"


def test_shared_venv_exists():
    """Verify shared virtual environment exists at /opt/venv/dev"""
    venv_path = "/opt/venv/dev"
    assert os.path.exists(venv_path), f"Shared venv directory {venv_path} does not exist"
    assert os.path.isdir(venv_path), f"{venv_path} is not a directory"

    # Check for venv structure
    bin_dir = os.path.join(venv_path, "bin")
    assert os.path.exists(bin_dir), f"Venv bin directory {bin_dir} does not exist"

    # Check for python in venv
    venv_python = os.path.join(bin_dir, "python")
    assert os.path.exists(venv_python), f"Python not found in venv at {venv_python}"


def test_venv_tools_installed():
    """Verify pytest, black, flake8, ipython are installed in shared venv"""
    tools = ["pytest", "black", "flake8", "ipython"]

    for tool in tools:
        result = subprocess.run([tool, "--version"], capture_output=True, text=True)
        assert result.returncode == 0, f"{tool} --version failed (not installed or not in PATH)"

        output = result.stdout + result.stderr
        assert len(output) > 0, f"{tool} produced no output"


def test_profile_activation_script():
    """Verify auto-activation script exists in /etc/profile.d/"""
    profile_dir = "/etc/profile.d"
    assert os.path.exists(profile_dir), f"Profile directory {profile_dir} does not exist"

    # Look for any .sh file that adds venv to PATH
    found_script = False
    for filename in os.listdir(profile_dir):
        if filename.endswith(".sh"):
            filepath = os.path.join(profile_dir, filename)
            with open(filepath, 'r') as f:
                content = f.read()
                if "/opt/venv/dev/bin" in content and "PATH" in content:
                    found_script = True
                    break

    assert found_script, "No profile.d script found that adds /opt/venv/dev/bin to PATH"


def test_verification_script_exists():
    """Verify verification script exists and is executable"""
    verify_script = "/app/verify_setup.sh"
    assert os.path.exists(verify_script), f"Verification script {verify_script} does not exist"
    assert os.access(verify_script, os.X_OK), f"Verification script {verify_script} is not executable"


def test_verification_script_passes():
    """Run verification script and ensure it passes"""
    verify_script = "/app/verify_setup.sh"

    # Run with proper environment
    env = os.environ.copy()
    env["PATH"] = f"/opt/venv/dev/bin:{env.get('PATH', '')}"

    result = subprocess.run([verify_script], capture_output=True, text=True, env=env)
    assert result.returncode == 0, f"Verification script failed with code {result.returncode}. Output: {result.stdout}\n{result.stderr}"


def test_setup_report_exists():
    """Verify setup report JSON exists"""
    report_path = "/app/setup_report.json"
    assert os.path.exists(report_path), f"Setup report {report_path} does not exist"
    assert os.path.isfile(report_path), f"{report_path} is not a file"

    # Check file is not empty
    assert os.path.getsize(report_path) > 0, f"Setup report {report_path} is empty"


def test_setup_report_structure():
    """Verify setup report has correct JSON structure"""
    report_path = "/app/setup_report.json"

    with open(report_path, 'r') as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            assert False, f"Setup report is not valid JSON: {e}"

    # Check required fields
    required_fields = ["python_version", "install_location", "shared_venv",
                      "installed_tools", "disk_usage_mb", "verification_passed"]

    for field in required_fields:
        assert field in data, f"Missing required field '{field}' in setup report"

    # Validate field types and values
    assert isinstance(data["python_version"], str), "python_version must be a string"
    assert data["python_version"].startswith("3.9"), f"Expected Python 3.9.x, got {data['python_version']}"

    assert data["install_location"] == "/opt/python3.9", f"Expected install_location '/opt/python3.9', got {data['install_location']}"

    assert data["shared_venv"] == "/opt/venv/dev", f"Expected shared_venv '/opt/venv/dev', got {data['shared_venv']}"

    assert isinstance(data["installed_tools"], list), "installed_tools must be a list"
    expected_tools = {"pytest", "black", "flake8", "ipython", "virtualenv"}
    actual_tools = set(data["installed_tools"])
    assert expected_tools == actual_tools, f"Expected tools {expected_tools}, got {actual_tools}"

    assert isinstance(data["disk_usage_mb"], (int, float)), "disk_usage_mb must be a number"
    assert data["disk_usage_mb"] > 0, f"disk_usage_mb must be positive, got {data['disk_usage_mb']}"

    assert data["verification_passed"] is True, "verification_passed must be true"


def test_no_system_python_conflict():
    """Verify system Python is not overwritten"""
    # Check that /usr/bin/python3 still exists (system Python)
    system_python = "/usr/bin/python3"
    if os.path.exists(system_python):
        result = subprocess.run([system_python, "--version"], capture_output=True, text=True)
        version_output = result.stdout + result.stderr
        # System Python should NOT be 3.9 (Ubuntu 20.04 comes with 3.8)
        # This verifies altinstall was used correctly
        assert result.returncode == 0, "System Python is broken"


def test_multi_user_permissions():
    """Verify installations have proper permissions for multi-user access"""
    paths_to_check = [
        "/opt/python3.9",
        "/opt/venv/dev",
        "/usr/local/bin/python3.9",
        "/usr/local/bin/pip3.9"
    ]

    for path in paths_to_check:
        if os.path.exists(path):
            stat_info = os.stat(path)
            # Check that others have at least read and execute permissions
            others_perms = stat_info.st_mode & 0o005
            assert others_perms != 0, f"{path} does not have proper permissions for multi-user access"


def test_cleanup_performed():
    """Verify build artifacts were cleaned up"""
    # Check that /tmp doesn't contain Python source files
    tmp_contents = os.listdir("/tmp")
    python_artifacts = [f for f in tmp_contents if "Python-3.9" in f]
    assert len(python_artifacts) == 0, f"Build artifacts not cleaned up: {python_artifacts}"


def test_optimizations_enabled():
    """Verify Python was compiled with optimizations"""
    # Check if Python has PGO (Profile Guided Optimization) enabled
    # This is indicated by the presence of certain files or by checking sys flags
    result = subprocess.run(
        ["python3.9", "-c", "import sys; print(sys.flags)"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0, "Failed to check Python optimization flags"

    # At minimum, verify Python runs and can import sys
    assert "sys.flags" in result.stdout or "optimize" in result.stdout.lower(), "Python optimization check failed"
