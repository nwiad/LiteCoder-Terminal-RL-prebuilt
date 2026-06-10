import os
import subprocess
import re


def run_git_command(cmd, cwd="/app"):
    """Helper to run git commands and return output."""
    result = subprocess.run(
        cmd,
        shell=True,
        cwd=cwd,
        capture_output=True,
        text=True
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def test_docs_integrated_branch_exists():
    """Test that the docs-integrated branch exists."""
    returncode, stdout, stderr = run_git_command("git branch --list docs-integrated")
    assert "docs-integrated" in stdout, "Branch 'docs-integrated' does not exist"


def test_docs_integrated_created_from_main():
    """Test that docs-integrated was created from main branch."""
    # Get the commit hash where docs-integrated diverged from main
    returncode, stdout, stderr = run_git_command("git merge-base main docs-integrated")
    merge_base = stdout

    # Get the latest commit on main
    returncode, stdout, stderr = run_git_command("git rev-parse main")
    main_commit = stdout

    assert merge_base == main_commit, "docs-integrated was not created from the latest main branch"


def test_sensors_file_exists():
    """Test that sensors.md file exists in docs-integrated branch."""
    returncode, stdout, stderr = run_git_command("git checkout docs-integrated")
    assert returncode == 0, "Failed to checkout docs-integrated branch"

    assert os.path.exists("/app/sensors.md"), "sensors.md file does not exist"


def test_no_conflict_markers():
    """Test that no git conflict markers remain in sensors.md."""
    returncode, stdout, stderr = run_git_command("git checkout docs-integrated")
    assert returncode == 0, "Failed to checkout docs-integrated branch"

    with open("/app/sensors.md", "r") as f:
        content = f.read()

    conflict_markers = ["<<<<<<<", "=======", ">>>>>>>"]
    for marker in conflict_markers:
        assert marker not in content, f"Conflict marker '{marker}' found in sensors.md"


def test_temperature_section_present():
    """Test that temperature sensor documentation is present with key specs."""
    returncode, stdout, stderr = run_git_command("git checkout docs-integrated")
    assert returncode == 0, "Failed to checkout docs-integrated branch"

    with open("/app/sensors.md", "r") as f:
        content = f.read().lower()

    # Check for temperature section header
    assert "temperature sensor" in content, "Temperature sensor section not found"

    # Check for key technical specifications (flexible matching)
    assert "-40" in content or "40" in content, "Temperature range not found"
    assert "125" in content, "Temperature max range not found"
    assert "0.5" in content or "±0.5" in content, "Temperature accuracy not found"


def test_humidity_section_present():
    """Test that humidity sensor documentation is present with key specs."""
    returncode, stdout, stderr = run_git_command("git checkout docs-integrated")
    assert returncode == 0, "Failed to checkout docs-integrated branch"

    with open("/app/sensors.md", "r") as f:
        content = f.read().lower()

    # Check for humidity section header
    assert "humidity sensor" in content, "Humidity sensor section not found"

    # Check for key technical specifications
    assert "0%" in content or "0 %" in content, "Humidity range minimum not found"
    assert "100%" in content or "100 %" in content, "Humidity range maximum not found"
    assert "±2" in content or "2%" in content, "Humidity accuracy not found"


def test_humidity_contains_moist():
    """Test that humidity documentation contains the word 'moist' (case-insensitive)."""
    returncode, stdout, stderr = run_git_command("git checkout docs-integrated")
    assert returncode == 0, "Failed to checkout docs-integrated branch"

    with open("/app/sensors.md", "r") as f:
        content = f.read().lower()

    assert "moist" in content, "The word 'moist' is not found in the humidity documentation"


def test_pressure_section_present():
    """Test that pressure sensor documentation is present with key specs."""
    returncode, stdout, stderr = run_git_command("git checkout docs-integrated")
    assert returncode == 0, "Failed to checkout docs-integrated branch"

    with open("/app/sensors.md", "r") as f:
        content = f.read().lower()

    # Check for pressure section header
    assert "pressure sensor" in content, "Pressure sensor section not found"

    # Check for key technical specifications
    assert "300" in content, "Pressure range minimum not found"
    assert "1100" in content, "Pressure range maximum not found"
    assert "±1" in content or "1 hpa" in content, "Pressure accuracy not found"


def test_all_three_branches_merged():
    """Test that all three feature branches were merged into docs-integrated."""
    returncode, stdout, stderr = run_git_command("git checkout docs-integrated")
    assert returncode == 0, "Failed to checkout docs-integrated branch"

    # Get the commit log to check merge history
    returncode, stdout, stderr = run_git_command("git log --oneline --all --graph")
    log_content = stdout.lower()

    # Check that all three branches appear in the history
    # We look for evidence of merges from each branch
    returncode, stdout, stderr = run_git_command("git log --oneline docs-integrated")
    log_content = stdout.lower()

    # Count commits that reference the feature branches
    has_temp = "temperature" in log_content or "docs-temperature" in log_content
    has_humidity = "humidity" in log_content or "docs-humidity" in log_content
    has_pressure = "pressure" in log_content or "docs-pressure" in log_content

    assert has_temp, "No evidence of docs-temperature merge in commit history"
    assert has_humidity, "No evidence of docs-humidity merge in commit history"
    assert has_pressure, "No evidence of docs-pressure merge in commit history"


def test_branch_pushed_to_remote():
    """Test that docs-integrated branch was pushed to origin remote."""
    # Check if the branch exists on the remote
    returncode, stdout, stderr = run_git_command("git ls-remote origin docs-integrated")

    assert returncode == 0, "Failed to query remote repository"
    assert "docs-integrated" in stdout, "Branch 'docs-integrated' was not pushed to remote 'origin'"
    assert len(stdout) > 0, "Remote branch 'docs-integrated' has no commits"


def test_merge_order_preserved():
    """Test that branches were merged in the correct order: temperature, humidity, pressure."""
    returncode, stdout, stderr = run_git_command("git checkout docs-integrated")
    assert returncode == 0, "Failed to checkout docs-integrated branch"

    # Get commit history with timestamps
    returncode, stdout, stderr = run_git_command(
        "git log --pretty=format:'%H %s' --reverse docs-integrated"
    )

    commits = stdout.lower().split('\n')

    # Find positions of merge commits
    temp_pos = -1
    humidity_pos = -1
    pressure_pos = -1

    for i, commit in enumerate(commits):
        if "temperature" in commit:
            if temp_pos == -1:
                temp_pos = i
        if "humidity" in commit:
            if humidity_pos == -1:
                humidity_pos = i
        if "pressure" in commit:
            if pressure_pos == -1:
                pressure_pos = i

    # Verify order: temperature < humidity < pressure
    if temp_pos != -1 and humidity_pos != -1:
        assert temp_pos < humidity_pos, "Temperature was not merged before humidity"

    if humidity_pos != -1 and pressure_pos != -1:
        assert humidity_pos < pressure_pos, "Humidity was not merged before pressure"


def test_file_not_empty():
    """Test that sensors.md is not empty or trivially small."""
    returncode, stdout, stderr = run_git_command("git checkout docs-integrated")
    assert returncode == 0, "Failed to checkout docs-integrated branch"

    with open("/app/sensors.md", "r") as f:
        content = f.read()

    # File should have substantial content (at least 500 characters for all three sections)
    assert len(content) > 500, "sensors.md appears to be empty or too small"

    # Should have multiple lines
    lines = content.strip().split('\n')
    assert len(lines) > 20, "sensors.md has too few lines"


def test_general_specifications_preserved():
    """Test that the original general specifications section is preserved."""
    returncode, stdout, stderr = run_git_command("git checkout docs-integrated")
    assert returncode == 0, "Failed to checkout docs-integrated branch"

    with open("/app/sensors.md", "r") as f:
        content = f.read().lower()

    # Check that general specifications are still present
    assert "general specifications" in content or "specifications" in content, \
        "General specifications section not found"
    assert "5v" in content or "5 v" in content, "Power supply specification not found"
    assert "i2c" in content, "I2C communication protocol not found"
