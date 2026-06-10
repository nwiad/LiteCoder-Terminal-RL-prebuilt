"""
Tests for the Docker Service Failures After Reboot task.

Verifies that the agent has:
1. Fixed the Docker daemon so it is running
2. Fixed /etc/docker/daemon.json to be valid JSON (or removed it)
3. Enabled Docker to start on boot
4. Restored all 3 production containers (prod-nginx, prod-app, prod-db)
5. Set restart policies on all containers
6. Written a proper incident report to /app/incident_report.txt
"""

import json
import os
import subprocess


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run_cmd(cmd, timeout=30):
    """Run a shell command and return (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "", "timeout"
    except Exception as e:
        return -1, "", str(e)


def docker_available():
    """Check if the docker CLI can talk to a running daemon."""
    rc, _, _ = run_cmd("docker info")
    return rc == 0


# ===========================================================================
# Test 1: Docker daemon is running and responsive
# ===========================================================================

class TestDockerDaemon:
    """Verify the Docker daemon is up and functional."""

    def test_docker_info_succeeds(self):
        """docker info should return exit code 0."""
        rc, stdout, stderr = run_cmd("docker info")
        assert rc == 0, (
            f"docker info failed (rc={rc}). "
            f"stderr: {stderr}"
        )

    def test_docker_ps_succeeds(self):
        """docker ps should return exit code 0."""
        rc, stdout, stderr = run_cmd("docker ps")
        assert rc == 0, (
            f"docker ps failed (rc={rc}). "
            f"stderr: {stderr}"
        )


# ===========================================================================
# Test 2: /etc/docker/daemon.json is valid (or absent)
# ===========================================================================

class TestDaemonJson:
    """The corrupted daemon.json must be fixed or removed."""

    def test_daemon_json_valid_or_absent(self):
        """If daemon.json exists it must be parseable JSON."""
        path = "/etc/docker/daemon.json"
        if not os.path.exists(path):
            # Removing the file entirely is a valid fix
            return
        with open(path, "r") as f:
            content = f.read().strip()
        if not content:
            # Empty file is acceptable (Docker uses defaults)
            return
        try:
            data = json.loads(content)
            assert isinstance(data, dict), "daemon.json root must be a JSON object"
        except json.JSONDecodeError as e:
            raise AssertionError(
                f"/etc/docker/daemon.json contains invalid JSON: {e}\n"
                f"Content:\n{content}"
            )


# ===========================================================================
# Test 3: Docker enabled on boot
# ===========================================================================

class TestDockerEnabled:
    """Docker should be configured to start on boot."""

    def test_docker_enabled_on_boot(self):
        """
        systemctl is-enabled docker should return 'enabled',
        OR the symlink in multi-user.target.wants should exist.
        Both are valid ways to enable Docker on boot.
        """
        # Method 1: systemctl is-enabled
        rc, stdout, _ = run_cmd("systemctl is-enabled docker 2>/dev/null")
        if rc == 0 and "enabled" in stdout.lower():
            return  # Pass

        # Method 2: Check for the systemd symlink directly
        symlink_path = "/etc/systemd/system/multi-user.target.wants/docker.service"
        if os.path.exists(symlink_path) or os.path.islink(symlink_path):
            return  # Pass

        # Method 3: Check if docker.service has a WantedBy alias installed
        rc2, stdout2, _ = run_cmd(
            "ls -la /etc/systemd/system/multi-user.target.wants/ 2>/dev/null"
        )
        if "docker" in stdout2.lower():
            return  # Pass

        raise AssertionError(
            f"Docker is not enabled on boot. "
            f"systemctl is-enabled returned: '{stdout}' (rc={rc}). "
            f"Symlink {symlink_path} does not exist. "
        )


# ===========================================================================
# Test 4: All three production containers are running
# ===========================================================================

REQUIRED_CONTAINERS = {"prod-nginx", "prod-app", "prod-db"}


class TestContainersRunning:
    """All three production containers must be in running state."""

    def test_all_containers_exist(self):
        """All three containers should appear in docker ps -a."""
        if not docker_available():
            raise AssertionError("Docker daemon is not running, cannot check containers")

        rc, stdout, stderr = run_cmd("docker ps -a --format '{{.Names}}'")
        assert rc == 0, f"docker ps -a failed: {stderr}"
        existing = set(stdout.splitlines())
        missing = REQUIRED_CONTAINERS - existing
        assert not missing, (
            f"Missing containers: {missing}. "
            f"Existing containers: {existing}"
        )

    def test_all_containers_running(self):
        """All three containers must be in 'running' state."""
        if not docker_available():
            raise AssertionError("Docker daemon is not running, cannot check containers")

        for name in REQUIRED_CONTAINERS:
            rc, stdout, stderr = run_cmd(
                f"docker inspect --format '{{{{.State.Running}}}}' {name}"
            )
            assert rc == 0, (
                f"docker inspect failed for {name}: {stderr}"
            )
            assert stdout.lower() == "true", (
                f"Container {name} is not running. "
                f"State.Running = {stdout}"
            )

    def test_containers_listed_in_docker_ps(self):
        """docker ps (without -a) should list all three containers."""
        if not docker_available():
            raise AssertionError("Docker daemon is not running")

        rc, stdout, stderr = run_cmd("docker ps --format '{{.Names}}'")
        assert rc == 0, f"docker ps failed: {stderr}"
        running = set(stdout.splitlines())
        missing = REQUIRED_CONTAINERS - running
        assert not missing, (
            f"Containers not shown in 'docker ps': {missing}. "
            f"Running containers: {running}"
        )


# ===========================================================================
# Test 5: Restart policies
# ===========================================================================

VALID_RESTART_POLICIES = {"unless-stopped", "always"}


class TestRestartPolicies:
    """Each container must have a restart policy that survives reboots."""

    def test_restart_policy_set(self):
        """Each container should have restart policy 'unless-stopped' or 'always'."""
        if not docker_available():
            raise AssertionError("Docker daemon is not running")

        for name in REQUIRED_CONTAINERS:
            rc, stdout, stderr = run_cmd(
                f"docker inspect --format '{{{{.HostConfig.RestartPolicy.Name}}}}' {name}"
            )
            assert rc == 0, (
                f"docker inspect failed for {name}: {stderr}"
            )
            policy = stdout.strip().lower()
            assert policy in VALID_RESTART_POLICIES, (
                f"Container {name} has restart policy '{policy}', "
                f"expected one of {VALID_RESTART_POLICIES}"
            )


# ===========================================================================
# Test 6: Incident report
# ===========================================================================

REPORT_PATH = "/app/incident_report.txt"
REQUIRED_SECTIONS = ["Root Cause:", "Fix Applied:", "Prevention:"]


class TestIncidentReport:
    """The incident report must exist and contain required sections."""

    def test_report_file_exists(self):
        """incident_report.txt must exist at /app/."""
        assert os.path.isfile(REPORT_PATH), (
            f"Incident report not found at {REPORT_PATH}"
        )

    def test_report_not_empty(self):
        """The report must not be empty."""
        if not os.path.isfile(REPORT_PATH):
            raise AssertionError(f"Report file missing: {REPORT_PATH}")
        size = os.path.getsize(REPORT_PATH)
        assert size > 50, (
            f"Incident report is suspiciously small ({size} bytes). "
            f"Expected a meaningful report."
        )

    def test_report_has_required_sections(self):
        """Report must contain Root Cause:, Fix Applied:, Prevention: headers."""
        if not os.path.isfile(REPORT_PATH):
            raise AssertionError(f"Report file missing: {REPORT_PATH}")
        with open(REPORT_PATH, "r") as f:
            content = f.read()
        for section in REQUIRED_SECTIONS:
            assert section in content, (
                f"Incident report missing required section '{section}'. "
                f"Report content:\n{content[:500]}"
            )

    def test_report_sections_have_content(self):
        """Each required section must have meaningful content after the label."""
        if not os.path.isfile(REPORT_PATH):
            raise AssertionError(f"Report file missing: {REPORT_PATH}")
        with open(REPORT_PATH, "r") as f:
            content = f.read()

        for section in REQUIRED_SECTIONS:
            if section not in content:
                raise AssertionError(f"Missing section: {section}")
            # Find the text after the section header
            idx = content.index(section)
            after = content[idx + len(section):]
            # Get text until the next section header or end of file
            end_idx = len(after)
            for other_section in REQUIRED_SECTIONS:
                if other_section != section and other_section in after:
                    pos = after.index(other_section)
                    if pos < end_idx:
                        end_idx = pos
            section_text = after[:end_idx].strip()
            assert len(section_text) >= 10, (
                f"Section '{section}' has insufficient content "
                f"(only {len(section_text)} chars): '{section_text[:100]}'. "
                f"Expected a meaningful description."
            )

    def test_report_mentions_relevant_concepts(self):
        """
        The report should reference Docker-related concepts,
        not be generic filler text.
        """
        if not os.path.isfile(REPORT_PATH):
            raise AssertionError(f"Report file missing: {REPORT_PATH}")
        with open(REPORT_PATH, "r") as f:
            content = f.read().lower()

        # The report should mention docker-related terms
        docker_terms = ["docker", "daemon", "container", "service"]
        found = [t for t in docker_terms if t in content]
        assert len(found) >= 2, (
            f"Incident report doesn't appear to be about Docker. "
            f"Expected at least 2 of {docker_terms} but found only: {found}"
        )

        # The root cause section should reference the actual issues
        # (corrupted config or masked service — at least one)
        root_cause_terms = [
            "json", "daemon.json", "config", "corrupt", "invalid",
            "mask", "masked", "systemd", "systemctl", "comma", "syntax",
            "parse", "configuration"
        ]
        found_rc = [t for t in root_cause_terms if t in content]
        assert len(found_rc) >= 1, (
            f"Incident report Root Cause doesn't reference the actual issue. "
            f"Expected mention of config/JSON corruption or masked service. "
            f"Found none of: {root_cause_terms}"
        )
