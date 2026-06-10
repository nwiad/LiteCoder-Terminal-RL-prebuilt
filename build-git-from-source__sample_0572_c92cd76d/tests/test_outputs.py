"""
Tests for the "Build and Install Git from Source" task.

Validates:
1. Source directory exists and is a valid Git repo with official Git source
2. Source is checked out at a stable release tag (v2.*, no -rc)
3. /usr/local/bin/git exists, is executable, reports version > 2.25.1
4. /app/build_report.json exists, is valid JSON, conforms to schema
5. Version consistency between binary, report, and checked-out tag
"""

import json
import os
import re
import subprocess
import stat


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SOURCE_DIR = "/app/git-source"
BINARY_PATH = "/usr/local/bin/git"
REPORT_PATH = "/app/build_report.json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def run(cmd, cwd=None):
    """Run a shell command and return stripped stdout."""
    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True, cwd=cwd, timeout=30
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def parse_version_from_tag(tag):
    """Extract numeric version from a tag like 'v2.47.1' -> '2.47.1'."""
    m = re.match(r"v?(\d+\.\d+\.\d+(?:\.\d+)?)", tag)
    if m:
        return m.group(1)
    return None


def version_tuple(version_str):
    """Convert '2.47.1' to (2, 47, 1) for comparison."""
    parts = version_str.split(".")
    return tuple(int(p) for p in parts)


# ===========================================================================
# Test 1: Source directory exists and is a Git repository
# ===========================================================================
def test_source_dir_exists():
    """The source directory /app/git-source must exist."""
    assert os.path.isdir(SOURCE_DIR), (
        f"Source directory {SOURCE_DIR} does not exist"
    )


def test_source_dir_is_git_repo():
    """The source directory must be a valid Git repository."""
    git_dir = os.path.join(SOURCE_DIR, ".git")
    assert os.path.exists(git_dir), (
        f"{SOURCE_DIR} is not a Git repository (no .git found)"
    )


def test_source_dir_contains_git_source():
    """
    The cloned repo must actually be the official Git source code,
    not some random repo. Check for signature files that exist in
    the Git source tree.
    """
    # The Git source repo always has a Makefile and GIT-VERSION-GEN
    makefile = os.path.join(SOURCE_DIR, "Makefile")
    version_gen = os.path.join(SOURCE_DIR, "GIT-VERSION-GEN")
    assert os.path.isfile(makefile), (
        f"Expected {makefile} in Git source tree"
    )
    assert os.path.isfile(version_gen), (
        f"Expected {version_gen} in Git source tree"
    )


# ===========================================================================
# Test 2: Checked out at a stable release tag
# ===========================================================================
def test_source_checked_out_at_stable_tag():
    """
    The source must be checked out at a tag matching v2.* without -rc.
    We use 'git describe --tags --exact-match' to get the current tag.
    """
    rc, stdout, stderr = run("git describe --tags --exact-match HEAD", cwd=SOURCE_DIR)
    assert rc == 0 and stdout, (
        f"Source is not checked out at an exact tag. "
        f"rc={rc}, stdout='{stdout}', stderr='{stderr}'"
    )
    tag = stdout.strip().split("\n")[0]
    assert tag.startswith("v2."), (
        f"Tag '{tag}' does not start with 'v2.'"
    )
    assert "-rc" not in tag, (
        f"Tag '{tag}' is a release candidate (contains -rc)"
    )


# ===========================================================================
# Test 3: Installed binary
# ===========================================================================
def test_binary_exists():
    """The compiled git binary must exist at /usr/local/bin/git."""
    assert os.path.isfile(BINARY_PATH), (
        f"Binary {BINARY_PATH} does not exist"
    )


def test_binary_is_executable():
    """The binary must be executable."""
    assert os.path.isfile(BINARY_PATH), f"{BINARY_PATH} does not exist"
    mode = os.stat(BINARY_PATH).st_mode
    assert mode & stat.S_IXUSR, (
        f"{BINARY_PATH} is not executable (mode={oct(mode)})"
    )


def test_binary_reports_version():
    """The binary must respond to --version with a valid version string."""
    rc, stdout, _ = run(f"{BINARY_PATH} --version")
    assert rc == 0, f"{BINARY_PATH} --version failed with rc={rc}"
    assert stdout.startswith("git version "), (
        f"Unexpected version output: '{stdout}'"
    )


def test_binary_version_newer_than_2_25_1():
    """
    The installed git must be newer than 2.25.1 (the ancient system git
    on Ubuntu 20.04). This ensures the agent actually built from a recent tag.
    """
    rc, stdout, _ = run(f"{BINARY_PATH} --version")
    assert rc == 0, f"{BINARY_PATH} --version failed"
    # Extract version number: "git version 2.47.1" -> "2.47.1"
    m = re.search(r"(\d+\.\d+\.\d+)", stdout)
    assert m, f"Could not parse version from '{stdout}'"
    ver = version_tuple(m.group(1))
    min_ver = version_tuple("2.25.1")
    assert ver > min_ver, (
        f"Installed version {m.group(1)} is not newer than 2.25.1"
    )


# ===========================================================================
# Test 4: Build report JSON
# ===========================================================================
def test_report_exists():
    """The build report must exist at /app/build_report.json."""
    assert os.path.isfile(REPORT_PATH), (
        f"Build report {REPORT_PATH} does not exist"
    )


def test_report_is_valid_json():
    """The report must be parseable JSON."""
    assert os.path.isfile(REPORT_PATH), f"{REPORT_PATH} missing"
    with open(REPORT_PATH, "r") as f:
        content = f.read().strip()
    assert len(content) > 2, "Build report is empty or trivially small"
    try:
        json.loads(content)
    except json.JSONDecodeError as e:
        raise AssertionError(f"Build report is not valid JSON: {e}")


def test_report_has_required_keys():
    """The report must contain all four required keys."""
    with open(REPORT_PATH, "r") as f:
        report = json.load(f)
    required = {"source_dir", "git_tag", "installed_binary", "installed_version"}
    missing = required - set(report.keys())
    assert not missing, f"Build report missing keys: {missing}"


def test_report_source_dir():
    """`source_dir` must be '/app/git-source'."""
    with open(REPORT_PATH, "r") as f:
        report = json.load(f)
    assert report.get("source_dir") == "/app/git-source", (
        f"source_dir is '{report.get('source_dir')}', expected '/app/git-source'"
    )


def test_report_installed_binary():
    """`installed_binary` must be '/usr/local/bin/git'."""
    with open(REPORT_PATH, "r") as f:
        report = json.load(f)
    assert report.get("installed_binary") == "/usr/local/bin/git", (
        f"installed_binary is '{report.get('installed_binary')}', "
        f"expected '/usr/local/bin/git'"
    )


def test_report_git_tag_format():
    """`git_tag` must start with 'v2.' and not contain '-rc'."""
    with open(REPORT_PATH, "r") as f:
        report = json.load(f)
    tag = report.get("git_tag", "")
    assert isinstance(tag, str) and tag.startswith("v2."), (
        f"git_tag '{tag}' does not start with 'v2.'"
    )
    assert "-rc" not in tag, (
        f"git_tag '{tag}' is a release candidate"
    )


def test_report_installed_version_format():
    """`installed_version` must start with 'git version ' and contain a version."""
    with open(REPORT_PATH, "r") as f:
        report = json.load(f)
    ver = report.get("installed_version", "")
    assert isinstance(ver, str) and ver.startswith("git version "), (
        f"installed_version '{ver}' does not start with 'git version '"
    )
    m = re.search(r"\d+\.\d+\.\d+", ver)
    assert m, f"No version number found in installed_version '{ver}'"


# ===========================================================================
# Test 5: Cross-consistency checks
# ===========================================================================
def test_report_tag_matches_checked_out_tag():
    """
    The git_tag in the report must match the tag actually checked out
    in the source directory. This catches hardcoded/fake reports.
    """
    with open(REPORT_PATH, "r") as f:
        report = json.load(f)
    report_tag = report.get("git_tag", "").strip()

    rc, stdout, _ = run("git describe --tags --exact-match HEAD", cwd=SOURCE_DIR)
    if rc != 0:
        # Fallback: try git tag --points-at HEAD
        rc2, stdout2, _ = run("git tag --points-at HEAD", cwd=SOURCE_DIR)
        assert rc2 == 0 and stdout2, "Cannot determine checked-out tag"
        actual_tags = [t.strip() for t in stdout2.split("\n") if t.strip()]
        assert report_tag in actual_tags, (
            f"Report tag '{report_tag}' not among checked-out tags {actual_tags}"
        )
    else:
        actual_tag = stdout.strip().split("\n")[0]
        assert report_tag == actual_tag, (
            f"Report tag '{report_tag}' != checked-out tag '{actual_tag}'"
        )


def test_report_version_matches_binary():
    """
    The installed_version in the report must match what the binary
    actually reports. This catches stale or fabricated reports.
    """
    with open(REPORT_PATH, "r") as f:
        report = json.load(f)
    report_version = report.get("installed_version", "").strip()

    rc, stdout, _ = run(f"{BINARY_PATH} --version")
    assert rc == 0, f"Could not run {BINARY_PATH} --version"
    actual_version = stdout.strip()

    assert report_version == actual_version, (
        f"Report version '{report_version}' != actual binary version '{actual_version}'"
    )


def test_tag_version_matches_binary_version():
    """
    The numeric version in the tag (e.g., v2.47.1 -> 2.47.1) must appear
    in the binary's version output. This ensures the binary was actually
    built from the checked-out tag, not from some other commit.
    """
    with open(REPORT_PATH, "r") as f:
        report = json.load(f)
    tag = report.get("git_tag", "")
    tag_version = parse_version_from_tag(tag)
    assert tag_version, f"Cannot parse version from tag '{tag}'"

    rc, stdout, _ = run(f"{BINARY_PATH} --version")
    assert rc == 0, f"Could not run {BINARY_PATH} --version"

    assert tag_version in stdout, (
        f"Tag version '{tag_version}' not found in binary output '{stdout}'"
    )


def test_binary_is_not_system_git():
    """
    Verify the binary at /usr/local/bin/git is not just a symlink to
    the system git. It should be a real compiled binary.
    """
    # Check it's not a symlink pointing to /usr/bin/git
    if os.path.islink(BINARY_PATH):
        target = os.readlink(BINARY_PATH)
        assert "/usr/bin" not in target, (
            f"{BINARY_PATH} is a symlink to system git: {target}"
        )
    # Also verify the binary path resolves differently from system git
    rc_local, local_out, _ = run(f"{BINARY_PATH} --version")
    rc_sys, sys_out, _ = run("/usr/bin/git --version")
    if rc_local == 0 and rc_sys == 0:
        # The locally built version should be >= the system version
        m_local = re.search(r"(\d+\.\d+\.\d+)", local_out)
        m_sys = re.search(r"(\d+\.\d+\.\d+)", sys_out)
        if m_local and m_sys:
            local_ver = version_tuple(m_local.group(1))
            sys_ver = version_tuple(m_sys.group(1))
            assert local_ver >= sys_ver, (
                f"Local git {m_local.group(1)} is older than system git {m_sys.group(1)}"
            )
