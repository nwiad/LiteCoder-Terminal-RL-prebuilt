"""
Tests for Git-based Website Deployment System.

Validates that the agent correctly set up:
1. deployer user with correct home/shell
2. SSH key authentication with correct permissions
3. Bare Git repository owned by deployer
4. Executable post-receive hook
5. Web deployment directory
6. Deployed index.html via git push
"""

import os
import subprocess
import stat
import pwd


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def run(cmd, **kwargs):
    """Run a shell command and return its stdout."""
    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True, **kwargs
    )
    return result


def file_owner(path):
    """Return the username that owns *path*."""
    st = os.stat(path)
    return pwd.getpwuid(st.st_uid).pw_name


def octal_perms(path):
    """Return the octal permission string (e.g. '700') for *path*."""
    return oct(os.stat(path).st_mode & 0o777)[2:]


# ===========================================================================
# 1. deployer user
# ===========================================================================

class TestDeployerUser:

    def test_user_exists(self):
        """The 'deployer' user must exist on the system."""
        try:
            pwd.getpwnam("deployer")
        except KeyError:
            assert False, "User 'deployer' does not exist"

    def test_home_directory(self):
        """Home directory must be /home/deployer and must exist."""
        info = pwd.getpwnam("deployer")
        assert info.pw_dir == "/home/deployer", (
            f"Expected home /home/deployer, got {info.pw_dir}"
        )
        assert os.path.isdir("/home/deployer"), "/home/deployer does not exist"

    def test_login_shell(self):
        """deployer must have a valid login shell (e.g. /bin/bash)."""
        info = pwd.getpwnam("deployer")
        # Accept any real shell, but it must not be /usr/sbin/nologin or /bin/false
        assert info.pw_shell not in ("/usr/sbin/nologin", "/bin/false", ""), (
            f"deployer has invalid shell: {info.pw_shell}"
        )


# ===========================================================================
# 2. SSH key authentication
# ===========================================================================

class TestSSHKeys:

    SSH_DIR = "/home/deployer/.ssh"
    PRIVATE_KEY = "/home/deployer/.ssh/id_ed25519"
    PUBLIC_KEY = "/home/deployer/.ssh/id_ed25519.pub"
    AUTH_KEYS = "/home/deployer/.ssh/authorized_keys"

    def test_ssh_dir_exists(self):
        assert os.path.isdir(self.SSH_DIR), ".ssh directory missing"

    def test_ssh_dir_permissions(self):
        perms = octal_perms(self.SSH_DIR)
        assert perms == "700", f".ssh dir perms should be 700, got {perms}"

    def test_private_key_exists(self):
        assert os.path.isfile(self.PRIVATE_KEY), "Private key missing"

    def test_private_key_is_ed25519(self):
        """The private key file must actually be an ed25519 key."""
        with open(self.PRIVATE_KEY, "r") as f:
            first_line = f.readline().strip()
        assert "PRIVATE KEY" in first_line, (
            f"Private key does not look like a PEM key: {first_line}"
        )

    def test_public_key_exists(self):
        assert os.path.isfile(self.PUBLIC_KEY), "Public key missing"

    def test_public_key_is_ed25519(self):
        with open(self.PUBLIC_KEY, "r") as f:
            content = f.read().strip()
        assert content.startswith("ssh-ed25519"), (
            "Public key is not ed25519 type"
        )

    def test_authorized_keys_exists(self):
        assert os.path.isfile(self.AUTH_KEYS), "authorized_keys missing"

    def test_authorized_keys_permissions(self):
        perms = octal_perms(self.AUTH_KEYS)
        assert perms == "600", (
            f"authorized_keys perms should be 600, got {perms}"
        )

    def test_authorized_keys_contains_public_key(self):
        """authorized_keys must contain the deployer's public key."""
        with open(self.PUBLIC_KEY, "r") as f:
            pub = f.read().strip()
        with open(self.AUTH_KEYS, "r") as f:
            ak = f.read().strip()
        # The public key (or at least its key material) must appear
        # Extract just the key data (second field) for flexible matching
        pub_key_data = pub.split()[1] if len(pub.split()) >= 2 else pub
        assert pub_key_data in ak, (
            "Public key not found in authorized_keys"
        )

    def test_ssh_dir_ownership(self):
        owner = file_owner(self.SSH_DIR)
        assert owner == "deployer", (
            f".ssh dir owned by {owner}, expected deployer"
        )


# ===========================================================================
# 3. Bare Git repository
# ===========================================================================

class TestBareRepo:

    BARE_REPO = "/srv/git/website.git"

    def test_bare_repo_exists(self):
        assert os.path.isdir(self.BARE_REPO), "Bare repo directory missing"

    def test_is_bare_repository(self):
        """A bare repo has HEAD at its root (not inside a .git subdir)."""
        assert os.path.isfile(os.path.join(self.BARE_REPO, "HEAD")), (
            "HEAD file missing — not a valid bare repo"
        )
        # A bare repo should NOT have a .git subdirectory
        assert not os.path.isdir(os.path.join(self.BARE_REPO, ".git")), (
            "Found .git subdir — this is not a bare repository"
        )

    def test_bare_repo_ownership(self):
        owner = file_owner(self.BARE_REPO)
        assert owner == "deployer", (
            f"Bare repo owned by {owner}, expected deployer"
        )

    def test_main_branch_has_commits(self):
        """The bare repo must have at least one commit on 'main'."""
        result = run(
            f"git -C {self.BARE_REPO} rev-parse --verify main"
        )
        assert result.returncode == 0, (
            "Bare repo has no 'main' branch or no commits on it"
        )

    def test_main_branch_commit_count(self):
        """There must be at least 1 commit on main."""
        result = run(
            f"git -C {self.BARE_REPO} rev-list --count main"
        )
        assert result.returncode == 0, "Could not count commits"
        count = int(result.stdout.strip())
        assert count >= 1, f"Expected >=1 commit on main, got {count}"


# ===========================================================================
# 4. Post-receive hook
# ===========================================================================

class TestPostReceiveHook:

    HOOK = "/srv/git/website.git/hooks/post-receive"

    def test_hook_exists(self):
        assert os.path.isfile(self.HOOK), "post-receive hook missing"

    def test_hook_is_executable(self):
        mode = os.stat(self.HOOK).st_mode
        assert mode & stat.S_IXUSR, "Hook is not executable by owner"

    def test_hook_references_main(self):
        """Hook must reference the 'main' branch."""
        with open(self.HOOK, "r") as f:
            content = f.read()
        assert "main" in content, (
            "Hook does not reference 'main' branch"
        )

    def test_hook_references_deploy_dir(self):
        """Hook must reference /var/www/html."""
        with open(self.HOOK, "r") as f:
            content = f.read()
        assert "/var/www/html" in content, (
            "Hook does not reference /var/www/html"
        )

    def test_hook_is_a_script(self):
        """Hook should start with a shebang or at least be a text file."""
        with open(self.HOOK, "r") as f:
            first_line = f.readline().strip()
        assert first_line.startswith("#!"), (
            f"Hook does not have a shebang line: {first_line}"
        )

    def test_hook_ownership(self):
        owner = file_owner(self.HOOK)
        assert owner == "deployer", (
            f"Hook owned by {owner}, expected deployer"
        )


# ===========================================================================
# 5. Web deployment directory
# ===========================================================================

class TestWebDirectory:

    WEB_DIR = "/var/www/html"

    def test_web_dir_exists(self):
        assert os.path.isdir(self.WEB_DIR), "/var/www/html does not exist"

    def test_web_dir_writable_by_deployer(self):
        """deployer must be able to write to /var/www/html."""
        # Check ownership or group write — the simplest reliable check
        # is to verify deployer owns it or it's world-writable
        st = os.stat(self.WEB_DIR)
        deployer_uid = pwd.getpwnam("deployer").pw_uid
        owner_ok = st.st_uid == deployer_uid
        world_writable = bool(st.st_mode & stat.S_IWOTH)
        group_writable = bool(st.st_mode & stat.S_IWGRP)
        assert owner_ok or world_writable or group_writable, (
            "/var/www/html is not writable by deployer"
        )


# ===========================================================================
# 6. Deployed content (the end-to-end proof)
# ===========================================================================

class TestDeployedContent:

    INDEX = "/var/www/html/index.html"

    def test_index_html_exists(self):
        assert os.path.isfile(self.INDEX), (
            "/var/www/html/index.html does not exist — deployment failed"
        )

    def test_index_html_not_empty(self):
        size = os.path.getsize(self.INDEX)
        assert size > 0, "index.html is empty"

    def test_index_html_contains_deployed_string(self):
        """Must contain the exact string 'Deployed via Git'."""
        with open(self.INDEX, "r") as f:
            content = f.read()
        assert "Deployed via Git" in content, (
            f"index.html does not contain 'Deployed via Git'. "
            f"Content: {content[:200]}"
        )

    def test_index_html_is_valid_html(self):
        """Basic sanity: must contain <html> and <body> tags."""
        with open(self.INDEX, "r") as f:
            content = f.read().lower()
        assert "<html>" in content or "<html " in content, (
            "index.html missing <html> tag"
        )
        assert "<body>" in content or "<body " in content, (
            "index.html missing <body> tag"
        )

    def test_index_html_has_h1(self):
        """The deployed page must have an <h1> heading."""
        with open(self.INDEX, "r") as f:
            content = f.read().lower()
        assert "<h1>" in content, "index.html missing <h1> tag"


# ===========================================================================
# 7. Local repository validation
# ===========================================================================

class TestLocalRepo:

    LOCAL_REPO = "/home/deployer/website-local"

    def test_local_repo_exists(self):
        assert os.path.isdir(self.LOCAL_REPO), (
            "Local repo /home/deployer/website-local missing"
        )

    def test_local_repo_is_git_repo(self):
        assert os.path.isdir(os.path.join(self.LOCAL_REPO, ".git")), (
            "website-local is not a git repository"
        )

    def test_production_remote_exists(self):
        """Local repo must have a remote named 'production'."""
        result = run(
            f"git -C {self.LOCAL_REPO} remote"
        )
        remotes = result.stdout.strip().splitlines()
        assert "production" in remotes, (
            f"No 'production' remote found. Remotes: {remotes}"
        )

    def test_production_remote_url(self):
        """production remote must point to /srv/git/website.git."""
        result = run(
            f"git -C {self.LOCAL_REPO} remote get-url production"
        )
        url = result.stdout.strip()
        assert "website.git" in url, (
            f"production remote URL unexpected: {url}"
        )

    def test_local_repo_has_index_html(self):
        """The local repo must contain index.html."""
        assert os.path.isfile(
            os.path.join(self.LOCAL_REPO, "index.html")
        ), "index.html missing from local repo"

    def test_local_main_branch_exists(self):
        """Local repo must have a main branch."""
        result = run(
            f"git -C {self.LOCAL_REPO} rev-parse --verify main"
        )
        assert result.returncode == 0, (
            "Local repo has no 'main' branch"
        )
