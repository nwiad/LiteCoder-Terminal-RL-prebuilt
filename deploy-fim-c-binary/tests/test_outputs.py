"""
Tests for the FIM (File Integrity Monitoring) deployment task.

Verifies:
- Binary and source file existence
- Directory structure
- Baseline database format and content
- FIM binary functionality (init, check with ADDED/MODIFIED/DELETED detection)
- FIM daemon (PID file, live process)
- Change log format and content
- Logrotate configuration
- Cron job setup
- Daily digest mail delivery
"""

import os
import re
import subprocess
import signal
import time
import hashlib


# ──────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────

def file_exists(path):
    return os.path.isfile(path)

def dir_exists(path):
    return os.path.isdir(path)

def read_file(path):
    """Read file content, return empty string if missing."""
    try:
        with open(path, "r", errors="replace") as f:
            return f.read()
    except (FileNotFoundError, PermissionError):
        return ""

def is_executable(path):
    return os.path.isfile(path) and os.access(path, os.X_OK)

def sha256_of_file(path):
    """Compute SHA-256 hex digest of a file."""
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()
    except (FileNotFoundError, PermissionError):
        return None


# ──────────────────────────────────────────────────────────────────────
# 1. Directory structure
# ──────────────────────────────────────────────────────────────────────

class TestDirectoryStructure:
    def test_webroot_exists(self):
        assert dir_exists("/var/www/html"), "/var/www/html must exist"

    def test_log_dir_exists(self):
        assert dir_exists("/var/log/fim"), "/var/log/fim must exist"

    def test_baseline_dir_exists(self):
        assert dir_exists("/root/.fim"), "/root/.fim must exist"


# ──────────────────────────────────────────────────────────────────────
# 2. FIM binary and source
# ──────────────────────────────────────────────────────────────────────

class TestFIMBinary:
    def test_source_exists(self):
        assert file_exists("/root/fim.c"), "/root/fim.c must exist"

    def test_source_is_c_code(self):
        content = read_file("/root/fim.c")
        assert len(content) > 100, "fim.c must contain substantial C code"
        assert "#include" in content, "fim.c must contain #include directives"
        assert "main" in content, "fim.c must contain a main function"

    def test_binary_exists(self):
        assert file_exists("/usr/local/bin/fim"), "/usr/local/bin/fim must exist"

    def test_binary_is_executable(self):
        assert is_executable("/usr/local/bin/fim"), "/usr/local/bin/fim must be executable"

    def test_binary_is_elf(self):
        """Verify it's a compiled binary, not a script."""
        try:
            with open("/usr/local/bin/fim", "rb") as f:
                magic = f.read(4)
            assert magic == b"\x7fELF", "fim must be a compiled ELF binary"
        except FileNotFoundError:
            assert False, "/usr/local/bin/fim not found"

    def test_binary_usage(self):
        """Binary should print usage or error when called without args."""
        result = subprocess.run(
            ["/usr/local/bin/fim"],
            capture_output=True, text=True, timeout=5
        )
        # Should exit non-zero without arguments
        assert result.returncode != 0, "fim with no args should exit non-zero"


# ──────────────────────────────────────────────────────────────────────
# 3. Baseline database
# ──────────────────────────────────────────────────────────────────────

BASELINE_PATH = "/root/.fim/baseline.db"

# The 5 files pre-loaded in the Dockerfile
EXPECTED_WEBROOT_FILES = {
    "/var/www/html/index.html",
    "/var/www/html/about.html",
    "/var/www/html/style.css",
    "/var/www/html/robots.txt",
    "/var/www/html/contact.html",
}

# Regex: 64 hex chars, two spaces, then an absolute path
BASELINE_LINE_RE = re.compile(r"^[0-9a-f]{64}  /.+$")


class TestBaselineDB:
    def test_baseline_exists(self):
        assert file_exists(BASELINE_PATH), f"{BASELINE_PATH} must exist"

    def test_baseline_not_empty(self):
        content = read_file(BASELINE_PATH).strip()
        assert len(content) > 0, "baseline.db must not be empty"

    def test_baseline_format(self):
        """Every non-empty line must match: <64-hex-sha256>  <absolute-path>"""
        content = read_file(BASELINE_PATH)
        lines = [l for l in content.strip().splitlines() if l.strip()]
        assert len(lines) >= 1, "baseline.db must have at least one entry"
        for line in lines:
            assert BASELINE_LINE_RE.match(line), (
                f"Baseline line does not match expected format: {line!r}"
            )

    def test_baseline_contains_webroot_files(self):
        """Baseline must list all original web-root files."""
        content = read_file(BASELINE_PATH)
        lines = [l.strip() for l in content.strip().splitlines() if l.strip()]
        paths_in_baseline = set()
        for line in lines:
            parts = line.split("  ", 1)
            if len(parts) == 2:
                paths_in_baseline.add(parts[1])
        for expected in EXPECTED_WEBROOT_FILES:
            assert expected in paths_in_baseline, (
                f"{expected} must be listed in baseline.db"
            )

    def test_baseline_hashes_are_valid(self):
        """Spot-check: at least one hash in baseline matches actual file."""
        content = read_file(BASELINE_PATH)
        lines = [l.strip() for l in content.strip().splitlines() if l.strip()]
        verified = 0
        for line in lines:
            parts = line.split("  ", 1)
            if len(parts) != 2:
                continue
            stored_hash, filepath = parts
            actual_hash = sha256_of_file(filepath)
            if actual_hash is not None and stored_hash == actual_hash:
                verified += 1
        # At least one file's hash should match (files may have been
        # modified during the verification step, so we don't require all)
        assert verified >= 1, "At least one baseline hash must match the actual file"


# ──────────────────────────────────────────────────────────────────────
# 4. FIM daemon
# ──────────────────────────────────────────────────────────────────────

PIDFILE = "/var/run/fim.pid"


class TestFIMDaemon:
    def test_pidfile_exists(self):
        assert file_exists(PIDFILE), f"{PIDFILE} must exist"

    def test_pidfile_contains_numeric_pid(self):
        content = read_file(PIDFILE).strip()
        assert content.isdigit(), f"PID file must contain a numeric PID, got: {content!r}"

    def test_daemon_process_is_alive(self):
        """The PID in the pidfile must correspond to a running process."""
        content = read_file(PIDFILE).strip()
        if not content.isdigit():
            assert False, "PID file does not contain a valid PID"
        pid = int(content)
        try:
            os.kill(pid, 0)  # signal 0 = check existence
        except ProcessLookupError:
            assert False, f"FIM daemon (PID {pid}) is not running"
        except PermissionError:
            pass  # process exists but we lack permission (unlikely as root)


# ──────────────────────────────────────────────────────────────────────
# 5. Change log format and content
# ──────────────────────────────────────────────────────────────────────

CHANGELOG = "/var/log/fim/changes.log"

# ISO-8601 datetime (YYYY-MM-DDTHH:MM:SS), then space, EVENT, space, path
CHANGELOG_LINE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\s+(ADDED|MODIFIED|DELETED)\s+/.+"
)


class TestChangeLog:
    def test_changelog_exists(self):
        assert file_exists(CHANGELOG), f"{CHANGELOG} must exist"

    def test_changelog_not_empty(self):
        content = read_file(CHANGELOG).strip()
        assert len(content) > 0, "changes.log must not be empty after verification"

    def test_changelog_line_format(self):
        """Every non-empty line must follow ISO-8601 EVENT filepath format."""
        content = read_file(CHANGELOG)
        lines = [l for l in content.strip().splitlines() if l.strip()]
        assert len(lines) >= 1, "changes.log must have at least one entry"
        for line in lines:
            assert CHANGELOG_LINE_RE.match(line.strip()), (
                f"Change log line does not match expected format: {line!r}"
            )

    def test_changelog_has_added_event(self):
        """Must contain at least one ADDED entry for test.html."""
        content = read_file(CHANGELOG)
        assert re.search(
            r"ADDED\s+/var/www/html/test\.html", content
        ), "changes.log must contain an ADDED event for /var/www/html/test.html"

    def test_changelog_has_modified_event(self):
        """Must contain at least one MODIFIED entry for test.html."""
        content = read_file(CHANGELOG)
        assert re.search(
            r"MODIFIED\s+/var/www/html/test\.html", content
        ), "changes.log must contain a MODIFIED event for /var/www/html/test.html"

    def test_changelog_has_deleted_event(self):
        """Must contain at least one DELETED entry for test.html."""
        content = read_file(CHANGELOG)
        assert re.search(
            r"DELETED\s+/var/www/html/test\.html", content
        ), "changes.log must contain a DELETED event for /var/www/html/test.html"

    def test_changelog_events_in_order(self):
        """ADDED should appear before MODIFIED, which should appear before DELETED."""
        content = read_file(CHANGELOG)
        lines = content.strip().splitlines()
        added_idx = None
        modified_idx = None
        deleted_idx = None
        for i, line in enumerate(lines):
            if re.search(r"ADDED\s+/var/www/html/test\.html", line) and added_idx is None:
                added_idx = i
            if re.search(r"MODIFIED\s+/var/www/html/test\.html", line) and modified_idx is None:
                modified_idx = i
            if re.search(r"DELETED\s+/var/www/html/test\.html", line) and deleted_idx is None:
                deleted_idx = i
        assert added_idx is not None, "ADDED event not found"
        assert modified_idx is not None, "MODIFIED event not found"
        assert deleted_idx is not None, "DELETED event not found"
        assert added_idx < modified_idx < deleted_idx, (
            f"Events must be in order: ADDED({added_idx}) < MODIFIED({modified_idx}) < DELETED({deleted_idx})"
        )


# ──────────────────────────────────────────────────────────────────────
# 6. Logrotate configuration
# ──────────────────────────────────────────────────────────────────────

LOGROTATE_CONF = "/etc/logrotate.d/fim"


class TestLogrotate:
    def test_logrotate_config_exists(self):
        assert file_exists(LOGROTATE_CONF), f"{LOGROTATE_CONF} must exist"

    def test_logrotate_targets_fim_logs(self):
        content = read_file(LOGROTATE_CONF)
        assert "/var/log/fim/" in content or "/var/log/fim" in content, (
            "Logrotate config must target /var/log/fim/ logs"
        )

    def test_logrotate_daily(self):
        content = read_file(LOGROTATE_CONF)
        assert re.search(r"\bdaily\b", content), (
            "Logrotate config must include 'daily' directive"
        )

    def test_logrotate_rotate_7(self):
        content = read_file(LOGROTATE_CONF)
        assert re.search(r"\brotate\s+7\b", content), (
            "Logrotate config must include 'rotate 7'"
        )

    def test_logrotate_compress(self):
        content = read_file(LOGROTATE_CONF)
        assert re.search(r"\bcompress\b", content), (
            "Logrotate config must include 'compress'"
        )

    def test_logrotate_missingok(self):
        content = read_file(LOGROTATE_CONF)
        assert re.search(r"\bmissingok\b", content), (
            "Logrotate config must include 'missingok'"
        )


# ──────────────────────────────────────────────────────────────────────
# 7. Cron job
# ──────────────────────────────────────────────────────────────────────

class TestCronJob:
    def test_cron_entry_exists(self):
        """Root's crontab must contain a daily 06:00 entry for the FIM digest."""
        result = subprocess.run(
            ["crontab", "-l"],
            capture_output=True, text=True, timeout=5
        )
        crontab = result.stdout
        assert len(crontab.strip()) > 0, "Root crontab must not be empty"
        # Look for the 0 6 * * * schedule
        assert re.search(r"0\s+6\s+\*\s+\*\s+\*", crontab), (
            "Crontab must contain a '0 6 * * *' schedule entry"
        )

    def test_cron_references_fim_digest(self):
        """The cron entry must reference the FIM digest script or mail command."""
        result = subprocess.run(
            ["crontab", "-l"],
            capture_output=True, text=True, timeout=5
        )
        crontab = result.stdout.lower()
        assert "fim" in crontab and "digest" in crontab, (
            "Crontab entry must reference a FIM digest script"
        )

    def test_digest_script_exists_and_executable(self):
        """The digest script referenced by cron should exist and be executable."""
        result = subprocess.run(
            ["crontab", "-l"],
            capture_output=True, text=True, timeout=5
        )
        crontab = result.stdout
        # Extract script path from the cron line containing fim-digest
        match = re.search(r"0\s+6\s+\*\s+\*\s+\*\s+(.+)", crontab)
        if match:
            cmd_part = match.group(1).strip()
            # The first token that looks like an absolute path
            path_match = re.search(r"(/\S+)", cmd_part)
            if path_match:
                script_path = path_match.group(1)
                assert is_executable(script_path), (
                    f"Digest script {script_path} must be executable"
                )
                return
        # Fallback: just check the common path
        assert is_executable("/usr/local/bin/fim-digest.sh"), (
            "fim-digest.sh must exist and be executable"
        )


# ──────────────────────────────────────────────────────────────────────
# 8. Mail delivery
# ──────────────────────────────────────────────────────────────────────

MAILBOX = "/var/mail/security"


class TestMailDelivery:
    def test_security_user_exists(self):
        """The local user 'security' must exist."""
        result = subprocess.run(
            ["id", "security"],
            capture_output=True, text=True, timeout=5
        )
        assert result.returncode == 0, "Local user 'security' must exist"

    def test_mailbox_exists(self):
        assert file_exists(MAILBOX), f"{MAILBOX} must exist"

    def test_mailbox_not_empty(self):
        content = read_file(MAILBOX).strip()
        assert len(content) > 0, (
            "Mailbox must not be empty — digest should have been triggered"
        )

    def test_mail_contains_fim_daily_digest_subject(self):
        """Mail must have a Subject header containing 'FIM Daily Digest'."""
        content = read_file(MAILBOX)
        assert re.search(r"Subject:.*FIM Daily Digest", content, re.IGNORECASE), (
            "Mail must contain a Subject header with 'FIM Daily Digest'"
        )

    def test_mail_body_has_change_log_content(self):
        """Mail body should include actual change log entries (not just empty)."""
        content = read_file(MAILBOX)
        # The mail body should contain at least one event keyword from the log
        has_event = (
            "ADDED" in content
            or "MODIFIED" in content
            or "DELETED" in content
            or "No changes detected" in content
        )
        assert has_event, (
            "Mail body must contain change log entries or 'No changes detected'"
        )


# ──────────────────────────────────────────────────────────────────────
# 9. FIM functional test — init produces correct hashes
# ──────────────────────────────────────────────────────────────────────

class TestFIMFunctionality:
    def test_fim_init_produces_correct_hashes(self):
        """Run fim init on a temp dir and verify hashes match sha256sum."""
        import tempfile
        tmpdir = tempfile.mkdtemp(prefix="fim_test_")
        testfile = os.path.join(tmpdir, "hello.txt")
        with open(testfile, "w") as f:
            f.write("hello world\n")

        expected_hash = sha256_of_file(testfile)

        # Run fim init
        result = subprocess.run(
            ["/usr/local/bin/fim", "init", tmpdir],
            capture_output=True, text=True, timeout=10
        )
        assert result.returncode == 0, f"fim init failed: {result.stderr}"

        # Read baseline and find our file
        baseline = read_file(BASELINE_PATH)
        found = False
        for line in baseline.strip().splitlines():
            parts = line.split("  ", 1)
            if len(parts) == 2 and parts[1] == testfile:
                assert parts[0] == expected_hash, (
                    f"Hash mismatch: expected {expected_hash}, got {parts[0]}"
                )
                found = True
                break
        assert found, f"{testfile} not found in baseline after fim init"

        # Cleanup
        os.unlink(testfile)
        os.rmdir(tmpdir)

    def test_fim_check_detects_new_file(self):
        """Create a file after init and verify fim check logs ADDED."""
        import tempfile
        tmpdir = tempfile.mkdtemp(prefix="fim_chk_")

        # Init with empty dir
        subprocess.run(
            ["/usr/local/bin/fim", "init", tmpdir],
            capture_output=True, timeout=10
        )

        # Truncate changelog to isolate our test
        with open(CHANGELOG, "w") as f:
            f.write("")

        # Add a new file
        newfile = os.path.join(tmpdir, "newfile.txt")
        with open(newfile, "w") as f:
            f.write("new content\n")

        # Run check
        result = subprocess.run(
            ["/usr/local/bin/fim", "check", tmpdir],
            capture_output=True, text=True, timeout=10
        )
        assert result.returncode == 0, f"fim check failed: {result.stderr}"

        log_content = read_file(CHANGELOG)
        assert re.search(r"ADDED\s+" + re.escape(newfile), log_content), (
            "fim check must log ADDED for a newly created file"
        )

        # Cleanup
        os.unlink(newfile)
        os.rmdir(tmpdir)

        # Restore baseline for webroot
        subprocess.run(
            ["/usr/local/bin/fim", "init", "/var/www/html"],
            capture_output=True, timeout=10
        )

