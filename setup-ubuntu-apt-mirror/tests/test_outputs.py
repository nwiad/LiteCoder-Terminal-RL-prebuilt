"""
Tests for the Ubuntu apt-mirror setup task.
Validates all 6 artifacts: apt-mirror config, web server, local apt source,
cron job, and disk usage script.
"""

import os
import re
import stat
import subprocess


# =============================================================================
# Task 1: apt-mirror package installed
# =============================================================================

def test_apt_mirror_installed():
    """apt-mirror binary must be available on the system."""
    result = subprocess.run(
        ["which", "apt-mirror"],
        capture_output=True, text=True
    )
    assert result.returncode == 0, "apt-mirror is not installed"


def test_apt_mirror_is_executable():
    """apt-mirror binary must be executable."""
    result = subprocess.run(
        ["which", "apt-mirror"],
        capture_output=True, text=True
    )
    path = result.stdout.strip()
    assert path, "apt-mirror binary not found"
    assert os.access(path, os.X_OK), f"apt-mirror at {path} is not executable"


# =============================================================================
# Task 2: /etc/apt/mirror.list configuration
# =============================================================================

MIRROR_LIST = "/etc/apt/mirror.list"


def test_mirror_list_exists():
    """mirror.list config file must exist."""
    assert os.path.isfile(MIRROR_LIST), f"{MIRROR_LIST} does not exist"


def test_mirror_list_base_path():
    """mirror.list must set base_path to /var/spool/apt-mirror."""
    content = _read_file(MIRROR_LIST)
    # Match: set base_path /var/spool/apt-mirror (with flexible whitespace)
    pattern = r"^\s*set\s+base_path\s+/var/spool/apt-mirror\s*$"
    assert re.search(pattern, content, re.MULTILINE), \
        "base_path must be set to /var/spool/apt-mirror"


def test_mirror_list_has_deb_line():
    """mirror.list must have a deb line for jammy main universe."""
    content = _read_file(MIRROR_LIST)
    lines = _non_comment_lines(content)
    deb_lines = [l for l in lines if re.match(r"^\s*deb\s+", l) and "deb-src" not in l.split()[0]]
    assert len(deb_lines) >= 1, "No deb line found in mirror.list"
    # At least one deb line must reference jammy with main and universe
    found = any(_line_has_jammy_main_universe(l) for l in deb_lines)
    assert found, "No deb line with jammy main universe found"


def test_mirror_list_has_deb_src_line():
    """mirror.list must have a deb-src line for jammy main universe."""
    content = _read_file(MIRROR_LIST)
    lines = _non_comment_lines(content)
    src_lines = [l for l in lines if re.match(r"^\s*deb-src\s+", l)]
    assert len(src_lines) >= 1, "No deb-src line found in mirror.list"
    found = any(_line_has_jammy_main_universe(l) for l in src_lines)
    assert found, "No deb-src line with jammy main universe found"


def test_mirror_list_uses_archive_ubuntu():
    """mirror.list must reference archive.ubuntu.com/ubuntu."""
    content = _read_file(MIRROR_LIST)
    lines = _non_comment_lines(content)
    deb_lines = [l for l in lines if re.match(r"^\s*deb(-src)?\s+", l)]
    found = any("archive.ubuntu.com/ubuntu" in l for l in deb_lines)
    assert found, "mirror.list must reference http://archive.ubuntu.com/ubuntu"


def test_mirror_list_no_restricted_multiverse():
    """mirror.list deb/deb-src lines must NOT include restricted or multiverse."""
    content = _read_file(MIRROR_LIST)
    lines = _non_comment_lines(content)
    deb_lines = [l for l in lines if re.match(r"^\s*deb(-src)?\s+", l)]
    for line in deb_lines:
        parts = line.lower().split()
        assert "restricted" not in parts, \
            f"mirror.list must not include 'restricted': {line}"
        assert "multiverse" not in parts, \
            f"mirror.list must not include 'multiverse': {line}"


# =============================================================================
# Task 3: Web server installed and configured
# =============================================================================

def test_web_server_installed():
    """Either nginx or apache2 must be installed."""
    nginx = subprocess.run(["which", "nginx"], capture_output=True)
    apache = subprocess.run(["which", "apache2"], capture_output=True)
    assert nginx.returncode == 0 or apache.returncode == 0, \
        "Neither nginx nor apache2 is installed"


def test_web_server_config_serves_mirror():
    """Web server config must serve content from /var/spool/apt-mirror/mirror."""
    nginx_ok = _check_nginx_config()
    apache_ok = _check_apache_config()
    assert nginx_ok or apache_ok, \
        "No web server config found that serves /var/spool/apt-mirror/mirror"


def _check_nginx_config():
    """Check if nginx is configured to serve the mirror directory."""
    config_dirs = ["/etc/nginx/sites-enabled", "/etc/nginx/conf.d"]
    for config_dir in config_dirs:
        if not os.path.isdir(config_dir):
            continue
        for fname in os.listdir(config_dir):
            fpath = os.path.join(config_dir, fname)
            if os.path.isfile(fpath) or os.path.islink(fpath):
                try:
                    # Resolve symlinks
                    real_path = os.path.realpath(fpath)
                    content = _read_file(real_path)
                    if "/var/spool/apt-mirror/mirror" in content:
                        return True
                except Exception:
                    continue
    return False


def _check_apache_config():
    """Check if apache2 is configured to serve the mirror directory."""
    config_dirs = ["/etc/apache2/sites-enabled", "/etc/apache2/conf-enabled"]
    for config_dir in config_dirs:
        if not os.path.isdir(config_dir):
            continue
        for fname in os.listdir(config_dir):
            fpath = os.path.join(config_dir, fname)
            if os.path.isfile(fpath) or os.path.islink(fpath):
                try:
                    real_path = os.path.realpath(fpath)
                    content = _read_file(real_path)
                    if "/var/spool/apt-mirror/mirror" in content:
                        return True
                except Exception:
                    continue
    return False


def test_web_server_config_has_autoindex_or_listing():
    """Web server config should enable directory listing (autoindex/Indexes)."""
    nginx_ok = False
    apache_ok = False
    # Check nginx
    for d in ["/etc/nginx/sites-enabled", "/etc/nginx/conf.d"]:
        if os.path.isdir(d):
            for f in os.listdir(d):
                try:
                    content = _read_file(os.path.realpath(os.path.join(d, f)))
                    if "autoindex" in content.lower():
                        nginx_ok = True
                except Exception:
                    pass
    # Check apache
    for d in ["/etc/apache2/sites-enabled", "/etc/apache2/conf-enabled"]:
        if os.path.isdir(d):
            for f in os.listdir(d):
                try:
                    content = _read_file(os.path.realpath(os.path.join(d, f)))
                    if "indexes" in content.lower():
                        apache_ok = True
                except Exception:
                    pass
    # This is a soft check — autoindex/Indexes is strongly recommended
    # but the core requirement is serving the mirror directory
    assert nginx_ok or apache_ok, \
        "Web server config should enable directory listing (autoindex on / Options +Indexes)"


# =============================================================================
# Task 4: Local apt source configuration
# =============================================================================

LOCAL_MIRROR_LIST = "/etc/apt/sources.list.d/local-mirror.list"


def test_local_mirror_list_exists():
    """Local mirror sources list must exist."""
    assert os.path.isfile(LOCAL_MIRROR_LIST), f"{LOCAL_MIRROR_LIST} does not exist"


def test_local_mirror_list_not_empty():
    """Local mirror sources list must not be empty."""
    content = _read_file(LOCAL_MIRROR_LIST)
    assert content.strip(), f"{LOCAL_MIRROR_LIST} is empty"


def test_local_mirror_list_has_deb_line():
    """Local mirror list must contain at least one deb line."""
    content = _read_file(LOCAL_MIRROR_LIST)
    lines = _non_comment_lines(content)
    deb_lines = [l for l in lines if re.match(r"^\s*deb\s+", l) and "deb-src" not in l.split()[0]]
    assert len(deb_lines) >= 1, "No deb line found in local-mirror.list"


def test_local_mirror_list_points_to_localhost():
    """Local mirror list deb lines must reference localhost."""
    content = _read_file(LOCAL_MIRROR_LIST)
    lines = _non_comment_lines(content)
    deb_lines = [l for l in lines if re.match(r"^\s*deb(-src)?\s+", l)]
    assert len(deb_lines) >= 1, "No deb/deb-src lines in local-mirror.list"
    # At least one line must point to localhost (127.0.0.1 is also acceptable)
    found = any(
        "localhost" in l or "127.0.0.1" in l
        for l in deb_lines
    )
    assert found, "local-mirror.list must reference localhost or 127.0.0.1"


def test_local_mirror_list_has_jammy():
    """Local mirror list must reference jammy distribution."""
    content = _read_file(LOCAL_MIRROR_LIST)
    lines = _non_comment_lines(content)
    deb_lines = [l for l in lines if re.match(r"^\s*deb(-src)?\s+", l)]
    found = any("jammy" in l for l in deb_lines)
    assert found, "local-mirror.list must reference jammy distribution"


def test_local_mirror_list_has_main_universe():
    """Local mirror list must include main and universe components."""
    content = _read_file(LOCAL_MIRROR_LIST)
    lines = _non_comment_lines(content)
    deb_lines = [l for l in lines if re.match(r"^\s*deb\s+", l) and "deb-src" not in l.split()[0]]
    found = any(_line_has_jammy_main_universe(l) for l in deb_lines)
    assert found, "local-mirror.list must have a deb line with jammy main universe"


# =============================================================================
# Task 5: Cron job for daily apt-mirror update
# =============================================================================

CRON_FILE = "/etc/cron.d/apt-mirror-update"


def test_cron_file_exists():
    """Cron file for apt-mirror must exist."""
    assert os.path.isfile(CRON_FILE), f"{CRON_FILE} does not exist"


def test_cron_file_not_empty():
    """Cron file must not be empty."""
    content = _read_file(CRON_FILE)
    assert content.strip(), f"{CRON_FILE} is empty"


def test_cron_file_references_apt_mirror():
    """Cron file must execute apt-mirror."""
    content = _read_file(CRON_FILE)
    lines = _non_comment_lines(content)
    found = any("apt-mirror" in l for l in lines)
    assert found, "Cron file must reference apt-mirror command"


def test_cron_file_has_valid_syntax():
    """Cron file must have valid system cron syntax (5 time fields + user + command)."""
    content = _read_file(CRON_FILE)
    lines = _non_comment_lines(content)
    # Filter to lines that look like cron entries (not variable assignments)
    cron_lines = [l for l in lines if "apt-mirror" in l]
    assert len(cron_lines) >= 1, "No cron entry with apt-mirror found"

    # System cron format: min hour dom mon dow user command
    # Each time field can be: number, *, */N, ranges, lists
    time_field = r"[\d\*,/\-]+"
    # Pattern: 5 time fields, then a username, then a command
    cron_pattern = re.compile(
        r"^\s*" +
        r"\s+".join([time_field] * 5) +
        r"\s+\S+" +   # user field
        r"\s+.+"      # command
    )
    valid = any(cron_pattern.match(l) for l in cron_lines)
    assert valid, "Cron entry does not have valid system cron syntax (5 fields + user + cmd)"


def test_cron_file_runs_daily():
    """Cron job must run at least once per day (not weekly/monthly)."""
    content = _read_file(CRON_FILE)
    lines = _non_comment_lines(content)
    cron_lines = [l for l in lines if "apt-mirror" in l]
    assert len(cron_lines) >= 1, "No cron entry found"

    for line in cron_lines:
        parts = line.split()
        if len(parts) < 7:
            continue
        # Fields: min hour dom mon dow
        dom = parts[2]   # day of month
        mon = parts[3]   # month
        dow = parts[4]   # day of week
        # For daily: dom should be * (or */1), mon should be *, dow should be *
        # This ensures it runs every day, not restricted to specific days/months
        if mon == "*" and (dom == "*" or dom == "*/1") and (dow == "*" or dow == "*/1"):
            return  # Valid daily schedule
    assert False, "Cron job does not appear to run daily"


def test_cron_file_permissions():
    """Cron file must have proper permissions (644 or stricter, owned by root)."""
    st = os.stat(CRON_FILE)
    mode = stat.S_IMODE(st.st_mode)
    # Cron files in /etc/cron.d must not be group/world writable
    assert not (mode & stat.S_IWGRP), "Cron file must not be group-writable"
    assert not (mode & stat.S_IWOTH), "Cron file must not be world-writable"


# =============================================================================
# Task 6: Disk usage check script
# =============================================================================

DISK_SCRIPT = "/app/check_mirror_size.sh"


def test_disk_script_exists():
    """Disk usage script must exist."""
    assert os.path.isfile(DISK_SCRIPT), f"{DISK_SCRIPT} does not exist"


def test_disk_script_is_executable():
    """Disk usage script must be executable."""
    assert os.path.isfile(DISK_SCRIPT), f"{DISK_SCRIPT} does not exist"
    st = os.stat(DISK_SCRIPT)
    mode = stat.S_IMODE(st.st_mode)
    assert mode & stat.S_IXUSR, f"{DISK_SCRIPT} is not executable by owner"


def test_disk_script_uses_du():
    """Disk usage script must use the du command."""
    content = _read_file(DISK_SCRIPT)
    assert content.strip(), f"{DISK_SCRIPT} is empty"
    # Check that du is referenced in the script (not just in comments)
    lines = _non_comment_lines(content)
    found = any("du " in l or "du\t" in l or l.strip().startswith("du") for l in lines)
    assert found, "Script must use the 'du' command"


def test_disk_script_references_mirror_path():
    """Disk usage script must reference /var/spool/apt-mirror."""
    content = _read_file(DISK_SCRIPT)
    assert "/var/spool/apt-mirror" in content, \
        "Script must reference /var/spool/apt-mirror"


def test_disk_script_has_shebang():
    """Disk usage script should have a proper shebang line."""
    content = _read_file(DISK_SCRIPT)
    first_line = content.strip().split("\n")[0]
    assert first_line.startswith("#!"), \
        "Script should start with a shebang (e.g., #!/bin/bash)"


# =============================================================================
# Helper functions
# =============================================================================

def _read_file(path):
    """Read file content, raising AssertionError if file doesn't exist."""
    assert os.path.isfile(path), f"File not found: {path}"
    with open(path, "r") as f:
        return f.read()


def _non_comment_lines(content):
    """Return non-empty, non-comment lines from content."""
    lines = []
    for line in content.split("\n"):
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            lines.append(line)
    return lines


def _line_has_jammy_main_universe(line):
    """Check if a deb/deb-src line contains jammy, main, and universe."""
    parts = line.lower().split()
    return "jammy" in parts and "main" in parts and "universe" in parts
