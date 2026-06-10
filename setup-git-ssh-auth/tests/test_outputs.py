"""
Tests for Git + SSH Configuration Task.
Validates all 9 requirements from instruction.md by checking
actual system state (git config, file permissions, repo state, etc.)
and the setup-report.txt output file.
"""

import os
import subprocess
import stat
import re


HOME = os.path.expanduser("~")
SSH_DIR = os.path.join(HOME, ".ssh")
PRIVATE_KEY = os.path.join(SSH_DIR, "id_ed25519")
PUBLIC_KEY = os.path.join(SSH_DIR, "id_ed25519.pub")
SSH_CONFIG = os.path.join(SSH_DIR, "config")
BARE_REPO = "/app/test-repo.git"
WORKSPACE = "/app/test-workspace"
REPORT_FILE = "/app/setup-report.txt"


def run(cmd, **kwargs):
    """Helper to run a shell command and return stripped stdout."""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, **kwargs)
    return result.stdout.strip(), result.returncode


# ============================================================
# Requirement 1: Git is installed
# ============================================================

class TestGitInstalled:
    def test_git_on_path(self):
        out, rc = run("which git")
        assert rc == 0, "git binary not found on PATH"

    def test_git_version_output(self):
        out, rc = run("git --version")
        assert rc == 0, "git --version failed"
        assert "git version" in out.lower(), f"Unexpected git version output: {out}"


# ============================================================
# Requirement 2: Global Git User Settings
# ============================================================

class TestGitUserConfig:
    def test_user_name(self):
        out, rc = run("git config --global user.name")
        assert rc == 0, "user.name not set in global git config"
        assert out == "John Developer", f"Expected 'John Developer', got '{out}'"

    def test_user_email(self):
        out, rc = run("git config --global user.email")
        assert rc == 0, "user.email not set in global git config"
        assert out == "john.developer@example.com", f"Expected 'john.developer@example.com', got '{out}'"

    def test_gitconfig_file_exists(self):
        gitconfig = os.path.join(HOME, ".gitconfig")
        assert os.path.isfile(gitconfig), f"~/.gitconfig not found at {gitconfig}"


# ============================================================
# Requirement 3: SSH Key Pair (Ed25519)
# ============================================================

class TestSSHKeyPair:
    def test_private_key_exists(self):
        assert os.path.isfile(PRIVATE_KEY), f"Private key not found at {PRIVATE_KEY}"

    def test_public_key_exists(self):
        assert os.path.isfile(PUBLIC_KEY), f"Public key not found at {PUBLIC_KEY}"

    def test_private_key_not_empty(self):
        assert os.path.getsize(PRIVATE_KEY) > 0, "Private key file is empty"

    def test_public_key_not_empty(self):
        assert os.path.getsize(PUBLIC_KEY) > 0, "Public key file is empty"

    def test_key_is_ed25519(self):
        """Verify the key type is Ed25519 by checking the public key content."""
        with open(PUBLIC_KEY, "r") as f:
            content = f.read().strip()
        assert content.startswith("ssh-ed25519"), (
            f"Public key does not start with 'ssh-ed25519'. Got: {content[:40]}"
        )

    def test_key_comment(self):
        """Verify the key comment contains the email."""
        with open(PUBLIC_KEY, "r") as f:
            content = f.read().strip()
        # Ed25519 public key format: ssh-ed25519 <base64> <comment>
        parts = content.split()
        assert len(parts) >= 3, "Public key missing comment field"
        assert parts[-1] == "john.developer@example.com", (
            f"Expected comment 'john.developer@example.com', got '{parts[-1]}'"
        )

    def test_key_fingerprint_valid(self):
        """Verify ssh-keygen can read the key and produce a fingerprint."""
        out, rc = run(f"ssh-keygen -lf {PUBLIC_KEY}")
        assert rc == 0, "ssh-keygen -lf failed on public key"
        assert "ED25519" in out.upper() or "256" in out, (
            f"Fingerprint doesn't indicate Ed25519 key: {out}"
        )


# ============================================================
# Requirement 4: SSH Config
# ============================================================

class TestSSHConfig:
    def test_ssh_config_exists(self):
        assert os.path.isfile(SSH_CONFIG), f"SSH config not found at {SSH_CONFIG}"

    def test_ssh_config_not_empty(self):
        assert os.path.getsize(SSH_CONFIG) > 0, "SSH config file is empty"

    def test_host_github_block(self):
        with open(SSH_CONFIG, "r") as f:
            content = f.read()
        # Normalize to lowercase for flexible matching
        lower = content.lower()
        assert "host github.com" in lower, "Missing 'Host github.com' block"

    def test_hostname_directive(self):
        with open(SSH_CONFIG, "r") as f:
            content = f.read()
        lower = content.lower()
        assert "hostname github.com" in lower, "Missing 'HostName github.com' directive"

    def test_user_directive(self):
        with open(SSH_CONFIG, "r") as f:
            content = f.read()
        lower = content.lower()
        assert "user git" in lower, "Missing 'User git' directive"

    def test_identityfile_directive(self):
        with open(SSH_CONFIG, "r") as f:
            content = f.read()
        assert "id_ed25519" in content, "Missing IdentityFile referencing id_ed25519"

    def test_identitiesonly_directive(self):
        with open(SSH_CONFIG, "r") as f:
            content = f.read()
        lower = content.lower()
        assert "identitiesonly yes" in lower, "Missing 'IdentitiesOnly yes' directive"


# ============================================================
# Requirement 5: File Permissions
# ============================================================

class TestFilePermissions:
    def _get_octal_perms(self, path):
        """Return octal permission string like '700', '600', '644'."""
        st = os.stat(path)
        return oct(stat.S_IMODE(st.st_mode))[-3:]

    def test_ssh_dir_permissions(self):
        perms = self._get_octal_perms(SSH_DIR)
        assert perms == "700", f"~/.ssh should be 700, got {perms}"

    def test_private_key_permissions(self):
        perms = self._get_octal_perms(PRIVATE_KEY)
        assert perms == "600", f"Private key should be 600, got {perms}"

    def test_public_key_permissions(self):
        perms = self._get_octal_perms(PUBLIC_KEY)
        assert perms == "644", f"Public key should be 644, got {perms}"

    def test_ssh_config_permissions(self):
        perms = self._get_octal_perms(SSH_CONFIG)
        assert perms == "600", f"SSH config should be 600, got {perms}"


# ============================================================
# Requirement 6: Local Test Repository
# ============================================================

class TestLocalRepository:
    def test_bare_repo_exists(self):
        assert os.path.isdir(BARE_REPO), f"Bare repo not found at {BARE_REPO}"

    def test_bare_repo_is_bare(self):
        """A bare repo has a HEAD file directly in its root."""
        head_file = os.path.join(BARE_REPO, "HEAD")
        assert os.path.isfile(head_file), f"Not a valid bare repo: missing HEAD at {head_file}"

    def test_workspace_exists(self):
        assert os.path.isdir(WORKSPACE), f"Workspace not found at {WORKSPACE}"

    def test_workspace_is_git_repo(self):
        git_dir = os.path.join(WORKSPACE, ".git")
        assert os.path.isdir(git_dir), f"Workspace is not a git repo (no .git dir)"

    def test_readme_exists(self):
        readme = os.path.join(WORKSPACE, "README.md")
        assert os.path.isfile(readme), f"README.md not found in workspace"

    def test_readme_content(self):
        readme = os.path.join(WORKSPACE, "README.md")
        with open(readme, "r") as f:
            content = f.read().strip()
        assert content == "# Test Repository", (
            f"Expected '# Test Repository', got '{content}'"
        )

    def test_commit_exists(self):
        """Verify at least one commit exists in the workspace."""
        out, rc = run("git log --oneline -1", cwd=WORKSPACE)
        assert rc == 0, "git log failed in workspace"
        assert len(out) > 0, "No commits found in workspace"

    def test_commit_message(self):
        """Verify the first commit message is 'Initial commit'."""
        out, rc = run("git log --format=%s -1", cwd=WORKSPACE)
        assert rc == 0, "git log failed"
        assert out.strip() == "Initial commit", (
            f"Expected commit message 'Initial commit', got '{out.strip()}'"
        )

    def test_push_succeeded(self):
        """Verify the bare repo has the commit (push worked)."""
        out, rc = run(f"git --git-dir={BARE_REPO} log --oneline -1")
        assert rc == 0, "git log on bare repo failed"
        assert len(out) > 0, "Bare repo has no commits — push likely failed"

    def test_bare_repo_commit_message(self):
        """Verify the bare repo received the correct commit."""
        out, rc = run(f"git --git-dir={BARE_REPO} log --format=%s -1")
        assert rc == 0, "git log on bare repo failed"
        assert out.strip() == "Initial commit", (
            f"Bare repo commit message: expected 'Initial commit', got '{out.strip()}'"
        )


# ============================================================
# Requirement 7: Git URL Rewrite (SSH by Default)
# ============================================================

class TestGitURLRewrite:
    def test_insteadof_config(self):
        out, rc = run('git config --global url."git@github.com:".insteadOf')
        assert rc == 0, "insteadOf config not set"
        assert out.strip() == "https://github.com/", (
            f"Expected 'https://github.com/', got '{out.strip()}'"
        )


# ============================================================
# Requirement 8: Git Aliases
# ============================================================

class TestGitAliases:
    EXPECTED_ALIASES = {
        "co": "checkout",
        "br": "branch",
        "ci": "commit",
        "st": "status",
        "lg": "log --oneline --graph --decorate",
    }

    def test_alias_co(self):
        out, rc = run("git config --global alias.co")
        assert rc == 0, "alias.co not set"
        assert out.strip() == self.EXPECTED_ALIASES["co"]

    def test_alias_br(self):
        out, rc = run("git config --global alias.br")
        assert rc == 0, "alias.br not set"
        assert out.strip() == self.EXPECTED_ALIASES["br"]

    def test_alias_ci(self):
        out, rc = run("git config --global alias.ci")
        assert rc == 0, "alias.ci not set"
        assert out.strip() == self.EXPECTED_ALIASES["ci"]

    def test_alias_st(self):
        out, rc = run("git config --global alias.st")
        assert rc == 0, "alias.st not set"
        assert out.strip() == self.EXPECTED_ALIASES["st"]

    def test_alias_lg(self):
        out, rc = run("git config --global alias.lg")
        assert rc == 0, "alias.lg not set"
        assert out.strip() == self.EXPECTED_ALIASES["lg"]


# ============================================================
# Requirement 9: Setup Report
# ============================================================

class TestSetupReport:
    def test_report_exists(self):
        assert os.path.isfile(REPORT_FILE), f"Report not found at {REPORT_FILE}"

    def test_report_not_empty(self):
        assert os.path.getsize(REPORT_FILE) > 0, "Report file is empty"

    def test_report_contains_git_version(self):
        with open(REPORT_FILE, "r") as f:
            content = f.read().lower()
        assert "git version" in content, "Report missing git version info"

    def test_report_contains_user_name(self):
        with open(REPORT_FILE, "r") as f:
            content = f.read()
        assert "John Developer" in content, "Report missing user.name"

    def test_report_contains_user_email(self):
        with open(REPORT_FILE, "r") as f:
            content = f.read()
        assert "john.developer@example.com" in content, "Report missing user.email"

    def test_report_contains_ssh_fingerprint(self):
        """Report should contain an SSH fingerprint (SHA256: or MD5: hash)."""
        with open(REPORT_FILE, "r") as f:
            content = f.read()
        has_sha256 = "SHA256:" in content
        has_md5 = "MD5:" in content
        # Also accept raw fingerprint patterns (hex colons)
        has_hex_fp = bool(re.search(r'[0-9a-fA-F]{2}(:[0-9a-fA-F]{2}){7,}', content))
        assert has_sha256 or has_md5 or has_hex_fp, (
            "Report missing SSH key fingerprint (no SHA256:, MD5:, or hex fingerprint found)"
        )

    def test_report_contains_aliases(self):
        """Report should mention the configured aliases."""
        with open(REPORT_FILE, "r") as f:
            content = f.read().lower()
        # Check that at least the alias names and values appear
        for alias in ["co", "br", "ci", "st", "lg"]:
            assert alias in content, f"Report missing alias '{alias}'"
        for value in ["checkout", "branch", "commit", "status"]:
            assert value in content, f"Report missing alias value '{value}'"
