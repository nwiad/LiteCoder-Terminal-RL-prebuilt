"""
Tests for Container Image Backup and Transfer System.

Validates that the agent correctly set up:
- Backup script (/app/backup.sh)
- Retention script (/app/retention.sh)
- Backup log (/app/backup_log.json) in JSONL format
- Retention report (/app/retention_report.json)
- Documentation (/app/backup_procedures.txt)
- Cron job for hourly backup
- Docker registry container (backup-registry)
- Backup test (testapp:1.0.0 in registry)
"""

import os
import json
import stat
import subprocess
import re

# ============================================================
# Helper utilities
# ============================================================

def file_exists(path):
    return os.path.isfile(path)

def read_file(path):
    with open(path, "r") as f:
        return f.read()

def is_executable(path):
    """Check if file has any execute permission bit set."""
    st = os.stat(path)
    return bool(st.st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH))

def run_cmd(cmd, timeout=30):
    """Run a shell command and return (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "timeout"
    except Exception as e:
        return -1, "", str(e)

# ============================================================
# 1. Backup Script Tests
# ============================================================

class TestBackupScript:
    """Tests for /app/backup.sh existence, permissions, and structure."""

    def test_backup_script_exists(self):
        assert file_exists("/app/backup.sh"), "/app/backup.sh does not exist"

    def test_backup_script_is_executable(self):
        assert is_executable("/app/backup.sh"), "/app/backup.sh is not executable"

    def test_backup_script_has_shebang(self):
        content = read_file("/app/backup.sh")
        first_line = content.strip().split("\n")[0]
        assert first_line.startswith("#!"), "/app/backup.sh missing shebang line"
        assert "bash" in first_line or "sh" in first_line, \
            "/app/backup.sh shebang does not reference bash/sh"

    def test_backup_script_references_registry(self):
        """Script must interact with localhost:5000 registry."""
        content = read_file("/app/backup.sh")
        assert "localhost:5000" in content, \
            "/app/backup.sh does not reference localhost:5000 registry"

    def test_backup_script_references_docker_tag(self):
        """Script must use docker tag command."""
        content = read_file("/app/backup.sh")
        assert "docker tag" in content or "docker push" in content, \
            "/app/backup.sh does not contain docker tag/push commands"

    def test_backup_script_writes_to_log(self):
        """Script must append to backup_log.json."""
        content = read_file("/app/backup.sh")
        assert "backup_log.json" in content, \
            "/app/backup.sh does not reference backup_log.json"

    def test_backup_script_handles_success_and_failure_status(self):
        """Script must handle both success and failed statuses."""
        content = read_file("/app/backup.sh")
        assert "success" in content, "/app/backup.sh missing 'success' status handling"
        assert "failed" in content or "fail" in content, \
            "/app/backup.sh missing failure status handling"


# ============================================================
# 2. Retention Script Tests
# ============================================================

class TestRetentionScript:
    """Tests for /app/retention.sh existence, permissions, and structure."""

    def test_retention_script_exists(self):
        assert file_exists("/app/retention.sh"), "/app/retention.sh does not exist"

    def test_retention_script_is_executable(self):
        assert is_executable("/app/retention.sh"), "/app/retention.sh is not executable"

    def test_retention_script_has_shebang(self):
        content = read_file("/app/retention.sh")
        first_line = content.strip().split("\n")[0]
        assert first_line.startswith("#!"), "/app/retention.sh missing shebang line"
        assert "bash" in first_line or "sh" in first_line, \
            "/app/retention.sh shebang does not reference bash/sh"

    def test_retention_script_references_registry(self):
        content = read_file("/app/retention.sh")
        assert "localhost:5000" in content, \
            "/app/retention.sh does not reference localhost:5000 registry"

    def test_retention_script_writes_report(self):
        content = read_file("/app/retention.sh")
        assert "retention_report.json" in content, \
            "/app/retention.sh does not reference retention_report.json"

    def test_retention_script_implements_keep_5_policy(self):
        """The script must implement a policy to keep only 5 versions."""
        content = read_file("/app/retention.sh")
        assert "5" in content, \
            "/app/retention.sh does not reference the number 5 for retention policy"


# ============================================================
# 3. Backup Log Tests
# ============================================================

class TestBackupLog:
    """Tests for /app/backup_log.json (JSONL format)."""

    def test_backup_log_exists(self):
        assert file_exists("/app/backup_log.json"), \
            "/app/backup_log.json does not exist"

    def test_backup_log_not_empty(self):
        content = read_file("/app/backup_log.json").strip()
        assert len(content) > 0, "/app/backup_log.json is empty"

    def test_backup_log_valid_jsonl(self):
        """Each line must be valid JSON."""
        content = read_file("/app/backup_log.json").strip()
        lines = [l for l in content.split("\n") if l.strip()]
        assert len(lines) >= 1, "backup_log.json has no JSONL entries"
        for i, line in enumerate(lines):
            try:
                json.loads(line)
            except json.JSONDecodeError:
                assert False, f"Line {i+1} in backup_log.json is not valid JSON: {line[:100]}"

    def test_backup_log_required_fields(self):
        """Each entry must have image, version, timestamp, status."""
        content = read_file("/app/backup_log.json").strip()
        lines = [l for l in content.split("\n") if l.strip()]
        required_fields = {"image", "version", "timestamp", "status"}
        for i, line in enumerate(lines):
            entry = json.loads(line)
            missing = required_fields - set(entry.keys())
            assert not missing, \
                f"Line {i+1} missing fields: {missing}"

    def test_backup_log_has_testapp_entry(self):
        """Must contain an entry for testapp version 1.0.0."""
        content = read_file("/app/backup_log.json").strip()
        lines = [l for l in content.split("\n") if l.strip()]
        found = False
        for line in lines:
            entry = json.loads(line)
            if entry.get("image") == "testapp" and entry.get("version") == "1.0.0":
                found = True
                break
        assert found, "backup_log.json missing entry for testapp:1.0.0"

    def test_backup_log_testapp_success(self):
        """The testapp:1.0.0 backup must have status 'success'."""
        content = read_file("/app/backup_log.json").strip()
        lines = [l for l in content.split("\n") if l.strip()]
        for line in lines:
            entry = json.loads(line)
            if entry.get("image") == "testapp" and entry.get("version") == "1.0.0":
                assert entry.get("status") == "success", \
                    f"testapp:1.0.0 backup status is '{entry.get('status')}', expected 'success'"
                return
        assert False, "No testapp:1.0.0 entry found to check status"

    def test_backup_log_timestamp_format(self):
        """Timestamps should be ISO-8601 UTC format."""
        content = read_file("/app/backup_log.json").strip()
        lines = [l for l in content.split("\n") if l.strip()]
        iso_pattern = re.compile(
            r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"
        )
        for i, line in enumerate(lines):
            entry = json.loads(line)
            ts = entry.get("timestamp", "")
            assert iso_pattern.match(ts), \
                f"Line {i+1} timestamp '{ts}' is not ISO-8601 format"


# ============================================================
# 4. Documentation Tests
# ============================================================

class TestDocumentation:
    """Tests for /app/backup_procedures.txt."""

    def test_documentation_exists(self):
        assert file_exists("/app/backup_procedures.txt"), \
            "/app/backup_procedures.txt does not exist"

    def test_documentation_not_empty(self):
        content = read_file("/app/backup_procedures.txt").strip()
        assert len(content) > 50, \
            "/app/backup_procedures.txt is too short to contain meaningful documentation"

    def test_documentation_has_backup_procedure_section(self):
        content = read_file("/app/backup_procedures.txt")
        assert "BACKUP PROCEDURE" in content, \
            "Missing 'BACKUP PROCEDURE' section header"

    def test_documentation_has_restore_procedure_section(self):
        content = read_file("/app/backup_procedures.txt")
        assert "RESTORE PROCEDURE" in content, \
            "Missing 'RESTORE PROCEDURE' section header"

    def test_documentation_has_retention_policy_section(self):
        content = read_file("/app/backup_procedures.txt")
        assert "RETENTION POLICY" in content, \
            "Missing 'RETENTION POLICY' section header"

    def test_documentation_has_scheduled_backup_section(self):
        content = read_file("/app/backup_procedures.txt")
        assert "SCHEDULED BACKUP" in content, \
            "Missing 'SCHEDULED BACKUP' section header"

    def test_documentation_sections_have_content(self):
        """Each section header must have at least one line of descriptive text below it."""
        content = read_file("/app/backup_procedures.txt")
        headers = [
            "BACKUP PROCEDURE",
            "RESTORE PROCEDURE",
            "RETENTION POLICY",
            "SCHEDULED BACKUP",
        ]
        lines = content.split("\n")
        for header in headers:
            # Find the line index of this header
            header_idx = None
            for i, line in enumerate(lines):
                if header in line:
                    header_idx = i
                    break
            assert header_idx is not None, f"Header '{header}' not found"
            # Check that there is at least one non-empty line after the header
            # before the next header or end of file
            found_content = False
            for j in range(header_idx + 1, len(lines)):
                stripped = lines[j].strip()
                # Stop if we hit another section header
                if any(h in lines[j] for h in headers if h != header):
                    break
                if stripped:
                    found_content = True
                    break
            assert found_content, \
                f"Section '{header}' has no descriptive content below it"


# ============================================================
# 5. Cron Job Tests
# ============================================================

class TestCronJob:
    """Tests for scheduled hourly backup via cron."""

    def test_cron_job_exists(self):
        """crontab -l must return an entry referencing /app/backup.sh."""
        rc, stdout, stderr = run_cmd("crontab -l 2>/dev/null")
        assert "/app/backup.sh" in stdout, \
            "No cron entry found referencing /app/backup.sh"

    def test_cron_job_runs_hourly(self):
        """Cron entry must run at minute 0 every hour: '0 * * * *'."""
        rc, stdout, _ = run_cmd("crontab -l 2>/dev/null")
        lines = [l.strip() for l in stdout.split("\n")
                 if "/app/backup.sh" in l and not l.strip().startswith("#")]
        assert len(lines) >= 1, "No active cron entry for /app/backup.sh"
        # Check that at least one matching line starts with the hourly pattern
        hourly_pattern = re.compile(r"^0\s+\*\s+\*\s+\*\s+\*\s+")
        matched = any(hourly_pattern.match(l) for l in lines)
        assert matched, \
            f"Cron entry does not match hourly pattern '0 * * * *'. Found: {lines}"


# ============================================================
# 6. Docker Registry Container Tests
# ============================================================

class TestDockerRegistry:
    """Tests for the backup-registry container."""

    def test_backup_registry_container_exists(self):
        """A container named 'backup-registry' must exist."""
        rc, stdout, _ = run_cmd("docker ps -a --format '{{.Names}}' 2>/dev/null")
        if rc != 0:
            # Docker may not be running in test env; check via docker inspect
            rc2, _, _ = run_cmd("docker inspect backup-registry 2>/dev/null")
            assert rc2 == 0, "Container 'backup-registry' does not exist"
        else:
            names = [n.strip() for n in stdout.strip().split("\n") if n.strip()]
            assert "backup-registry" in names, \
                f"Container 'backup-registry' not found. Containers: {names}"

    def test_backup_registry_uses_registry2_image(self):
        """The backup-registry container must use the registry:2 image."""
        rc, stdout, _ = run_cmd(
            "docker inspect --format '{{.Config.Image}}' backup-registry 2>/dev/null"
        )
        if rc == 0:
            image = stdout.strip()
            assert "registry" in image, \
                f"backup-registry uses image '{image}', expected registry:2"

    def test_backup_registry_port_5000(self):
        """The registry must be mapped to host port 5000."""
        rc, stdout, _ = run_cmd(
            "docker inspect --format '{{json .HostConfig.PortBindings}}' backup-registry 2>/dev/null"
        )
        if rc == 0:
            assert "5000" in stdout, \
                f"Port 5000 not found in port bindings: {stdout}"

    def test_backup_registry_restart_always(self):
        """The registry container must have restart policy 'always'."""
        rc, stdout, _ = run_cmd(
            "docker inspect --format '{{.HostConfig.RestartPolicy.Name}}' backup-registry 2>/dev/null"
        )
        if rc == 0:
            policy = stdout.strip()
            assert policy == "always", \
                f"Restart policy is '{policy}', expected 'always'"


# ============================================================
# 7. Backup & Restore Test Verification
# ============================================================

class TestBackupRestore:
    """Verify that testapp:1.0.0 was backed up to the registry."""

    def test_registry_has_testapp(self):
        """Query registry API for testapp tags; 1.0.0 must be present."""
        rc, stdout, _ = run_cmd(
            "curl -s http://localhost:5000/v2/testapp/tags/list 2>/dev/null"
        )
        if rc != 0 or not stdout.strip():
            # Registry might not be reachable; skip gracefully but warn
            assert False, \
                "Cannot reach registry at localhost:5000 to verify testapp"
        try:
            data = json.loads(stdout)
        except json.JSONDecodeError:
            assert False, f"Registry response is not valid JSON: {stdout[:200]}"
        tags = data.get("tags", [])
        assert tags is not None, "Registry returned null tags for testapp"
        assert "1.0.0" in tags, \
            f"Tag '1.0.0' not found in registry for testapp. Tags: {tags}"

    def test_registry_testapp_name(self):
        """Registry response must report the correct image name."""
        rc, stdout, _ = run_cmd(
            "curl -s http://localhost:5000/v2/testapp/tags/list 2>/dev/null"
        )
        if rc == 0 and stdout.strip():
            try:
                data = json.loads(stdout)
                name = data.get("name", "")
                assert name == "testapp", \
                    f"Registry reports image name '{name}', expected 'testapp'"
            except json.JSONDecodeError:
                pass  # Already covered by test above


# ============================================================
# 8. Retention Report Structure Tests (if report exists)
# ============================================================

class TestRetentionReport:
    """
    Tests for /app/retention_report.json structure.
    The report may or may not exist depending on whether retention.sh was run.
    If it exists, validate its structure.
    """

    def test_retention_report_valid_json_if_exists(self):
        """If retention_report.json exists, it must be valid JSON."""
        if not file_exists("/app/retention_report.json"):
            return  # Not required to exist unless retention.sh was run
        content = read_file("/app/retention_report.json").strip()
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            assert False, "retention_report.json is not valid JSON"
        assert isinstance(data, dict), "retention_report.json root must be a JSON object"

    def test_retention_report_required_keys_if_exists(self):
        """If report exists, it must have the required keys."""
        if not file_exists("/app/retention_report.json"):
            return
        content = read_file("/app/retention_report.json").strip()
        data = json.loads(content)
        required_keys = {"image", "kept_versions", "deleted_versions",
                         "total_kept", "total_deleted"}
        missing = required_keys - set(data.keys())
        assert not missing, f"retention_report.json missing keys: {missing}"

    def test_retention_report_types_if_exists(self):
        """Validate field types in the retention report."""
        if not file_exists("/app/retention_report.json"):
            return
        content = read_file("/app/retention_report.json").strip()
        data = json.loads(content)
        assert isinstance(data.get("image"), str), "'image' must be a string"
        assert isinstance(data.get("kept_versions"), list), \
            "'kept_versions' must be a list"
        assert isinstance(data.get("deleted_versions"), list), \
            "'deleted_versions' must be a list"
        assert isinstance(data.get("total_kept"), int), \
            "'total_kept' must be an integer"
        assert isinstance(data.get("total_deleted"), int), \
            "'total_deleted' must be an integer"

    def test_retention_report_counts_match_if_exists(self):
        """total_kept and total_deleted must match array lengths."""
        if not file_exists("/app/retention_report.json"):
            return
        content = read_file("/app/retention_report.json").strip()
        data = json.loads(content)
        kept = data.get("kept_versions", [])
        deleted = data.get("deleted_versions", [])
        assert data.get("total_kept") == len(kept), \
            f"total_kept ({data.get('total_kept')}) != len(kept_versions) ({len(kept)})"
        assert data.get("total_deleted") == len(deleted), \
            f"total_deleted ({data.get('total_deleted')}) != len(deleted_versions) ({len(deleted)})"

    def test_retention_report_max_kept_5_if_exists(self):
        """kept_versions should have at most 5 entries."""
        if not file_exists("/app/retention_report.json"):
            return
        content = read_file("/app/retention_report.json").strip()
        data = json.loads(content)
        kept = data.get("kept_versions", [])
        assert len(kept) <= 5, \
            f"kept_versions has {len(kept)} entries, max allowed is 5"

