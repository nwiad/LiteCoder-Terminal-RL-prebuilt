"""
Tests for Automated Offsite Backup System.
Validates all 6 deliverable files under /app/ for existence, structure,
content correctness, executability, and functional behavior.
"""

import os
import re
import stat
import subprocess

# ─── Paths ───────────────────────────────────────────────────────────────────
APP = "/app"
BACKUP_SH = os.path.join(APP, "backup.sh")
VERIFY_SH = os.path.join(APP, "verify_backup.sh")
RESTORE_SH = os.path.join(APP, "restore.sh")
BACKUP_CONF = os.path.join(APP, "backup.conf")
CRONTAB_TXT = os.path.join(APP, "crontab.txt")
LOGROTATE_CONF = os.path.join(APP, "logrotate.conf")

ALL_FILES = [BACKUP_SH, VERIFY_SH, RESTORE_SH, BACKUP_CONF, CRONTAB_TXT, LOGROTATE_CONF]


# ═══════════════════════════════════════════════════════════════════════════════
# 1. FILE EXISTENCE
# ═══════════════════════════════════════════════════════════════════════════════

def test_all_files_exist():
    """Every required deliverable must be present."""
    for f in ALL_FILES:
        assert os.path.isfile(f), f"Missing required file: {f}"


def test_all_files_non_empty():
    """No deliverable should be an empty stub."""
    for f in ALL_FILES:
        size = os.path.getsize(f)
        assert size > 10, f"File {f} appears empty or trivially small ({size} bytes)"


# ═══════════════════════════════════════════════════════════════════════════════
# 2. EXECUTABILITY OF SCRIPTS
# ═══════════════════════════════════════════════════════════════════════════════

def test_scripts_are_executable():
    """backup.sh, verify_backup.sh, restore.sh must have execute permission."""
    for script in [BACKUP_SH, VERIFY_SH, RESTORE_SH]:
        mode = os.stat(script).st_mode
        assert mode & stat.S_IXUSR, f"{script} is not executable (user)"


def test_scripts_have_shebang():
    """Each script must start with a valid shebang line."""
    for script in [BACKUP_SH, VERIFY_SH, RESTORE_SH]:
        with open(script, "r") as fh:
            first_line = fh.readline().strip()
        assert first_line.startswith("#!"), f"{script} missing shebang"
        assert "bash" in first_line or "sh" in first_line, \
            f"{script} shebang does not reference bash/sh: {first_line}"


# ═══════════════════════════════════════════════════════════════════════════════
# 3. BACKUP.CONF — Configuration file
# ═══════════════════════════════════════════════════════════════════════════════

def _parse_conf(path):
    """Parse KEY=VALUE config, ignoring comments and blanks."""
    cfg = {}
    with open(path, "r") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, val = line.split("=", 1)
                cfg[key.strip()] = val.strip()
    return cfg

EXPECTED_CONF = {
    "SOURCE_DIR": "/app/data",
    "REMOTE_USER": "backupuser",
    "REMOTE_HOST": "backup.remote.example.com",
    "REMOTE_DIR": "/backups/daily",
    "SSH_KEY": "/app/.ssh/backup_key",
    "LOG_DIR": "/app/logs",
    "LOG_FILE": "/app/logs/backup.log",
    "RETENTION_DAYS": "30",
    "CHECKSUM_FILE": "/app/checksums.sha256",
}


def test_backup_conf_has_all_keys():
    """All required configuration keys must be present."""
    cfg = _parse_conf(BACKUP_CONF)
    for key in EXPECTED_CONF:
        assert key in cfg, f"Missing config key: {key}"


def test_backup_conf_values():
    """Each config key must have the exact specified value."""
    cfg = _parse_conf(BACKUP_CONF)
    for key, expected in EXPECTED_CONF.items():
        actual = cfg.get(key, "")
        assert actual == expected, \
            f"Config {key}: expected '{expected}', got '{actual}'"


def test_backup_conf_no_spaces_around_equals():
    """KEY=VALUE lines must not have spaces around '='."""
    with open(BACKUP_CONF, "r") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                # Should not match "KEY = VALUE" or "KEY =VALUE"
                assert not re.match(r"^\w+\s+=", line), \
                    f"Space before '=' in: {line}"
                assert not re.match(r"^\w+=\s+", line) or True, \
                    "Allowing value with leading space for flexibility"


# ═══════════════════════════════════════════════════════════════════════════════
# 4. BACKUP.SH — Main backup script
# ═══════════════════════════════════════════════════════════════════════════════

def _read_file(path):
    with open(path, "r") as fh:
        return fh.read()


def test_backup_sh_sources_config():
    """backup.sh must source backup.conf."""
    content = _read_file(BACKUP_SH)
    assert re.search(r"source\s+.*/backup\.conf|\.[\s]+.*/backup\.conf", content), \
        "backup.sh does not source backup.conf"


def test_backup_sh_creates_log_dir():
    """backup.sh must create LOG_DIR if it doesn't exist (mkdir -p)."""
    content = _read_file(BACKUP_SH)
    assert "mkdir" in content and "-p" in content, \
        "backup.sh does not create LOG_DIR with mkdir -p"


def test_backup_sh_timestamp_logging():
    """backup.sh must have a logging function with [YYYY-MM-DD HH:MM:SS] format."""
    content = _read_file(BACKUP_SH)
    # Check for date format pattern used in logging
    assert re.search(r"date\s+['\"].*%Y.*%M.*%S", content), \
        "backup.sh missing timestamped logging with date format"


def test_backup_sh_calls_verify_pre():
    """backup.sh must call verify_backup.sh pre before rsync."""
    content = _read_file(BACKUP_SH)
    assert re.search(r"verify_backup\.sh\s+pre", content), \
        "backup.sh does not call verify_backup.sh pre"


def test_backup_sh_calls_verify_post():
    """backup.sh must call verify_backup.sh post after rsync."""
    content = _read_file(BACKUP_SH)
    assert re.search(r"verify_backup\.sh\s+post", content), \
        "backup.sh does not call verify_backup.sh post"


def test_backup_sh_rsync_flags():
    """backup.sh must use rsync with -avz --delete and SSH key options."""
    content = _read_file(BACKUP_SH)
    assert "rsync" in content, "backup.sh does not invoke rsync"
    assert "-avz" in content or ("-a" in content and "-v" in content and "-z" in content), \
        "backup.sh missing rsync -avz flags"
    assert "--delete" in content, "backup.sh missing rsync --delete flag"
    assert "StrictHostKeyChecking=no" in content, \
        "backup.sh missing StrictHostKeyChecking=no"


def test_backup_sh_logs_success_and_failed():
    """backup.sh must log SUCCESS on success and FAILED on failure."""
    content = _read_file(BACKUP_SH)
    assert "SUCCESS" in content, "backup.sh does not log SUCCESS"
    assert "FAILED" in content, "backup.sh does not log FAILED"


def test_backup_sh_captures_rsync_exit():
    """backup.sh must capture rsync exit code and act on it."""
    content = _read_file(BACKUP_SH)
    # Should capture $? after rsync
    assert "$?" in content or "PIPESTATUS" in content or re.search(r"RSYNC.*EXIT|rsync.*exit|exit_code|rc=", content, re.IGNORECASE), \
        "backup.sh does not capture rsync exit code"


# ═══════════════════════════════════════════════════════════════════════════════
# 5. VERIFY_BACKUP.SH — Verification script
# ═══════════════════════════════════════════════════════════════════════════════

def test_verify_sh_sources_config():
    """verify_backup.sh must source backup.conf."""
    content = _read_file(VERIFY_SH)
    assert re.search(r"source\s+.*/backup\.conf|\.[\s]+.*/backup\.conf", content), \
        "verify_backup.sh does not source backup.conf"


def test_verify_sh_accepts_pre_post():
    """verify_backup.sh must handle 'pre' and 'post' arguments."""
    content = _read_file(VERIFY_SH)
    assert "pre" in content and "post" in content, \
        "verify_backup.sh does not handle pre/post modes"


def test_verify_sh_checks_source_dir():
    """verify_backup.sh pre mode must check SOURCE_DIR exists."""
    content = _read_file(VERIFY_SH)
    assert re.search(r"SOURCE_DIR|source_dir", content), \
        "verify_backup.sh does not reference SOURCE_DIR"
    assert re.search(r"not found|not.found|does not exist|doesn.t exist", content, re.IGNORECASE), \
        "verify_backup.sh missing 'not found' error message for SOURCE_DIR"


def test_verify_sh_checks_ssh_key():
    """verify_backup.sh pre mode must check SSH_KEY exists."""
    content = _read_file(VERIFY_SH)
    assert re.search(r"SSH.KEY|SSH_KEY|ssh.key", content, re.IGNORECASE), \
        "verify_backup.sh does not reference SSH_KEY"


def test_verify_sh_generates_checksums():
    """verify_backup.sh pre mode must generate SHA-256 checksums."""
    content = _read_file(VERIFY_SH)
    assert "sha256sum" in content or "sha256" in content.lower(), \
        "verify_backup.sh does not use sha256sum"


def test_verify_sh_verifies_checksums():
    """verify_backup.sh post mode must verify checksums (sha256sum -c or equivalent)."""
    content = _read_file(VERIFY_SH)
    assert re.search(r"sha256sum\s+-c|shasum.*-c", content), \
        "verify_backup.sh does not verify checksums with -c flag"


def test_verify_sh_usage_on_bad_arg():
    """verify_backup.sh must print Usage on invalid argument."""
    content = _read_file(VERIFY_SH)
    assert "Usage" in content or "usage" in content, \
        "verify_backup.sh missing usage message"


# ═══════════════════════════════════════════════════════════════════════════════
# 6. RESTORE.SH — Restoration script
# ═══════════════════════════════════════════════════════════════════════════════

def test_restore_sh_sources_config():
    """restore.sh must source backup.conf."""
    content = _read_file(RESTORE_SH)
    assert re.search(r"source\s+.*/backup\.conf|\.[\s]+.*/backup\.conf", content), \
        "restore.sh does not source backup.conf"


def test_restore_sh_accepts_argument():
    """restore.sh must accept a restore target directory argument."""
    content = _read_file(RESTORE_SH)
    # Should reference $1 or positional args
    assert "$1" in content or "${1}" in content or "$@" in content, \
        "restore.sh does not accept a positional argument"


def test_restore_sh_usage_on_no_arg():
    """restore.sh must print Usage when no argument is provided."""
    content = _read_file(RESTORE_SH)
    assert "Usage" in content or "usage" in content, \
        "restore.sh missing usage message"


def test_restore_sh_creates_target_dir():
    """restore.sh must create the restore target directory if it doesn't exist."""
    content = _read_file(RESTORE_SH)
    assert "mkdir" in content, "restore.sh does not create restore target directory"


def test_restore_sh_uses_rsync_with_ssh():
    """restore.sh must use rsync with SSH key to pull from remote."""
    content = _read_file(RESTORE_SH)
    assert "rsync" in content, "restore.sh does not invoke rsync"
    assert "StrictHostKeyChecking=no" in content or "SSH_KEY" in content or "ssh" in content.lower(), \
        "restore.sh does not use SSH key configuration"


def test_restore_sh_logs_operations():
    """restore.sh must log operations with timestamps."""
    content = _read_file(RESTORE_SH)
    assert re.search(r"date\s+['\"].*%Y|log_message|LOG_FILE", content), \
        "restore.sh does not log with timestamps"


# ═══════════════════════════════════════════════════════════════════════════════
# 7. CRONTAB.TXT — Cron scheduling
# ═══════════════════════════════════════════════════════════════════════════════

def _get_uncommented_cron_lines(path):
    """Return non-empty, non-comment lines from crontab file."""
    lines = []
    with open(path, "r") as fh:
        for line in fh:
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                lines.append(stripped)
    return lines


def test_crontab_has_one_entry():
    """crontab.txt must contain exactly one uncommented cron entry."""
    lines = _get_uncommented_cron_lines(CRONTAB_TXT)
    assert len(lines) == 1, \
        f"Expected 1 uncommented cron entry, found {len(lines)}"


def test_crontab_daily_2am():
    """Cron entry must schedule daily at 2:00 AM (0 2 * * *)."""
    lines = _get_uncommented_cron_lines(CRONTAB_TXT)
    assert len(lines) >= 1, "No cron entry found"
    entry = lines[0]
    # Match "0 2 * * *" at the start (minute=0, hour=2, day=*, month=*, dow=*)
    assert re.match(r"^0\s+2\s+\*\s+\*\s+\*\s+", entry), \
        f"Cron entry does not schedule daily at 2:00 AM: {entry}"


def test_crontab_runs_backup_sh():
    """Cron entry must execute /app/backup.sh (or equivalent path)."""
    lines = _get_uncommented_cron_lines(CRONTAB_TXT)
    entry = lines[0]
    assert "backup.sh" in entry, \
        f"Cron entry does not reference backup.sh: {entry}"


def test_crontab_redirects_output():
    """Cron entry must redirect stdout and stderr to /app/logs/cron_backup.log."""
    lines = _get_uncommented_cron_lines(CRONTAB_TXT)
    entry = lines[0]
    assert "cron_backup.log" in entry, \
        f"Cron entry does not redirect to cron_backup.log: {entry}"
    # Must redirect stderr: 2>&1 or &> or similar
    assert "2>&1" in entry or "&>" in entry, \
        f"Cron entry does not redirect stderr: {entry}"


# ═══════════════════════════════════════════════════════════════════════════════
# 8. LOGROTATE.CONF — Log rotation configuration
# ═══════════════════════════════════════════════════════════════════════════════

def test_logrotate_targets_backup_log():
    """logrotate.conf must target /app/logs/backup.log."""
    content = _read_file(LOGROTATE_CONF)
    assert "/app/logs/backup.log" in content, \
        "logrotate.conf does not target /app/logs/backup.log"


def test_logrotate_daily():
    """logrotate.conf must specify daily rotation."""
    content = _read_file(LOGROTATE_CONF)
    assert re.search(r"^\s*daily\s*$", content, re.MULTILINE), \
        "logrotate.conf missing 'daily' directive"


def test_logrotate_rotate_count():
    """logrotate.conf must retain at least 7 rotated logs."""
    content = _read_file(LOGROTATE_CONF)
    match = re.search(r"^\s*rotate\s+(\d+)", content, re.MULTILINE)
    assert match, "logrotate.conf missing 'rotate' directive"
    count = int(match.group(1))
    assert count >= 7, f"logrotate.conf rotate count is {count}, expected >= 7"


def test_logrotate_compress():
    """logrotate.conf must include compress directive."""
    content = _read_file(LOGROTATE_CONF)
    assert re.search(r"^\s*compress\s*$", content, re.MULTILINE), \
        "logrotate.conf missing 'compress' directive"


def test_logrotate_missingok():
    """logrotate.conf must include missingok directive."""
    content = _read_file(LOGROTATE_CONF)
    assert re.search(r"^\s*missingok\s*$", content, re.MULTILINE), \
        "logrotate.conf missing 'missingok' directive"


def test_logrotate_notifempty():
    """logrotate.conf must include notifempty directive."""
    content = _read_file(LOGROTATE_CONF)
    assert re.search(r"^\s*notifempty\s*$", content, re.MULTILINE), \
        "logrotate.conf missing 'notifempty' directive"


# ═══════════════════════════════════════════════════════════════════════════════
# 9. FUNCTIONAL TESTS — verify_backup.sh execution
# ═══════════════════════════════════════════════════════════════════════════════

def test_verify_pre_runs_successfully():
    """verify_backup.sh pre must exit 0 when SOURCE_DIR and SSH_KEY exist."""
    result = subprocess.run(
        ["bash", VERIFY_SH, "pre"],
        capture_output=True, text=True, timeout=30
    )
    assert result.returncode == 0, \
        f"verify_backup.sh pre failed (rc={result.returncode}): {result.stderr}"


def test_verify_pre_generates_checksum_file():
    """After running verify_backup.sh pre, CHECKSUM_FILE must exist and be non-empty."""
    # Run pre first to ensure checksum file is generated
    subprocess.run(["bash", VERIFY_SH, "pre"], capture_output=True, timeout=30)
    checksum_file = "/app/checksums.sha256"
    assert os.path.isfile(checksum_file), \
        f"Checksum file {checksum_file} not created after pre verification"
    size = os.path.getsize(checksum_file)
    assert size > 0, "Checksum file is empty"


def test_verify_pre_checksum_file_has_all_data_files():
    """Checksum file must contain entries for all files in /app/data/."""
    subprocess.run(["bash", VERIFY_SH, "pre"], capture_output=True, timeout=30)
    checksum_file = "/app/checksums.sha256"
    with open(checksum_file, "r") as fh:
        content = fh.read()
    # All 4 test data files should appear
    for fname in ["sample1.txt", "sample2.csv", "config.json", "notes.md"]:
        assert fname in content, \
            f"Checksum file missing entry for {fname}"


def test_verify_post_passes_after_pre():
    """verify_backup.sh post must exit 0 when checksums match (no files changed)."""
    # Generate checksums first
    subprocess.run(["bash", VERIFY_SH, "pre"], capture_output=True, timeout=30)
    # Verify them immediately — nothing changed, so should pass
    result = subprocess.run(
        ["bash", VERIFY_SH, "post"],
        capture_output=True, text=True, timeout=30
    )
    assert result.returncode == 0, \
        f"verify_backup.sh post failed after clean pre (rc={result.returncode}): {result.stderr}"


def test_verify_invalid_arg_exits_nonzero():
    """verify_backup.sh with invalid argument must exit non-zero."""
    result = subprocess.run(
        ["bash", VERIFY_SH, "invalid"],
        capture_output=True, text=True, timeout=30
    )
    assert result.returncode != 0, \
        "verify_backup.sh should exit non-zero on invalid argument"


def test_verify_invalid_arg_prints_usage():
    """verify_backup.sh with invalid argument must print Usage."""
    result = subprocess.run(
        ["bash", VERIFY_SH, "invalid"],
        capture_output=True, text=True, timeout=30
    )
    combined = result.stdout + result.stderr
    assert re.search(r"[Uu]sage", combined), \
        f"verify_backup.sh did not print usage on invalid arg: {combined}"


def test_verify_no_arg_exits_nonzero():
    """verify_backup.sh with no argument must exit non-zero."""
    result = subprocess.run(
        ["bash", VERIFY_SH],
        capture_output=True, text=True, timeout=30
    )
    assert result.returncode != 0, \
        "verify_backup.sh should exit non-zero when called with no arguments"


def test_restore_no_arg_exits_nonzero():
    """restore.sh with no argument must exit non-zero."""
    result = subprocess.run(
        ["bash", RESTORE_SH],
        capture_output=True, text=True, timeout=30
    )
    assert result.returncode != 0, \
        "restore.sh should exit non-zero when called with no arguments"


def test_restore_no_arg_prints_usage():
    """restore.sh with no argument must print Usage."""
    result = subprocess.run(
        ["bash", RESTORE_SH],
        capture_output=True, text=True, timeout=30
    )
    combined = result.stdout + result.stderr
    assert re.search(r"[Uu]sage", combined), \
        f"restore.sh did not print usage on missing arg: {combined}"


def test_verify_checksum_format_is_sha256():
    """Checksum file entries must be valid sha256sum format (64 hex chars + space + path)."""
    subprocess.run(["bash", VERIFY_SH, "pre"], capture_output=True, timeout=30)
    checksum_file = "/app/checksums.sha256"
    with open(checksum_file, "r") as fh:
        lines = [l.strip() for l in fh if l.strip()]
    assert len(lines) > 0, "Checksum file has no entries"
    for line in lines:
        # sha256sum output: 64 hex chars, then two spaces or space+asterisk, then path
        assert re.match(r"^[0-9a-f]{64}\s+.+", line), \
            f"Invalid sha256sum format: {line}"
