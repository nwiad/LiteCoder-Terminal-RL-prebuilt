"""
Tests for Bidirectional File Sync Recovery task.

Validates all 5 deliverables:
1. Sync directories exist with correct permissions
2. Sync script at correct path, executable, correct content
3. systemd service unit with required fields
4. logrotate config with required directives
5. Summary document with required sections
"""

import os
import re
import stat
import subprocess


# ============================================================================
# 1. Sync Directories
# ============================================================================

class TestSyncDirectories:
    """Verify /srv/project_a and /srv/project_b exist with correct permissions."""

    def test_project_a_exists(self):
        assert os.path.isdir("/srv/project_a"), "/srv/project_a directory must exist"

    def test_project_b_exists(self):
        assert os.path.isdir("/srv/project_b"), "/srv/project_b directory must exist"

    def test_project_a_permissions(self):
        mode = os.stat("/srv/project_a").st_mode
        perms = stat.S_IMODE(mode)
        assert perms == 0o755, (
            f"/srv/project_a permissions should be 755, got {oct(perms)}"
        )

    def test_project_b_permissions(self):
        mode = os.stat("/srv/project_b").st_mode
        perms = stat.S_IMODE(mode)
        assert perms == 0o755, (
            f"/srv/project_b permissions should be 755, got {oct(perms)}"
        )


# ============================================================================
# 2. Sync Script
# ============================================================================

class TestSyncScript:
    """Verify /usr/local/bin/bidirectional_sync.sh exists and has correct properties."""

    SCRIPT_PATH = "/usr/local/bin/bidirectional_sync.sh"

    def test_script_exists(self):
        assert os.path.isfile(self.SCRIPT_PATH), (
            f"Sync script must exist at {self.SCRIPT_PATH}"
        )

    def test_script_is_executable(self):
        assert os.path.isfile(self.SCRIPT_PATH), "Script must exist first"
        mode = os.stat(self.SCRIPT_PATH).st_mode
        assert mode & stat.S_IXUSR, "Script must be executable by owner"

    def test_script_is_not_empty(self):
        assert os.path.isfile(self.SCRIPT_PATH), "Script must exist first"
        size = os.path.getsize(self.SCRIPT_PATH)
        assert size > 100, f"Script should not be trivially small ({size} bytes)"

    def _read_script(self):
        with open(self.SCRIPT_PATH, "r") as f:
            return f.read()

    def test_script_has_shebang(self):
        content = self._read_script()
        assert content.startswith("#!/"), "Script must start with a shebang line"

    def test_script_uses_inotifywait(self):
        content = self._read_script()
        assert "inotifywait" in content, (
            "Script must use inotifywait for filesystem monitoring"
        )

    def test_script_uses_rsync(self):
        content = self._read_script()
        assert "rsync" in content, "Script must use rsync for file synchronization"

    def test_script_references_project_a(self):
        content = self._read_script()
        assert "/srv/project_a" in content, (
            "Script must reference /srv/project_a"
        )

    def test_script_references_project_b(self):
        content = self._read_script()
        assert "/srv/project_b" in content, (
            "Script must reference /srv/project_b"
        )

    def test_script_references_log_file(self):
        content = self._read_script()
        assert "/var/log/file_sync.log" in content, (
            "Script must reference /var/log/file_sync.log"
        )

    def test_script_has_a_to_b_direction(self):
        content = self._read_script()
        assert "A->B" in content, (
            "Script must log A->B direction for project_a to project_b syncs"
        )

    def test_script_has_b_to_a_direction(self):
        content = self._read_script()
        assert "B->A" in content, (
            "Script must log B->A direction for project_b to project_a syncs"
        )

    def test_script_has_error_logging(self):
        content = self._read_script()
        assert "ERROR" in content.upper(), (
            "Script must have error logging capability"
        )

    def test_script_monitors_create_modify_delete_move(self):
        """Script must monitor create, modify, delete, and move events."""
        content = self._read_script().lower()
        for event in ["create", "modify", "delete", "move"]:
            assert event in content, (
                f"Script must monitor '{event}' events via inotifywait"
            )

    def test_script_log_format_has_timestamp_pattern(self):
        """Script must produce logs with [YYYY-MM-DD HH:MM:SS] format."""
        content = self._read_script()
        # Look for date formatting patterns commonly used in bash
        # e.g., date '+%Y-%m-%d %H:%M:%S' or similar
        has_date_format = (
            "%Y" in content and "%M" in content and "%S" in content
        )
        # Also accept if they use a literal timestamp regex or printf
        has_bracket_format = "[" in content and "]" in content
        assert has_date_format or has_bracket_format, (
            "Script must format log timestamps as [YYYY-MM-DD HH:MM:SS]"
        )


# ============================================================================
# 3. systemd Service Unit
# ============================================================================

class TestSystemdService:
    """Verify /etc/systemd/system/file-sync.service has correct configuration."""

    SERVICE_PATH = "/etc/systemd/system/file-sync.service"

    def test_service_file_exists(self):
        assert os.path.isfile(self.SERVICE_PATH), (
            f"systemd service unit must exist at {self.SERVICE_PATH}"
        )

    def test_service_file_not_empty(self):
        assert os.path.isfile(self.SERVICE_PATH), "Service file must exist"
        size = os.path.getsize(self.SERVICE_PATH)
        assert size > 50, f"Service file should not be trivially small ({size} bytes)"

    def _read_service(self):
        with open(self.SERVICE_PATH, "r") as f:
            return f.read()

    def test_service_has_unit_section(self):
        content = self._read_service()
        assert "[Unit]" in content, "Service must have [Unit] section"

    def test_service_has_service_section(self):
        content = self._read_service()
        assert "[Service]" in content, "Service must have [Service] section"

    def test_service_has_install_section(self):
        content = self._read_service()
        assert "[Install]" in content, "Service must have [Install] section"

    def test_service_type_simple(self):
        content = self._read_service()
        # Match Type=simple with flexible whitespace
        assert re.search(r"Type\s*=\s*simple", content), (
            "Service must have Type=simple"
        )

    def test_service_execstart(self):
        content = self._read_service()
        assert re.search(
            r"ExecStart\s*=\s*/usr/local/bin/bidirectional_sync\.sh",
            content,
        ), "Service ExecStart must point to /usr/local/bin/bidirectional_sync.sh"

    def test_service_restart_on_failure(self):
        content = self._read_service()
        assert re.search(r"Restart\s*=\s*on-failure", content), (
            "Service must have Restart=on-failure"
        )

    def test_service_restart_sec_30(self):
        content = self._read_service()
        assert re.search(r"RestartSec\s*=\s*30", content), (
            "Service must have RestartSec=30"
        )

    def test_service_wanted_by_multi_user(self):
        content = self._read_service()
        assert re.search(r"WantedBy\s*=\s*multi-user\.target", content), (
            "Service must have WantedBy=multi-user.target"
        )

    def test_service_is_enabled(self):
        """Check that the service is enabled (symlink or systemctl)."""
        # In Docker, systemd may not be running. Check for the symlink.
        symlink_path = (
            "/etc/systemd/system/multi-user.target.wants/file-sync.service"
        )
        # Try systemctl first
        try:
            result = subprocess.run(
                ["systemctl", "is-enabled", "file-sync.service"],
                capture_output=True, text=True, timeout=5,
            )
            if result.stdout.strip() == "enabled":
                return  # pass
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        # Fallback: check symlink exists
        assert os.path.exists(symlink_path) or os.path.islink(symlink_path), (
            "file-sync.service must be enabled "
            "(symlink in multi-user.target.wants or systemctl is-enabled)"
        )


# ============================================================================
# 4. Logrotate Configuration
# ============================================================================

class TestLogrotateConfig:
    """Verify /etc/logrotate.d/file-sync has correct directives."""

    LOGROTATE_PATH = "/etc/logrotate.d/file-sync"

    def test_logrotate_file_exists(self):
        assert os.path.isfile(self.LOGROTATE_PATH), (
            f"Logrotate config must exist at {self.LOGROTATE_PATH}"
        )

    def test_logrotate_file_not_empty(self):
        assert os.path.isfile(self.LOGROTATE_PATH), "Config must exist"
        size = os.path.getsize(self.LOGROTATE_PATH)
        assert size > 20, (
            f"Logrotate config should not be trivially small ({size} bytes)"
        )

    def _read_config(self):
        with open(self.LOGROTATE_PATH, "r") as f:
            return f.read()

    def test_logrotate_targets_correct_log(self):
        content = self._read_config()
        assert "/var/log/file_sync.log" in content, (
            "Logrotate must target /var/log/file_sync.log"
        )

    def test_logrotate_weekly(self):
        content = self._read_config()
        assert re.search(r"\bweekly\b", content), (
            "Logrotate must have 'weekly' directive"
        )

    def test_logrotate_rotate_1(self):
        content = self._read_config()
        assert re.search(r"\brotate\s+1\b", content), (
            "Logrotate must have 'rotate 1' directive"
        )

    def test_logrotate_missingok(self):
        content = self._read_config()
        assert re.search(r"\bmissingok\b", content), (
            "Logrotate must have 'missingok' directive"
        )

    def test_logrotate_notifempty(self):
        content = self._read_config()
        assert re.search(r"\bnotifempty\b", content), (
            "Logrotate must have 'notifempty' directive"
        )

    def test_logrotate_compress(self):
        content = self._read_config()
        assert re.search(r"\bcompress\b", content), (
            "Logrotate must have 'compress' directive"
        )


# ============================================================================
# 5. Summary Document
# ============================================================================

class TestSummaryDocument:
    """Verify /root/SYNC_SUMMARY.md exists and has required content."""

    SUMMARY_PATH = "/root/SYNC_SUMMARY.md"

    def test_summary_exists(self):
        assert os.path.isfile(self.SUMMARY_PATH), (
            f"Summary document must exist at {self.SUMMARY_PATH}"
        )

    def test_summary_not_empty(self):
        assert os.path.isfile(self.SUMMARY_PATH), "Summary must exist"
        size = os.path.getsize(self.SUMMARY_PATH)
        assert size > 100, (
            f"Summary should not be trivially small ({size} bytes)"
        )

    def _read_summary(self):
        with open(self.SUMMARY_PATH, "r") as f:
            return f.read()

    def test_summary_mentions_project_a(self):
        content = self._read_summary()
        assert "/srv/project_a" in content, (
            "Summary must mention /srv/project_a"
        )

    def test_summary_mentions_project_b(self):
        content = self._read_summary()
        assert "/srv/project_b" in content, (
            "Summary must mention /srv/project_b"
        )

    def test_summary_mentions_sync_script_path(self):
        content = self._read_summary()
        assert "/usr/local/bin/bidirectional_sync.sh" in content, (
            "Summary must mention the sync script path"
        )

    def test_summary_mentions_service_unit_path(self):
        content = self._read_summary()
        assert "/etc/systemd/system/file-sync.service" in content, (
            "Summary must mention the service unit path"
        )

    def test_summary_mentions_logrotate_path(self):
        content = self._read_summary()
        assert "/etc/logrotate.d/file-sync" in content, (
            "Summary must mention the logrotate config path"
        )

    def test_summary_mentions_log_file_path(self):
        content = self._read_summary()
        assert "/var/log/file_sync.log" in content, (
            "Summary must mention the log file path"
        )

    def test_summary_has_runbook_start(self):
        """Summary must explain how to start the service."""
        content = self._read_summary().lower()
        assert "start" in content, (
            "Summary runbook must explain how to start the service"
        )

    def test_summary_has_runbook_stop(self):
        """Summary must explain how to stop the service."""
        content = self._read_summary().lower()
        assert "stop" in content, (
            "Summary runbook must explain how to stop the service"
        )

    def test_summary_has_runbook_status(self):
        """Summary must explain how to check service status."""
        content = self._read_summary().lower()
        assert "status" in content, (
            "Summary runbook must explain how to check service status"
        )

    def test_summary_references_systemctl(self):
        """Runbook should reference systemctl commands."""
        content = self._read_summary()
        assert "systemctl" in content, (
            "Summary runbook should reference systemctl for service management"
        )


# ============================================================================
# 6. Log File
# ============================================================================

class TestLogFile:
    """Verify /var/log/file_sync.log exists."""

    LOG_PATH = "/var/log/file_sync.log"

    def test_log_file_exists(self):
        assert os.path.isfile(self.LOG_PATH), (
            f"Log file must exist at {self.LOG_PATH}"
        )


# ============================================================================
# 7. Cross-cutting: Consistency checks
# ============================================================================

class TestCrossCuttingConsistency:
    """Verify that all deliverables are consistent with each other."""

    def test_service_points_to_existing_script(self):
        """The ExecStart path in the service must point to an existing file."""
        service_path = "/etc/systemd/system/file-sync.service"
        script_path = "/usr/local/bin/bidirectional_sync.sh"
        if not os.path.isfile(service_path):
            return  # covered by other tests
        with open(service_path, "r") as f:
            content = f.read()
        match = re.search(r"ExecStart\s*=\s*(\S+)", content)
        if match:
            exec_path = match.group(1)
            assert os.path.isfile(exec_path), (
                f"ExecStart path '{exec_path}' must point to an existing file"
            )
        assert os.path.isfile(script_path), (
            "Sync script must exist at /usr/local/bin/bidirectional_sync.sh"
        )

    def test_logrotate_targets_existing_log_path(self):
        """The logrotate config must target the same log the script writes to."""
        logrotate_path = "/etc/logrotate.d/file-sync"
        if not os.path.isfile(logrotate_path):
            return  # covered by other tests
        with open(logrotate_path, "r") as f:
            content = f.read()
        assert "/var/log/file_sync.log" in content, (
            "Logrotate config must target /var/log/file_sync.log"
        )

    def test_script_log_path_matches_logrotate(self):
        """The script's log path must match what logrotate manages."""
        script_path = "/usr/local/bin/bidirectional_sync.sh"
        if not os.path.isfile(script_path):
            return
        with open(script_path, "r") as f:
            script_content = f.read()
        assert "/var/log/file_sync.log" in script_content, (
            "Script must write to /var/log/file_sync.log"
        )

