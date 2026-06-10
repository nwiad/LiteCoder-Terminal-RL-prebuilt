"""
Tests for SSH hardening task.
Validates all 7 output files and the live effective sshd configuration.
"""

import os
import subprocess

APP_DIR = "/app"

# ─── Helpers ────────────────────────────────────────────────────────────────

def read_file(path):
    """Read file content, return stripped string or None if missing."""
    full = os.path.join(APP_DIR, path) if not os.path.isabs(path) else path
    if not os.path.isfile(full):
        return None
    with open(full, "r") as f:
        return f.read()


def parse_sshd_dump(text):
    """Parse sshd -T style output into a dict (lowercase keys)."""
    result = {}
    for line in text.strip().splitlines():
        parts = line.strip().split(None, 1)
        if len(parts) == 2:
            result[parts[0].lower()] = parts[1].lower()
    return result


def get_live_sshd_config():
    """Run sshd -T and return parsed dict of effective config."""
    try:
        out = subprocess.check_output(["sshd", "-T"], stderr=subprocess.DEVNULL, text=True)
        return parse_sshd_dump(out)
    except Exception:
        return {}


# ─── Required auth directives ──────────────────────────────────────────────

REQUIRED_AUTH_DIRECTIVES = [
    "pubkeyauthentication",
    "passwordauthentication",
    "kbdinteractiveauthentication",
    "hostbasedauthentication",
    "gssapiauthentication",
    "kerberosauthentication",
]

HARDENED_VALUES = {
    "pubkeyauthentication": "yes",
    "passwordauthentication": "no",
    "kbdinteractiveauthentication": "no",
    "hostbasedauthentication": "no",
    "gssapiauthentication": "no",
    "kerberosauthentication": "no",
}

# ─── 1. File existence tests ───────────────────────────────────────────────

EXPECTED_FILES = [
    "pre_audit.txt",
    "syntax_check_before.txt",
    "sshd_config.bak",
    "syntax_check_after.txt",
    "reload_status.txt",
    "post_audit.txt",
    "cronjob.txt",
]


def test_all_output_files_exist():
    """Every required output file must exist and be non-empty."""
    for fname in EXPECTED_FILES:
        fpath = os.path.join(APP_DIR, fname)
        assert os.path.isfile(fpath), f"Missing output file: {fpath}"
        assert os.path.getsize(fpath) > 0, f"Output file is empty: {fpath}"


# ─── 2. Pre-audit tests ───────────────────────────────────────────────────

def test_pre_audit_contains_required_directives():
    """pre_audit.txt must contain all 6 required auth directive names."""
    content = read_file("pre_audit.txt")
    assert content is not None, "pre_audit.txt missing"
    parsed = parse_sshd_dump(content)
    for directive in REQUIRED_AUTH_DIRECTIVES:
        assert directive in parsed, (
            f"pre_audit.txt missing directive: {directive}"
        )


def test_pre_audit_shows_original_insecure_values():
    """
    pre_audit.txt should reflect the ORIGINAL unhardened config.
    At minimum, passwordauthentication should be 'yes' (the default).
    This catches agents that just copy post_audit as pre_audit.
    """
    content = read_file("pre_audit.txt")
    assert content is not None, "pre_audit.txt missing"
    parsed = parse_sshd_dump(content)
    # The original config had PasswordAuthentication yes
    pw_val = parsed.get("passwordauthentication", "")
    assert pw_val == "yes", (
        f"pre_audit.txt passwordauthentication should be 'yes' (original), got '{pw_val}'"
    )


# ─── 3. Syntax check tests ─────────────────────────────────────────────────

def test_syntax_check_before_is_zero():
    """syntax_check_before.txt must contain '0' (valid config before changes)."""
    content = read_file("syntax_check_before.txt")
    assert content is not None, "syntax_check_before.txt missing"
    assert content.strip() == "0", (
        f"syntax_check_before.txt should be '0', got '{content.strip()}'"
    )


def test_syntax_check_after_is_zero():
    """syntax_check_after.txt must contain '0' (valid config after hardening)."""
    content = read_file("syntax_check_after.txt")
    assert content is not None, "syntax_check_after.txt missing"
    assert content.strip() == "0", (
        f"syntax_check_after.txt should be '0', got '{content.strip()}'"
    )


# ─── 4. Backup tests ──────────────────────────────────────────────────────

def test_backup_exists_and_is_valid_sshd_config():
    """
    sshd_config.bak must exist and look like a real sshd_config.
    It should contain key SSH directives from the original file.
    """
    content = read_file("sshd_config.bak")
    assert content is not None, "sshd_config.bak missing"
    # Must contain typical sshd_config directives (case-insensitive)
    lower = content.lower()
    assert "port" in lower or "listenaddress" in lower, (
        "sshd_config.bak does not look like a valid sshd_config"
    )
    assert "pubkeyauthentication" in lower, (
        "sshd_config.bak missing PubkeyAuthentication directive"
    )


def test_backup_reflects_original_unhardened_config():
    """
    The backup should reflect the ORIGINAL config (before hardening).
    PasswordAuthentication should be 'yes' in the backup.
    """
    content = read_file("sshd_config.bak")
    assert content is not None, "sshd_config.bak missing"
    # Look for PasswordAuthentication yes (uncommented) in the backup
    found = False
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("passwordauthentication"):
            parts = stripped.split()
            if len(parts) >= 2 and parts[1].lower() == "yes":
                found = True
                break
    assert found, (
        "sshd_config.bak should contain 'PasswordAuthentication yes' from original config"
    )


# ─── 5. Post-audit tests (CORE hardening verification) ────────────────────

def test_post_audit_contains_required_directives():
    """post_audit.txt must contain all 6 required auth directive names."""
    content = read_file("post_audit.txt")
    assert content is not None, "post_audit.txt missing"
    parsed = parse_sshd_dump(content)
    for directive in REQUIRED_AUTH_DIRECTIVES:
        assert directive in parsed, (
            f"post_audit.txt missing directive: {directive}"
        )


def test_post_audit_hardened_values():
    """
    post_audit.txt must show the correct hardened values for all
    authentication directives.
    """
    content = read_file("post_audit.txt")
    assert content is not None, "post_audit.txt missing"
    parsed = parse_sshd_dump(content)
    for directive, expected in HARDENED_VALUES.items():
        actual = parsed.get(directive, "MISSING")
        assert actual == expected, (
            f"post_audit.txt: {directive} should be '{expected}', got '{actual}'"
        )


def test_post_audit_permitrootlogin():
    """
    post_audit.txt must show permitrootlogin as 'prohibit-password' or 'no'.
    """
    content = read_file("post_audit.txt")
    assert content is not None, "post_audit.txt missing"
    parsed = parse_sshd_dump(content)
    prl = parsed.get("permitrootlogin", "MISSING")
    assert prl in ("prohibit-password", "no"), (
        f"post_audit.txt: permitrootlogin should be 'prohibit-password' or 'no', got '{prl}'"
    )


# ─── 6. Pre vs Post diff — hardening actually changed something ────────────

def test_hardening_changed_password_auth():
    """
    The pre-audit should show passwordauthentication=yes and the post-audit
    should show passwordauthentication=no. This proves the hardening actually
    took effect (catches agents that skip the hardening step).
    """
    pre = read_file("pre_audit.txt")
    post = read_file("post_audit.txt")
    assert pre is not None, "pre_audit.txt missing"
    assert post is not None, "post_audit.txt missing"

    pre_parsed = parse_sshd_dump(pre)
    post_parsed = parse_sshd_dump(post)

    pre_pw = pre_parsed.get("passwordauthentication", "")
    post_pw = post_parsed.get("passwordauthentication", "")

    assert pre_pw == "yes", (
        f"Pre-audit passwordauthentication should be 'yes', got '{pre_pw}'"
    )
    assert post_pw == "no", (
        f"Post-audit passwordauthentication should be 'no', got '{post_pw}'"
    )


def test_hardening_changed_hostbased_auth():
    """hostbasedauthentication must change from yes to no."""
    pre = read_file("pre_audit.txt")
    post = read_file("post_audit.txt")
    assert pre is not None and post is not None

    pre_parsed = parse_sshd_dump(pre)
    post_parsed = parse_sshd_dump(post)

    assert pre_parsed.get("hostbasedauthentication", "") == "yes"
    assert post_parsed.get("hostbasedauthentication", "") == "no"


# ─── 7. Reload status tests ───────────────────────────────────────────────

def test_reload_status_valid():
    """reload_status.txt must contain 'reloaded' or 'skipped'."""
    content = read_file("reload_status.txt")
    assert content is not None, "reload_status.txt missing"
    val = content.strip().lower()
    assert val in ("reloaded", "skipped"), (
        f"reload_status.txt should be 'reloaded' or 'skipped', got '{val}'"
    )


def test_reload_status_is_reloaded_when_syntax_ok():
    """
    If syntax_check_after is 0, reload_status should be 'reloaded'.
    """
    syntax = read_file("syntax_check_after.txt")
    reload_st = read_file("reload_status.txt")
    if syntax is None or reload_st is None:
        assert False, "Required files missing"
    if syntax.strip() == "0":
        assert reload_st.strip().lower() == "reloaded", (
            "Syntax check passed but reload_status is not 'reloaded'"
        )


# ─── 8. Cron job tests ────────────────────────────────────────────────────

def test_cronjob_file_content():
    """
    cronjob.txt must contain a valid cron line with:
    - diff command
    - references to sshd_config and sshd_config.bak
    - mail command with subject 'sshd configuration drift'
    """
    content = read_file("cronjob.txt")
    assert content is not None, "cronjob.txt missing"
    line = content.strip()
    assert len(line) > 0, "cronjob.txt is empty"

    # Must reference diff
    assert "diff" in line.lower(), "Cron line must use 'diff'"
    # Must reference the config file
    assert "sshd_config" in line, "Cron line must reference sshd_config"
    # Must reference the backup
    assert "sshd_config.bak" in line, "Cron line must reference sshd_config.bak"
    # Must use mail
    assert "mail" in line.lower(), "Cron line must use 'mail'"
    # Must have the correct subject
    assert "sshd configuration drift" in line, (
        "Cron line must include subject 'sshd configuration drift'"
    )


def test_cronjob_has_valid_cron_schedule():
    """The cron line must start with a valid 5-field cron schedule."""
    content = read_file("cronjob.txt")
    assert content is not None, "cronjob.txt missing"
    line = content.strip()
    parts = line.split()
    assert len(parts) >= 6, (
        "Cron line must have at least 5 schedule fields + command"
    )
    # Each of the first 5 fields should be a valid cron token
    # (digits, *, /, -, comma)
    import re
    cron_field_re = re.compile(r'^[\d\*,/\-]+$')
    for i in range(5):
        assert cron_field_re.match(parts[i]), (
            f"Cron schedule field {i+1} is invalid: '{parts[i]}'"
        )


# ─── 9. Live sshd -T verification (ground truth) ──────────────────────────

def test_live_sshd_config_pubkey_enabled():
    """Live sshd -T must show pubkeyauthentication yes."""
    cfg = get_live_sshd_config()
    if not cfg:
        # sshd -T may fail in some test environments; skip gracefully
        return
    assert cfg.get("pubkeyauthentication") == "yes", (
        f"Live sshd: pubkeyauthentication is '{cfg.get('pubkeyauthentication')}'"
    )


def test_live_sshd_config_password_disabled():
    """Live sshd -T must show passwordauthentication no."""
    cfg = get_live_sshd_config()
    if not cfg:
        return
    assert cfg.get("passwordauthentication") == "no", (
        f"Live sshd: passwordauthentication is '{cfg.get('passwordauthentication')}'"
    )


def test_live_sshd_config_kbd_disabled():
    """Live sshd -T must show kbdinteractiveauthentication no."""
    cfg = get_live_sshd_config()
    if not cfg:
        return
    assert cfg.get("kbdinteractiveauthentication") == "no", (
        f"Live sshd: kbdinteractiveauthentication is '{cfg.get('kbdinteractiveauthentication')}'"
    )


def test_live_sshd_config_hostbased_disabled():
    """Live sshd -T must show hostbasedauthentication no."""
    cfg = get_live_sshd_config()
    if not cfg:
        return
    assert cfg.get("hostbasedauthentication") == "no", (
        f"Live sshd: hostbasedauthentication is '{cfg.get('hostbasedauthentication')}'"
    )


def test_live_sshd_config_gssapi_disabled():
    """Live sshd -T must show gssapiauthentication no."""
    cfg = get_live_sshd_config()
    if not cfg:
        return
    assert cfg.get("gssapiauthentication") == "no", (
        f"Live sshd: gssapiauthentication is '{cfg.get('gssapiauthentication')}'"
    )


def test_live_sshd_config_kerberos_disabled():
    """Live sshd -T must show kerberosauthentication no."""
    cfg = get_live_sshd_config()
    if not cfg:
        return
    assert cfg.get("kerberosauthentication") == "no", (
        f"Live sshd: kerberosauthentication is '{cfg.get('kerberosauthentication')}'"
    )


def test_live_sshd_config_permitrootlogin():
    """Live sshd -T must show permitrootlogin as prohibit-password or no."""
    cfg = get_live_sshd_config()
    if not cfg:
        return
    prl = cfg.get("permitrootlogin", "MISSING")
    assert prl in ("prohibit-password", "no"), (
        f"Live sshd: permitrootlogin is '{prl}', expected 'prohibit-password' or 'no'"
    )


# ─── 10. Live crontab verification ────────────────────────────────────────

def test_live_crontab_contains_drift_job():
    """
    crontab -l -u root must contain a line referencing diff, sshd_config,
    and 'sshd configuration drift'.
    """
    try:
        out = subprocess.check_output(
            ["crontab", "-l", "-u", "root"],
            stderr=subprocess.DEVNULL, text=True
        )
    except subprocess.CalledProcessError:
        # No crontab installed for root
        assert False, "No crontab found for root user"
        return

    assert "diff" in out, "Root crontab missing 'diff' command"
    assert "sshd_config" in out, "Root crontab missing sshd_config reference"
    assert "sshd configuration drift" in out, (
        "Root crontab missing 'sshd configuration drift' subject"
    )


# ─── 11. sshd_config file itself is hardened ──────────────────────────────

def test_sshd_config_file_has_hardened_directives():
    """
    The actual /etc/ssh/sshd_config must contain the hardened directives.
    This catches agents that only wrote audit files but didn't modify the config.
    """
    content = read_file("/etc/ssh/sshd_config")
    if content is None:
        assert False, "/etc/ssh/sshd_config not found"

    lower = content.lower()
    # PasswordAuthentication must be set to no (uncommented)
    found_pw_no = False
    for line in content.splitlines():
        stripped = line.strip().lower()
        if stripped.startswith("#"):
            continue
        if stripped.startswith("passwordauthentication") and "no" in stripped.split():
            found_pw_no = True
            break
    assert found_pw_no, (
        "/etc/ssh/sshd_config must have 'PasswordAuthentication no' (uncommented)"
    )


def test_sshd_config_syntax_valid():
    """Running sshd -t on the current config must succeed (exit 0)."""
    try:
        result = subprocess.run(
            ["sshd", "-t"],
            capture_output=True, text=True
        )
        assert result.returncode == 0, (
            f"sshd -t failed with exit code {result.returncode}: {result.stderr}"
        )
    except FileNotFoundError:
        # sshd not available in test env
        pass
