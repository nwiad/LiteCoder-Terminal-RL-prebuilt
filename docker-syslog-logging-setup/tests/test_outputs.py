"""
Tests for Docker Syslog Logging Setup task.

Validates that all configuration files are correctly created with the
required content, directory permissions are set, and configs are syntactically valid.
"""

import os
import json
import re
import subprocess
import stat
import grp
import pwd


# =============================================================================
# 1. rsyslog configuration: /etc/rsyslog.d/30-docker.conf
# =============================================================================

RSYSLOG_CONF = "/etc/rsyslog.d/30-docker.conf"


def test_rsyslog_config_exists():
    """The rsyslog config file must exist at the specified path."""
    assert os.path.isfile(RSYSLOG_CONF), (
        f"rsyslog config file not found at {RSYSLOG_CONF}"
    )


def test_rsyslog_config_not_empty():
    """The rsyslog config must not be empty."""
    assert os.path.getsize(RSYSLOG_CONF) > 0, (
        f"{RSYSLOG_CONF} exists but is empty"
    )


def _read_rsyslog_conf():
    with open(RSYSLOG_CONF, "r") as f:
        return f.read()


def test_rsyslog_udp_enabled():
    """rsyslog must load the imudp module and listen on port 514."""
    content = _read_rsyslog_conf()
    # Check module load — accept both legacy ($ModLoad) and new-style (module(load=...))
    has_module = (
        re.search(r'module\s*\(\s*load\s*=\s*"imudp"\s*\)', content) is not None
        or re.search(r'\$ModLoad\s+imudp', content) is not None
    )
    assert has_module, "imudp module not loaded in rsyslog config"

    # Check port 514 for UDP
    has_port = (
        re.search(r'input\s*\(.*type\s*=\s*"imudp".*port\s*=\s*"514"', content) is not None
        or re.search(r'\$UDPServerRun\s+514', content) is not None
    )
    assert has_port, "UDP port 514 not configured in rsyslog config"


def test_rsyslog_tcp_enabled():
    """rsyslog must load the imtcp module and listen on port 514."""
    content = _read_rsyslog_conf()
    has_module = (
        re.search(r'module\s*\(\s*load\s*=\s*"imtcp"\s*\)', content) is not None
        or re.search(r'\$ModLoad\s+imtcp', content) is not None
    )
    assert has_module, "imtcp module not loaded in rsyslog config"

    has_port = (
        re.search(r'input\s*\(.*type\s*=\s*"imtcp".*port\s*=\s*"514"', content) is not None
        or re.search(r'\$InputTCPServerRun\s+514', content) is not None
    )
    assert has_port, "TCP port 514 not configured in rsyslog config"


def test_rsyslog_docker_tag_filter():
    """rsyslog must filter messages with syslog tag starting with 'docker/'."""
    content = _read_rsyslog_conf()
    # Accept various filter syntaxes for matching docker/ tag
    has_filter = (
        re.search(r':syslogtag,\s*startswith,\s*"docker/"', content) is not None
        or re.search(r"docker/", content) is not None
    )
    assert has_filter, "No docker/ syslog tag filter found in rsyslog config"


def test_rsyslog_output_path():
    """rsyslog must write docker logs to /var/log/docker/containers.log."""
    content = _read_rsyslog_conf()
    assert "/var/log/docker/containers.log" in content, (
        "Output path /var/log/docker/containers.log not found in rsyslog config"
    )


def test_rsyslog_stop_processing():
    """rsyslog must stop processing matched messages (no duplicates)."""
    content = _read_rsyslog_conf()
    # Accept "& stop" or "& ~" (legacy) for stopping further processing
    has_stop = (
        re.search(r'&\s*stop', content) is not None
        or re.search(r'&\s*~', content) is not None
    )
    assert has_stop, "No stop directive found — matched messages may be duplicated"


# =============================================================================
# 2. Log directory: /var/log/docker/
# =============================================================================

LOG_DIR = "/var/log/docker"


def test_log_directory_exists():
    """The /var/log/docker/ directory must exist."""
    assert os.path.isdir(LOG_DIR), f"Directory {LOG_DIR} does not exist"


def test_log_directory_permissions():
    """The /var/log/docker/ directory must have 0755 permissions."""
    st = os.stat(LOG_DIR)
    perms = stat.S_IMODE(st.st_mode)
    assert perms == 0o755, (
        f"Expected permissions 0755 for {LOG_DIR}, got {oct(perms)}"
    )


def test_log_directory_ownership():
    """The /var/log/docker/ directory must be owned by syslog:adm."""
    st = os.stat(LOG_DIR)
    try:
        owner_name = pwd.getpwuid(st.st_uid).pw_name
    except KeyError:
        owner_name = str(st.st_uid)
    try:
        group_name = grp.getgrgid(st.st_gid).gr_name
    except KeyError:
        group_name = str(st.st_gid)

    assert owner_name == "syslog", (
        f"Expected owner 'syslog' for {LOG_DIR}, got '{owner_name}'"
    )
    assert group_name == "adm", (
        f"Expected group 'adm' for {LOG_DIR}, got '{group_name}'"
    )


# =============================================================================
# 3. Docker daemon config: /etc/docker/daemon.json
# =============================================================================

DAEMON_JSON = "/etc/docker/daemon.json"


def test_daemon_json_exists():
    """The Docker daemon config must exist."""
    assert os.path.isfile(DAEMON_JSON), (
        f"Docker daemon config not found at {DAEMON_JSON}"
    )


def test_daemon_json_not_empty():
    """The Docker daemon config must not be empty."""
    assert os.path.getsize(DAEMON_JSON) > 0, (
        f"{DAEMON_JSON} exists but is empty"
    )


def test_daemon_json_valid_json():
    """The Docker daemon config must be valid JSON."""
    with open(DAEMON_JSON, "r") as f:
        raw = f.read()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        assert False, f"{DAEMON_JSON} is not valid JSON: {e}"
    assert isinstance(data, dict), f"{DAEMON_JSON} root must be a JSON object"


def test_daemon_json_log_driver():
    """The Docker daemon must use the syslog log driver."""
    with open(DAEMON_JSON, "r") as f:
        data = json.load(f)
    assert data.get("log-driver") == "syslog", (
        f"Expected log-driver 'syslog', got '{data.get('log-driver')}'"
    )


def test_daemon_json_syslog_address():
    """The syslog address must point to udp://127.0.0.1:514."""
    with open(DAEMON_JSON, "r") as f:
        data = json.load(f)
    log_opts = data.get("log-opts", {})
    addr = log_opts.get("syslog-address", "")
    assert addr == "udp://127.0.0.1:514", (
        f"Expected syslog-address 'udp://127.0.0.1:514', got '{addr}'"
    )


def test_daemon_json_tag():
    """The syslog tag must use the docker/{{.Name}} template."""
    with open(DAEMON_JSON, "r") as f:
        data = json.load(f)
    log_opts = data.get("log-opts", {})
    tag = log_opts.get("tag", "")
    assert tag == "docker/{{.Name}}", (
        f"Expected tag 'docker/{{{{.Name}}}}', got '{tag}'"
    )


# =============================================================================
# 4. Logrotate config: /etc/logrotate.d/docker-containers
# =============================================================================

LOGROTATE_CONF = "/etc/logrotate.d/docker-containers"


def test_logrotate_config_exists():
    """The logrotate config file must exist."""
    assert os.path.isfile(LOGROTATE_CONF), (
        f"Logrotate config not found at {LOGROTATE_CONF}"
    )


def test_logrotate_config_not_empty():
    """The logrotate config must not be empty."""
    assert os.path.getsize(LOGROTATE_CONF) > 0, (
        f"{LOGROTATE_CONF} exists but is empty"
    )


def _read_logrotate_conf():
    with open(LOGROTATE_CONF, "r") as f:
        return f.read()


def test_logrotate_targets_correct_file():
    """Logrotate must target /var/log/docker/containers.log."""
    content = _read_logrotate_conf()
    assert "/var/log/docker/containers.log" in content, (
        "Logrotate config does not target /var/log/docker/containers.log"
    )


def test_logrotate_daily():
    """Logrotate must rotate daily."""
    content = _read_logrotate_conf()
    assert re.search(r'^\s*daily\s*$', content, re.MULTILINE), (
        "'daily' directive not found in logrotate config"
    )


def test_logrotate_rotate_7():
    """Logrotate must keep 7 rotated files."""
    content = _read_logrotate_conf()
    assert re.search(r'^\s*rotate\s+7\s*$', content, re.MULTILINE), (
        "'rotate 7' directive not found in logrotate config"
    )


def test_logrotate_compress():
    """Logrotate must compress rotated files."""
    content = _read_logrotate_conf()
    assert re.search(r'^\s*compress\s*$', content, re.MULTILINE), (
        "'compress' directive not found in logrotate config"
    )


def test_logrotate_delaycompress():
    """Logrotate must use delaycompress."""
    content = _read_logrotate_conf()
    assert re.search(r'^\s*delaycompress\s*$', content, re.MULTILINE), (
        "'delaycompress' directive not found in logrotate config"
    )


def test_logrotate_missingok():
    """Logrotate must handle missing log files gracefully."""
    content = _read_logrotate_conf()
    assert re.search(r'^\s*missingok\s*$', content, re.MULTILINE), (
        "'missingok' directive not found in logrotate config"
    )


def test_logrotate_notifempty():
    """Logrotate must not error on empty log files."""
    content = _read_logrotate_conf()
    assert re.search(r'^\s*notifempty\s*$', content, re.MULTILINE), (
        "'notifempty' directive not found in logrotate config"
    )


def test_logrotate_create_mode():
    """Logrotate must create new files with mode 0640, owner syslog, group adm."""
    content = _read_logrotate_conf()
    # Accept both "create 0640 syslog adm" and "create 640 syslog adm"
    assert re.search(r'^\s*create\s+0?640\s+syslog\s+adm\s*$', content, re.MULTILINE), (
        "'create 0640 syslog adm' directive not found in logrotate config"
    )


def test_logrotate_postrotate():
    """Logrotate must include a postrotate script that reloads rsyslog."""
    content = _read_logrotate_conf()
    assert re.search(r'^\s*postrotate\s*$', content, re.MULTILINE), (
        "'postrotate' block not found in logrotate config"
    )
    assert re.search(r'^\s*endscript\s*$', content, re.MULTILINE), (
        "'endscript' not found — postrotate block is incomplete"
    )
    # The postrotate script must reference rsyslog reload/HUP
    has_rsyslog_reload = (
        "reload rsyslog" in content
        or "rsyslog reload" in content
        or "HUP" in content
        or "rsyslogd.pid" in content
        or "rsyslogd" in content.split("postrotate")[-1].split("endscript")[0]
    )
    assert has_rsyslog_reload, (
        "postrotate script does not reload/HUP rsyslog"
    )


# =============================================================================
# 5. Logrotate syntax validation (dry run)
# =============================================================================

def test_logrotate_syntax_valid():
    """Logrotate config must pass a dry-run syntax check."""
    result = subprocess.run(
        ["logrotate", "-d", LOGROTATE_CONF],
        capture_output=True, text=True
    )
    # logrotate -d outputs to stderr; exit code 0 means valid syntax
    assert result.returncode == 0, (
        f"logrotate dry-run failed (exit {result.returncode}):\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
