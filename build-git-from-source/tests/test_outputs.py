"""
Tests for Build Git from Source task.

Validates that Git was compiled from source with custom configuration,
installed correctly, and all required outputs are present and valid.
"""

import json
import os
import subprocess
import re

# ─── Paths ───────────────────────────────────────────────────────────────────

GIT_BINARY = "/opt/git-custom/bin/git"
SYMLINK_PATH = "/usr/local/bin/git-custom"
OUTPUT_JSON = "/app/output.json"
TEST_REPO = "/app/test-repo"
SOURCE_DIR = "/app/git-source"
INSTALL_PREFIX = "/opt/git-custom"


# ─── 1. Git binary existence and executability ──────────────────────────────

class TestGitBinaryInstallation:

    def test_git_binary_exists(self):
        """The custom git binary must exist at /opt/git-custom/bin/git."""
        assert os.path.exists(GIT_BINARY), (
            f"Git binary not found at {GIT_BINARY}"
        )

    def test_git_binary_is_executable(self):
        """The binary must have execute permissions."""
        assert os.path.isfile(GIT_BINARY), f"{GIT_BINARY} is not a regular file"
        assert os.access(GIT_BINARY, os.X_OK), f"{GIT_BINARY} is not executable"

    def test_git_binary_is_not_symlink_to_system_git(self):
        """The binary must be a real compiled binary, not a symlink to system git."""
        # Resolve the real path of the binary
        real_path = os.path.realpath(GIT_BINARY)
        # It should live under /opt/git-custom, not /usr/bin or /usr/lib
        assert real_path.startswith("/opt/git-custom"), (
            f"Git binary resolves to {real_path}, expected it under /opt/git-custom/. "
            "It may be a symlink to system git."
        )

    def test_git_binary_is_elf(self):
        """The binary should be a real compiled ELF executable."""
        result = subprocess.run(
            ["file", GIT_BINARY], capture_output=True, text=True
        )
        assert "ELF" in result.stdout, (
            f"Expected {GIT_BINARY} to be an ELF binary, got: {result.stdout.strip()}"
        )

    def test_git_binary_runs(self):
        """The binary must execute and return a version string."""
        result = subprocess.run(
            [GIT_BINARY, "--version"], capture_output=True, text=True, timeout=10
        )
        assert result.returncode == 0, (
            f"git --version failed with rc={result.returncode}: {result.stderr}"
        )
        assert "git version" in result.stdout, (
            f"Unexpected version output: {result.stdout}"
        )

    def test_git_version_at_least_2_40(self):
        """Git version must be 2.40 or later as required."""
        result = subprocess.run(
            [GIT_BINARY, "--version"], capture_output=True, text=True, timeout=10
        )
        # Parse version like "git version 2.47.0"
        match = re.search(r"git version (\d+)\.(\d+)", result.stdout)
        assert match, f"Could not parse version from: {result.stdout}"
        major, minor = int(match.group(1)), int(match.group(2))
        assert (major, minor) >= (2, 40), (
            f"Git version {major}.{minor} is below minimum 2.40"
        )


# ─── 2. Symlink ─────────────────────────────────────────────────────────────

class TestSymlink:

    def test_symlink_exists(self):
        """Symlink /usr/local/bin/git-custom must exist."""
        assert os.path.exists(SYMLINK_PATH), (
            f"Symlink not found at {SYMLINK_PATH}"
        )

    def test_symlink_is_link(self):
        """The path must be an actual symbolic link."""
        assert os.path.islink(SYMLINK_PATH), (
            f"{SYMLINK_PATH} exists but is not a symbolic link"
        )

    def test_symlink_target(self):
        """Symlink must point to /opt/git-custom/bin/git."""
        target = os.readlink(SYMLINK_PATH)
        assert target == GIT_BINARY, (
            f"Symlink points to {target}, expected {GIT_BINARY}"
        )

    def test_symlink_works(self):
        """Running git-custom --version must succeed."""
        result = subprocess.run(
            [SYMLINK_PATH, "--version"], capture_output=True, text=True, timeout=10
        )
        assert result.returncode == 0, (
            f"git-custom --version failed: {result.stderr}"
        )
        assert "git version" in result.stdout


# ─── 3. PCRE support ────────────────────────────────────────────────────────

class TestPCRESupport:

    def test_pcre_grep_works(self):
        """
        git grep -P (Perl-compatible regex) must work, proving PCRE was compiled in.
        We create a tiny repo, add a file, commit, and run git grep -P.
        """
        test_dir = "/tmp/_pcre_verify_test"
        os.makedirs(test_dir, exist_ok=True)
        try:
            subprocess.run([GIT_BINARY, "init"], cwd=test_dir,
                           capture_output=True, text=True, timeout=10)
            # Create a test file
            with open(os.path.join(test_dir, "sample.txt"), "w") as f:
                f.write("hello world\n")
            subprocess.run([GIT_BINARY, "add", "."], cwd=test_dir,
                           capture_output=True, timeout=10)
            subprocess.run(
                [GIT_BINARY, "-c", "user.email=t@t.com", "-c", "user.name=T",
                 "commit", "-m", "init"],
                cwd=test_dir, capture_output=True, timeout=10
            )
            # The actual PCRE test: use a Perl regex feature (\w+)
            result = subprocess.run(
                [GIT_BINARY, "grep", "-P", r"\bhel\w+", "--", "sample.txt"],
                cwd=test_dir, capture_output=True, text=True, timeout=10
            )
            assert result.returncode == 0, (
                f"git grep -P failed (rc={result.returncode}). "
                f"PCRE may not be compiled in. stderr: {result.stderr}"
            )
            assert "hello" in result.stdout, (
                f"git grep -P did not match expected content: {result.stdout}"
            )
        finally:
            subprocess.run(["rm", "-rf", test_dir], capture_output=True)


# ─── 4. Test repository ─────────────────────────────────────────────────────

class TestTestRepo:

    def test_test_repo_exists(self):
        """The test repo directory /app/test-repo/ must exist."""
        assert os.path.isdir(TEST_REPO), (
            f"Test repo directory not found at {TEST_REPO}"
        )

    def test_test_repo_is_git_repo(self):
        """The test repo must be a valid git repository."""
        git_dir = os.path.join(TEST_REPO, ".git")
        assert os.path.isdir(git_dir), (
            f"{TEST_REPO} is not a git repository (no .git directory)"
        )

    def test_test_repo_has_head(self):
        """The test repo must have a HEAD reference."""
        head_file = os.path.join(TEST_REPO, ".git", "HEAD")
        assert os.path.isfile(head_file), (
            f"No HEAD file in {TEST_REPO}/.git/"
        )


# ─── 5. Source cleanup ──────────────────────────────────────────────────────

class TestCleanup:

    def test_source_dir_removed(self):
        """/app/git-source/ must not exist after task completion."""
        assert not os.path.exists(SOURCE_DIR), (
            f"Source directory {SOURCE_DIR} still exists. Cleanup was not performed."
        )


# ─── 6. Output JSON report ──────────────────────────────────────────────────

def _load_output_json():
    """Helper to load and return the output JSON, or None on failure."""
    if not os.path.isfile(OUTPUT_JSON):
        return None
    with open(OUTPUT_JSON, "r") as f:
        content = f.read().strip()
    if not content:
        return None
    return json.loads(content)


class TestOutputJSON:

    def test_output_json_exists(self):
        """The report file /app/output.json must exist."""
        assert os.path.isfile(OUTPUT_JSON), (
            f"Output JSON not found at {OUTPUT_JSON}"
        )

    def test_output_json_is_valid_json(self):
        """The file must contain valid JSON."""
        data = _load_output_json()
        assert data is not None, "output.json is empty or not valid JSON"
        assert isinstance(data, dict), "output.json root must be a JSON object"

    def test_output_json_has_required_keys(self):
        """All required keys must be present."""
        data = _load_output_json()
        assert data is not None, "Could not load output.json"
        required_keys = [
            "git_version",
            "install_prefix",
            "pcre_support",
            "binary_path",
            "symlink_path",
            "optimization_flags",
            "linker_flags",
            "test_repo_status",
        ]
        missing = [k for k in required_keys if k not in data]
        assert not missing, f"Missing keys in output.json: {missing}"

    def test_git_version_field(self):
        """git_version must contain 'git version' and match the actual binary output."""
        data = _load_output_json()
        assert data is not None, "Could not load output.json"
        version_str = data.get("git_version", "")
        assert "git version" in version_str, (
            f"git_version field does not contain 'git version': {version_str}"
        )
        # Cross-check with actual binary output
        result = subprocess.run(
            [GIT_BINARY, "--version"], capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            actual = result.stdout.strip()
            assert actual == version_str.strip(), (
                f"git_version in JSON ({version_str.strip()}) does not match "
                f"actual binary output ({actual})"
            )

    def test_install_prefix_field(self):
        """install_prefix must be /opt/git-custom."""
        data = _load_output_json()
        assert data is not None, "Could not load output.json"
        assert data.get("install_prefix") == "/opt/git-custom", (
            f"install_prefix is {data.get('install_prefix')}, expected /opt/git-custom"
        )

    def test_pcre_support_field(self):
        """pcre_support must be boolean true."""
        data = _load_output_json()
        assert data is not None, "Could not load output.json"
        val = data.get("pcre_support")
        assert val is True, (
            f"pcre_support is {val!r} (type {type(val).__name__}), expected True"
        )

    def test_binary_path_field(self):
        """binary_path must be /opt/git-custom/bin/git."""
        data = _load_output_json()
        assert data is not None, "Could not load output.json"
        assert data.get("binary_path") == "/opt/git-custom/bin/git", (
            f"binary_path is {data.get('binary_path')}"
        )

    def test_symlink_path_field(self):
        """symlink_path must be /usr/local/bin/git-custom."""
        data = _load_output_json()
        assert data is not None, "Could not load output.json"
        assert data.get("symlink_path") == "/usr/local/bin/git-custom", (
            f"symlink_path is {data.get('symlink_path')}"
        )

    def test_optimization_flags_field(self):
        """optimization_flags must be -O2."""
        data = _load_output_json()
        assert data is not None, "Could not load output.json"
        assert data.get("optimization_flags") == "-O2", (
            f"optimization_flags is {data.get('optimization_flags')}"
        )

    def test_linker_flags_field(self):
        """linker_flags must be -Wl,-O1."""
        data = _load_output_json()
        assert data is not None, "Could not load output.json"
        assert data.get("linker_flags") == "-Wl,-O1", (
            f"linker_flags is {data.get('linker_flags')}"
        )

    def test_test_repo_status_field(self):
        """test_repo_status must be a non-empty string referencing repo init."""
        data = _load_output_json()
        assert data is not None, "Could not load output.json"
        val = data.get("test_repo_status", "")
        assert isinstance(val, str) and len(val.strip()) > 0, (
            f"test_repo_status is empty or not a string: {val!r}"
        )


# ─── 7. Install directory structure ─────────────────────────────────────────

class TestInstallDirectoryStructure:

    def test_bin_directory_exists(self):
        """/opt/git-custom/bin/ must exist."""
        assert os.path.isdir(os.path.join(INSTALL_PREFIX, "bin")), (
            "Missing /opt/git-custom/bin/ directory"
        )

    def test_libexec_or_share_exists(self):
        """A proper Git install has libexec/git-core or share/."""
        libexec = os.path.isdir(os.path.join(INSTALL_PREFIX, "libexec", "git-core"))
        share = os.path.isdir(os.path.join(INSTALL_PREFIX, "share"))
        assert libexec or share, (
            "Neither libexec/git-core nor share/ found under /opt/git-custom. "
            "This doesn't look like a proper Git installation."
        )

    def test_git_core_commands_present(self):
        """Key git sub-commands should exist in the installation."""
        # A real Git install has helpers like git-upload-pack
        result = subprocess.run(
            [GIT_BINARY, "upload-pack", "--help"],
            capture_output=True, text=True, timeout=10
        )
        # Just checking it doesn't fail with "command not found" type error
        # upload-pack --help returns 0 or 129 depending on version, both are fine
        assert result.returncode in (0, 1, 129), (
            f"git upload-pack --help returned unexpected code {result.returncode}"
        )
