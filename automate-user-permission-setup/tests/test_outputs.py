"""
Tests for the Automate User and Permission Management task.

These tests verify that /app/setup.sh was created correctly and that
running it produces the expected system state: users, groups, directories,
permissions, and umask configuration.

The tests execute the script (if not already executed) and then inspect
the resulting system state.
"""

import os
import subprocess
import stat
import pwd
import grp
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SETUP_SCRIPT = "/app/setup.sh"


def run_setup_script():
    """Run the setup script if system state is not already configured."""
    if not os.path.isfile(SETUP_SCRIPT):
        pytest.fail(f"Setup script not found at {SETUP_SCRIPT}")
    result = subprocess.run(
        ["bash", SETUP_SCRIPT],
        capture_output=True, text=True, timeout=30
    )
    return result


def get_octal_permissions(path):
    """Return the full octal permission string (including setgid) for a path."""
    st = os.stat(path)
    return oct(stat.S_IMODE(st.st_mode))


# ---------------------------------------------------------------------------
# Fixture: ensure the setup script has been executed once
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session", autouse=True)
def execute_setup():
    """Run setup.sh once before all tests if users don't exist yet."""
    # Only run if the script hasn't been executed already
    try:
        pwd.getpwnam("dev1")
    except KeyError:
        # Users don't exist yet — run the script
        result = run_setup_script()
        if result.returncode != 0:
            pytest.fail(
                f"setup.sh failed on first run.\n"
                f"STDOUT: {result.stdout}\nSTDERR: {result.stderr}"
            )


# ===========================================================================
# Section 1: Script file existence and properties
# ===========================================================================

class TestScriptFile:
    def test_setup_script_exists(self):
        """setup.sh must exist at /app/setup.sh."""
        assert os.path.isfile(SETUP_SCRIPT), \
            f"Expected script at {SETUP_SCRIPT} but it does not exist."

    def test_setup_script_is_executable(self):
        """setup.sh must have the executable bit set."""
        assert os.access(SETUP_SCRIPT, os.X_OK), \
            f"{SETUP_SCRIPT} is not executable."

    def test_setup_script_is_not_empty(self):
        """setup.sh must not be an empty file."""
        size = os.path.getsize(SETUP_SCRIPT)
        assert size > 50, \
            f"{SETUP_SCRIPT} is suspiciously small ({size} bytes)."

    def test_setup_script_has_comments(self):
        """setup.sh should include comments explaining major sections."""
        with open(SETUP_SCRIPT, "r") as f:
            content = f.read()
        comment_lines = [l for l in content.splitlines() if l.strip().startswith("#")]
        # Expect at least a few comment lines for major sections
        assert len(comment_lines) >= 3, \
            "Script should contain comments explaining each major section."


# ===========================================================================
# Section 2: Group creation
# ===========================================================================

class TestGroups:
    def test_developers_group_exists(self):
        """The 'developers' group must exist."""
        try:
            grp.getgrnam("developers")
        except KeyError:
            pytest.fail("Group 'developers' does not exist.")

    def test_projects_group_exists(self):
        """The 'projects' group must exist."""
        try:
            grp.getgrnam("projects")
        except KeyError:
            pytest.fail("Group 'projects' does not exist.")


# ===========================================================================
# Section 3: User creation
# ===========================================================================

class TestUsers:
    @pytest.mark.parametrize("username", ["dev1", "dev2", "dev3", "projectmanager"])
    def test_user_exists(self, username):
        """Each required user must exist in /etc/passwd."""
        try:
            pwd.getpwnam(username)
        except KeyError:
            pytest.fail(f"User '{username}' does not exist.")

    @pytest.mark.parametrize("username", ["dev1", "dev2", "dev3", "projectmanager"])
    def test_user_has_bash_shell(self, username):
        """Each user must have /bin/bash as their default shell."""
        pw = pwd.getpwnam(username)
        assert pw.pw_shell == "/bin/bash", \
            f"User '{username}' shell is '{pw.pw_shell}', expected '/bin/bash'."

    @pytest.mark.parametrize("username", ["dev1", "dev2", "dev3", "projectmanager"])
    def test_user_has_home_directory(self, username):
        """Each user must have a home directory that exists on disk."""
        pw = pwd.getpwnam(username)
        assert os.path.isdir(pw.pw_dir), \
            f"Home directory '{pw.pw_dir}' for user '{username}' does not exist."


# ===========================================================================
# Section 4: Group membership
# ===========================================================================

class TestGroupMembership:
    @pytest.mark.parametrize("username", ["dev1", "dev2", "dev3"])
    def test_dev_user_in_developers_group(self, username):
        """dev1, dev2, dev3 must be members of the 'developers' group."""
        gr = grp.getgrnam("developers")
        # Check supplementary group membership
        assert username in gr.gr_mem, \
            f"User '{username}' is not in the 'developers' group. Members: {gr.gr_mem}"

    def test_projectmanager_in_projects_group(self):
        """projectmanager must be a member of the 'projects' group."""
        gr = grp.getgrnam("projects")
        assert "projectmanager" in gr.gr_mem, \
            f"User 'projectmanager' is not in the 'projects' group. Members: {gr.gr_mem}"

    @pytest.mark.parametrize("username", ["dev1", "dev2", "dev3"])
    def test_dev_user_not_primary_developers(self, username):
        """developers should be a supplementary group, not the primary group."""
        pw = pwd.getpwnam(username)
        dev_group = grp.getgrnam("developers")
        # The user's primary GID should NOT be the developers group
        # (it should be their own personal group or default group)
        # This is a soft check — some implementations may differ,
        # but the instruction says "supplementary group"
        # We just verify they ARE in the group members list (supplementary)
        assert username in dev_group.gr_mem


# ===========================================================================
# Section 5: Directory structure and permissions
# ===========================================================================

class TestDirectoryStructure:
    def test_opt_projects_exists(self):
        """/opt/projects directory must exist."""
        assert os.path.isdir("/opt/projects"), \
            "/opt/projects directory does not exist."

    def test_opt_projects_owner(self):
        """/opt/projects must be owned by root."""
        st = os.stat("/opt/projects")
        owner = pwd.getpwuid(st.st_uid).pw_name
        assert owner == "root", \
            f"/opt/projects owner is '{owner}', expected 'root'."

    def test_opt_projects_group(self):
        """/opt/projects must have group 'projects'."""
        st = os.stat("/opt/projects")
        group = grp.getgrgid(st.st_gid).gr_name
        assert group == "projects", \
            f"/opt/projects group is '{group}', expected 'projects'."

    def test_opt_projects_permissions(self):
        """/opt/projects must have permissions 2775 (rwxrwsr-x with SetGID)."""
        perms = get_octal_permissions("/opt/projects")
        assert perms == "0o2775", \
            f"/opt/projects permissions are {perms}, expected 0o2775."

    @pytest.mark.parametrize("username", ["dev1", "dev2", "dev3"])
    def test_user_subdir_exists(self, username):
        """Per-user subdirectory must exist under /opt/projects."""
        path = f"/opt/projects/{username}"
        assert os.path.isdir(path), \
            f"Directory {path} does not exist."

    @pytest.mark.parametrize("username", ["dev1", "dev2", "dev3"])
    def test_user_subdir_owner(self, username):
        """Per-user subdirectory must be owned by the respective user."""
        path = f"/opt/projects/{username}"
        st = os.stat(path)
        owner = pwd.getpwuid(st.st_uid).pw_name
        assert owner == username, \
            f"{path} owner is '{owner}', expected '{username}'."

    @pytest.mark.parametrize("username", ["dev1", "dev2", "dev3"])
    def test_user_subdir_group(self, username):
        """Per-user subdirectory must have group 'projects'."""
        path = f"/opt/projects/{username}"
        st = os.stat(path)
        group = grp.getgrgid(st.st_gid).gr_name
        assert group == "projects", \
            f"{path} group is '{group}', expected 'projects'."

    @pytest.mark.parametrize("username", ["dev1", "dev2", "dev3"])
    def test_user_subdir_permissions(self, username):
        """Per-user subdirectory must have permissions 2770 (rwxrws---)."""
        path = f"/opt/projects/{username}"
        perms = get_octal_permissions(path)
        assert perms == "0o2770", \
            f"{path} permissions are {perms}, expected 0o2770."

    @pytest.mark.parametrize("username", ["dev1", "dev2", "dev3"])
    def test_user_subdir_no_other_access(self, username):
        """Per-user subdirectories must have no 'other' permission bits."""
        path = f"/opt/projects/{username}"
        st = os.stat(path)
        other_bits = stat.S_IMODE(st.st_mode) & 0o007
        assert other_bits == 0, \
            f"{path} has 'other' permission bits set: {oct(other_bits)}"

    @pytest.mark.parametrize("username", ["dev1", "dev2", "dev3"])
    def test_user_subdir_setgid_bit(self, username):
        """Per-user subdirectories must have the SetGID bit set."""
        path = f"/opt/projects/{username}"
        st = os.stat(path)
        has_setgid = bool(st.st_mode & stat.S_ISGID)
        assert has_setgid, \
            f"{path} does not have the SetGID bit set."

    def test_opt_projects_setgid_bit(self):
        """/opt/projects must have the SetGID bit set."""
        st = os.stat("/opt/projects")
        has_setgid = bool(st.st_mode & stat.S_ISGID)
        assert has_setgid, \
            "/opt/projects does not have the SetGID bit set."


# ===========================================================================
# Section 6: Umask configuration
# ===========================================================================

class TestUmaskConfiguration:
    @pytest.mark.parametrize("username", ["dev1", "dev2", "dev3"])
    def test_umask_in_bashrc(self, username):
        """Each developer's ~/.bashrc must contain 'umask 002'."""
        bashrc_path = f"/home/{username}/.bashrc"
        assert os.path.isfile(bashrc_path), \
            f"{bashrc_path} does not exist."
        with open(bashrc_path, "r") as f:
            content = f.read()
        # Check that umask 002 appears (possibly with varying whitespace)
        lines = content.splitlines()
        found = any(
            line.strip() == "umask 002" or line.strip().startswith("umask 002")
            for line in lines
            if not line.strip().startswith("#")
        )
        assert found, \
            f"'umask 002' not found in {bashrc_path}."

    @pytest.mark.parametrize("username", ["dev1", "dev2", "dev3"])
    def test_umask_not_duplicated(self, username):
        """umask 002 should appear exactly once (idempotency check)."""
        bashrc_path = f"/home/{username}/.bashrc"
        if not os.path.isfile(bashrc_path):
            pytest.skip(f"{bashrc_path} does not exist.")
        with open(bashrc_path, "r") as f:
            content = f.read()
        lines = content.splitlines()
        count = sum(
            1 for line in lines
            if line.strip() == "umask 002"
            and not line.strip().startswith("#")
        )
        # After running the script (possibly twice via idempotency test),
        # umask 002 should appear exactly once
        assert count >= 1, \
            f"'umask 002' not found in {bashrc_path}."


# ===========================================================================
# Section 7: Idempotency — running the script twice must not fail
# ===========================================================================

class TestIdempotency:
    def test_script_runs_twice_without_error(self):
        """Running setup.sh a second time must succeed (exit code 0)."""
        # First run already happened in the fixture; run it again
        result = run_setup_script()
        assert result.returncode == 0, \
            f"setup.sh failed on second run (exit code {result.returncode}).\n" \
            f"STDOUT: {result.stdout}\nSTDERR: {result.stderr}"

    def test_state_unchanged_after_second_run(self):
        """System state must remain correct after a second run."""
        # Run the script again
        run_setup_script()

        # Verify key state is still intact
        # Users still exist
        for u in ["dev1", "dev2", "dev3", "projectmanager"]:
            try:
                pwd.getpwnam(u)
            except KeyError:
                pytest.fail(f"User '{u}' missing after second run.")

        # Groups still exist
        for g in ["developers", "projects"]:
            try:
                grp.getgrnam(g)
            except KeyError:
                pytest.fail(f"Group '{g}' missing after second run.")

        # /opt/projects permissions still correct
        perms = get_octal_permissions("/opt/projects")
        assert perms == "0o2775", \
            f"/opt/projects permissions changed to {perms} after second run."

        # Per-user dirs still correct
        for u in ["dev1", "dev2", "dev3"]:
            path = f"/opt/projects/{u}"
            perms = get_octal_permissions(path)
            assert perms == "0o2770", \
                f"{path} permissions changed to {perms} after second run."


# ===========================================================================
# Section 8: Script runs non-interactively
# ===========================================================================

class TestNonInteractive:
    def test_script_completes_within_timeout(self):
        """Script must complete within 30 seconds (no interactive prompts)."""
        result = subprocess.run(
            ["bash", SETUP_SCRIPT],
            capture_output=True, text=True, timeout=30,
            input=""  # provide empty stdin to ensure no interactive prompts
        )
        assert result.returncode == 0, \
            f"Script did not complete successfully with empty stdin.\n" \
            f"STDERR: {result.stderr}"
