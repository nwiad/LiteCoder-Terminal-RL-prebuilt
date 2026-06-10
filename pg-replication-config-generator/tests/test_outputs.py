"""
Tests for PostgreSQL Streaming Replication Configuration Generator.

Validates all 8 output files under /app/output/ for correctness,
completeness, and adherence to the instruction requirements.
"""

import os
import json
import re
import stat

OUTPUT_DIR = "/app/output"

REQUIRED_FILES = [
    "primary_postgresql.conf",
    "primary_pg_hba.conf",
    "standby1_postgresql.conf",
    "standby2_postgresql.conf",
    "setup_primary.sh",
    "setup_standby.sh",
    "monitor.sh",
    "cluster_info.json",
]


def _read_file(filename):
    """Read a file from the output directory, return its content."""
    path = os.path.join(OUTPUT_DIR, filename)
    assert os.path.isfile(path), f"File not found: {path}"
    with open(path, "r") as f:
        content = f.read()
    assert len(content.strip()) > 0, f"File is empty: {path}"
    return content


def _parse_pg_conf(content):
    """
    Parse PostgreSQL config content into a dict of key -> value.
    Handles 'key = value' lines, ignoring comments and blank lines.
    """
    settings = {}
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        # Match key = value or key=value
        m = re.match(r"^(\w+)\s*=\s*(.+)$", stripped)
        if m:
            key = m.group(1).strip()
            val = m.group(2).strip().rstrip(";")
            # Remove surrounding quotes if present
            if (val.startswith("'") and val.endswith("'")) or \
               (val.startswith('"') and val.endswith('"')):
                val = val[1:-1]
            settings[key] = val
    return settings


# ============================================================
# Test: All required files exist and are non-empty
# ============================================================
class TestFileExistence:
    """All 8 required files must exist and be non-empty."""

    def test_all_files_exist(self):
        for fname in REQUIRED_FILES:
            path = os.path.join(OUTPUT_DIR, fname)
            assert os.path.isfile(path), f"Missing required file: {fname}"

    def test_all_files_non_empty(self):
        for fname in REQUIRED_FILES:
            content = _read_file(fname)
            assert len(content.strip()) > 10, \
                f"File {fname} appears to be trivially small or empty"

    def test_shell_scripts_executable(self):
        """All .sh files should be executable."""
        sh_files = [f for f in REQUIRED_FILES if f.endswith(".sh")]
        for fname in sh_files:
            path = os.path.join(OUTPUT_DIR, fname)
            assert os.path.isfile(path), f"Missing: {fname}"
            mode = os.stat(path).st_mode
            assert mode & stat.S_IXUSR, \
                f"{fname} is not executable (missing user execute bit)"


# ============================================================
# Test: primary_postgresql.conf
# ============================================================
class TestPrimaryPostgresqlConf:

    def _get_settings(self):
        content = _read_file("primary_postgresql.conf")
        return _parse_pg_conf(content), content

    def test_listen_addresses(self):
        settings, _ = self._get_settings()
        assert "listen_addresses" in settings, "Missing listen_addresses"
        assert settings["listen_addresses"] == "*", \
            f"listen_addresses should be '*', got '{settings['listen_addresses']}'"

    def test_wal_level(self):
        settings, _ = self._get_settings()
        assert "wal_level" in settings, "Missing wal_level"
        assert settings["wal_level"] == "replica", \
            f"wal_level should be 'replica', got '{settings['wal_level']}'"

    def test_max_wal_senders(self):
        settings, _ = self._get_settings()
        assert "max_wal_senders" in settings, "Missing max_wal_senders"
        val = int(settings["max_wal_senders"])
        assert val >= 10, f"max_wal_senders should be >= 10, got {val}"

    def test_max_replication_slots(self):
        settings, _ = self._get_settings()
        assert "max_replication_slots" in settings, "Missing max_replication_slots"
        val = int(settings["max_replication_slots"])
        assert val >= 10, f"max_replication_slots should be >= 10, got {val}"

    def test_hot_standby(self):
        settings, _ = self._get_settings()
        assert "hot_standby" in settings, "Missing hot_standby"
        assert settings["hot_standby"] == "on", \
            f"hot_standby should be 'on', got '{settings['hot_standby']}'"

    def test_wal_keep_size(self):
        settings, _ = self._get_settings()
        assert "wal_keep_size" in settings, "Missing wal_keep_size"
        raw = settings["wal_keep_size"].upper().strip()
        # Accept values like 1GB, 2GB, 1024MB, etc. — must be >= 1GB
        m = re.match(r"^(\d+)\s*(GB|MB|TB)$", raw)
        assert m, f"Cannot parse wal_keep_size: {raw}"
        num, unit = int(m.group(1)), m.group(2)
        mb_val = num * (1024 if unit == "GB" else 1 if unit == "MB" else 1024 * 1024)
        assert mb_val >= 1024, f"wal_keep_size should be >= 1GB, got {raw}"

    def test_synchronous_standby_names(self):
        settings, content = self._get_settings()
        assert "synchronous_standby_names" in settings, \
            "Missing synchronous_standby_names"
        val = settings["synchronous_standby_names"]
        # Must reference both standbys — look for standby1 and standby2 identifiers
        assert re.search(r"standby1|pg_standby1", val, re.IGNORECASE), \
            f"synchronous_standby_names must reference standby1, got: {val}"
        assert re.search(r"standby2|pg_standby2", val, re.IGNORECASE), \
            f"synchronous_standby_names must reference standby2, got: {val}"

    def test_archive_mode(self):
        settings, _ = self._get_settings()
        assert "archive_mode" in settings, "Missing archive_mode"
        assert settings["archive_mode"] == "on", \
            f"archive_mode should be 'on', got '{settings['archive_mode']}'"

    def test_archive_command(self):
        settings, _ = self._get_settings()
        assert "archive_command" in settings, "Missing archive_command"
        assert len(settings["archive_command"].strip()) > 0, \
            "archive_command must be non-empty"


# ============================================================
# Test: primary_pg_hba.conf
# ============================================================
class TestPrimaryPgHbaConf:

    def _get_content(self):
        return _read_file("primary_pg_hba.conf")

    def _get_active_lines(self):
        """Return non-comment, non-blank lines."""
        content = self._get_content()
        lines = []
        for line in content.splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                lines.append(stripped)
        return lines

    def test_has_replication_entry(self):
        """Must have a replication entry for user replicator from 10.0.1.0/24."""
        lines = self._get_active_lines()
        found = False
        for line in lines:
            if "replication" in line and "replicator" in line and "10.0.1.0/24" in line:
                found = True
                break
        assert found, \
            "Missing replication entry for user 'replicator' from subnet 10.0.1.0/24"

    def test_replication_auth_method(self):
        """Replication entry must use md5 or scram-sha-256."""
        lines = self._get_active_lines()
        found_valid = False
        for line in lines:
            if "replication" in line and "replicator" in line:
                if "scram-sha-256" in line or "md5" in line:
                    found_valid = True
                    break
        assert found_valid, \
            "Replication entry must use 'md5' or 'scram-sha-256' authentication"

    def test_has_local_entries(self):
        """Must have at least one local access entry."""
        lines = self._get_active_lines()
        found_local = any(line.startswith("local") for line in lines)
        assert found_local, "Missing local access entries in pg_hba.conf"

    def test_has_host_entries(self):
        """Must have at least one host entry (beyond replication)."""
        lines = self._get_active_lines()
        host_lines = [l for l in lines if l.startswith("host")]
        assert len(host_lines) >= 1, "Missing host entries in pg_hba.conf"


# ============================================================
# Test: standby1_postgresql.conf
# ============================================================
class TestStandby1Conf:

    def _get_settings(self):
        content = _read_file("standby1_postgresql.conf")
        return _parse_pg_conf(content), content

    def test_hot_standby_on(self):
        settings, _ = self._get_settings()
        assert "hot_standby" in settings, "Missing hot_standby in standby1 conf"
        assert settings["hot_standby"] == "on"

    def test_primary_conninfo_host(self):
        settings, _ = self._get_settings()
        assert "primary_conninfo" in settings, "Missing primary_conninfo in standby1"
        conninfo = settings["primary_conninfo"]
        assert "10.0.1.10" in conninfo, \
            f"primary_conninfo must contain host 10.0.1.10, got: {conninfo}"

    def test_primary_conninfo_port(self):
        settings, _ = self._get_settings()
        conninfo = settings.get("primary_conninfo", "")
        assert "5432" in conninfo, \
            f"primary_conninfo must contain port 5432, got: {conninfo}"

    def test_primary_conninfo_user(self):
        settings, _ = self._get_settings()
        conninfo = settings.get("primary_conninfo", "")
        assert "replicator" in conninfo, \
            f"primary_conninfo must contain user replicator, got: {conninfo}"

    def test_primary_conninfo_password(self):
        settings, _ = self._get_settings()
        conninfo = settings.get("primary_conninfo", "")
        # Must contain a password field (any non-empty value)
        assert re.search(r"password\s*=\s*\S+", conninfo), \
            f"primary_conninfo must contain a password, got: {conninfo}"

    def test_primary_slot_name(self):
        settings, _ = self._get_settings()
        assert "primary_slot_name" in settings, "Missing primary_slot_name in standby1"
        assert settings["primary_slot_name"] == "standby1_slot", \
            f"primary_slot_name should be 'standby1_slot', got '{settings['primary_slot_name']}'"


# ============================================================
# Test: standby2_postgresql.conf
# ============================================================
class TestStandby2Conf:

    def _get_settings(self):
        content = _read_file("standby2_postgresql.conf")
        return _parse_pg_conf(content), content

    def test_hot_standby_on(self):
        settings, _ = self._get_settings()
        assert "hot_standby" in settings, "Missing hot_standby in standby2 conf"
        assert settings["hot_standby"] == "on"

    def test_primary_conninfo_host(self):
        settings, _ = self._get_settings()
        assert "primary_conninfo" in settings, "Missing primary_conninfo in standby2"
        conninfo = settings["primary_conninfo"]
        assert "10.0.1.10" in conninfo, \
            f"primary_conninfo must contain host 10.0.1.10, got: {conninfo}"

    def test_primary_conninfo_port(self):
        settings, _ = self._get_settings()
        conninfo = settings.get("primary_conninfo", "")
        assert "5432" in conninfo

    def test_primary_conninfo_user(self):
        settings, _ = self._get_settings()
        conninfo = settings.get("primary_conninfo", "")
        assert "replicator" in conninfo

    def test_primary_conninfo_password(self):
        settings, _ = self._get_settings()
        conninfo = settings.get("primary_conninfo", "")
        assert re.search(r"password\s*=\s*\S+", conninfo), \
            "primary_conninfo must contain a password"

    def test_primary_slot_name(self):
        settings, _ = self._get_settings()
        assert "primary_slot_name" in settings, "Missing primary_slot_name in standby2"
        assert settings["primary_slot_name"] == "standby2_slot", \
            f"primary_slot_name should be 'standby2_slot', got '{settings['primary_slot_name']}'"

    def test_standby2_differs_from_standby1(self):
        """Standby2 must have different slot and application_name from standby1."""
        s1_content = _read_file("standby1_postgresql.conf")
        s2_content = _read_file("standby2_postgresql.conf")
        s1 = _parse_pg_conf(s1_content)
        s2 = _parse_pg_conf(s2_content)
        assert s1.get("primary_slot_name") != s2.get("primary_slot_name"), \
            "standby1 and standby2 must have different primary_slot_name"


# ============================================================
# Test: setup_primary.sh
# ============================================================
class TestSetupPrimarySh:

    def _get_content(self):
        return _read_file("setup_primary.sh")

    def test_shebang(self):
        content = self._get_content()
        assert content.strip().startswith("#!/bin/bash"), \
            "setup_primary.sh must start with #!/bin/bash"

    def test_creates_replicator_role(self):
        """Must create the replicator role with REPLICATION and LOGIN."""
        content = self._get_content().lower()
        assert "replicator" in content, \
            "setup_primary.sh must reference the replicator user"
        # Check for CREATE ROLE or CREATE USER with REPLICATION
        assert re.search(r"create\s+(role|user)\s+replicator", content), \
            "setup_primary.sh must contain CREATE ROLE/USER replicator"
        assert "replication" in content, \
            "setup_primary.sh must grant REPLICATION privilege"
        assert "login" in content, \
            "setup_primary.sh must grant LOGIN privilege"

    def test_creates_standby1_slot(self):
        content = self._get_content()
        assert "standby1_slot" in content, \
            "setup_primary.sh must create standby1_slot"
        assert "pg_create_physical_replication_slot" in content, \
            "setup_primary.sh must use pg_create_physical_replication_slot"

    def test_creates_standby2_slot(self):
        content = self._get_content()
        assert "standby2_slot" in content, \
            "setup_primary.sh must create standby2_slot"

    def test_restarts_or_reloads_pg(self):
        """Must include a command to restart or reload PostgreSQL."""
        content = self._get_content().lower()
        has_restart = "restart" in content and "postgresql" in content
        has_reload = "reload" in content and "postgresql" in content
        has_pg_ctl = "pg_ctl" in content and ("restart" in content or "reload" in content)
        assert has_restart or has_reload or has_pg_ctl, \
            "setup_primary.sh must restart or reload PostgreSQL"

    def test_uses_psql(self):
        """Must use psql or similar to run SQL commands."""
        content = self._get_content()
        assert "psql" in content, \
            "setup_primary.sh must use psql to execute SQL commands"


# ============================================================
# Test: setup_standby.sh
# ============================================================
class TestSetupStandbySh:

    def _get_content(self):
        return _read_file("setup_standby.sh")

    def test_shebang(self):
        content = self._get_content()
        assert content.strip().startswith("#!/bin/bash"), \
            "setup_standby.sh must start with #!/bin/bash"

    def test_accepts_argument(self):
        """Must accept standby number as a command-line argument ($1)."""
        content = self._get_content()
        assert "$1" in content, \
            "setup_standby.sh must accept standby number via $1"

    def test_uses_pg_basebackup(self):
        content = self._get_content()
        assert "pg_basebackup" in content, \
            "setup_standby.sh must use pg_basebackup"

    def test_pg_basebackup_host(self):
        content = self._get_content()
        assert "10.0.1.10" in content, \
            "setup_standby.sh pg_basebackup must target primary host 10.0.1.10"

    def test_pg_basebackup_user(self):
        content = self._get_content()
        assert "replicator" in content, \
            "setup_standby.sh pg_basebackup must use replicator user"

    def test_creates_standby_signal(self):
        content = self._get_content()
        assert "standby.signal" in content, \
            "setup_standby.sh must create standby.signal file"

    def test_starts_postgresql(self):
        content = self._get_content().lower()
        has_start = ("start" in content and "postgresql" in content)
        has_pg_ctl = "pg_ctl" in content and "start" in content
        assert has_start or has_pg_ctl, \
            "setup_standby.sh must include a command to start PostgreSQL"

    def test_references_slot_name(self):
        """Must reference slot name dynamically based on argument."""
        content = self._get_content()
        # Should contain standby slot reference — either dynamic or both names
        has_dynamic = re.search(r"standby\$\{?\d?\}?.*slot|slot.*standby", content)
        has_both = "standby1_slot" in content or "standby2_slot" in content
        # Or constructs slot name from $1
        has_constructed = re.search(r"standby.*\$1.*slot|\$\{?1\}?", content)
        assert has_dynamic or has_both or has_constructed, \
            "setup_standby.sh must reference the appropriate replication slot"


# ============================================================
# Test: monitor.sh
# ============================================================
class TestMonitorSh:

    def _get_content(self):
        return _read_file("monitor.sh")

    def test_shebang(self):
        content = self._get_content()
        assert content.strip().startswith("#!/bin/bash"), \
            "monitor.sh must start with #!/bin/bash"

    def test_queries_pg_stat_replication(self):
        content = self._get_content()
        assert "pg_stat_replication" in content, \
            "monitor.sh must query pg_stat_replication"

    def test_checks_replication_lag(self):
        """Must check replication lag via pg_wal_lsn_diff or replay_lag."""
        content = self._get_content()
        has_lsn_diff = "pg_wal_lsn_diff" in content
        has_replay_lag = "replay_lag" in content
        has_write_lag = "write_lag" in content
        has_flush_lag = "flush_lag" in content
        assert has_lsn_diff or has_replay_lag or has_write_lag or has_flush_lag, \
            "monitor.sh must check replication lag (pg_wal_lsn_diff or lag columns)"

    def test_outputs_to_stdout(self):
        """Script should produce output (echo/print/psql output)."""
        content = self._get_content()
        has_echo = "echo" in content
        has_psql = "psql" in content
        assert has_echo or has_psql, \
            "monitor.sh must output results to stdout"


# ============================================================
# Test: cluster_info.json
# ============================================================
class TestClusterInfoJson:

    def _get_data(self):
        content = _read_file("cluster_info.json")
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            raise AssertionError(f"cluster_info.json is not valid JSON: {e}")
        return data

    def test_valid_json(self):
        self._get_data()

    def test_postgresql_version(self):
        data = self._get_data()
        assert "postgresql_version" in data, "Missing postgresql_version"
        assert data["postgresql_version"] == 15, \
            f"postgresql_version must be 15, got {data['postgresql_version']}"

    def test_has_cluster_name(self):
        data = self._get_data()
        assert "cluster_name" in data, "Missing cluster_name"
        assert isinstance(data["cluster_name"], str) and len(data["cluster_name"]) > 0, \
            "cluster_name must be a non-empty string"

    def test_nodes_count(self):
        data = self._get_data()
        assert "nodes" in data, "Missing nodes array"
        assert isinstance(data["nodes"], list), "nodes must be a list"
        assert len(data["nodes"]) == 3, \
            f"nodes must contain exactly 3 entries, got {len(data['nodes'])}"

    def test_primary_node(self):
        data = self._get_data()
        nodes = data.get("nodes", [])
        primaries = [n for n in nodes if n.get("role") == "primary"]
        assert len(primaries) == 1, "Must have exactly 1 primary node"
        p = primaries[0]
        assert p.get("hostname") == "pg-primary", \
            f"Primary hostname must be 'pg-primary', got '{p.get('hostname')}'"
        assert p.get("ip") == "10.0.1.10", \
            f"Primary IP must be '10.0.1.10', got '{p.get('ip')}'"
        assert p.get("port") == 5432, \
            f"Primary port must be 5432, got {p.get('port')}"

    def test_standby_nodes(self):
        data = self._get_data()
        nodes = data.get("nodes", [])
        standbys = [n for n in nodes if n.get("role") == "standby"]
        assert len(standbys) == 2, \
            f"Must have exactly 2 standby nodes, got {len(standbys)}"

        # Collect hostnames and IPs
        hostnames = sorted([s.get("hostname") for s in standbys])
        ips = sorted([s.get("ip") for s in standbys])

        assert "pg-standby1" in hostnames, "Missing standby node pg-standby1"
        assert "pg-standby2" in hostnames, "Missing standby node pg-standby2"
        assert "10.0.1.11" in ips, "Missing standby IP 10.0.1.11"
        assert "10.0.1.12" in ips, "Missing standby IP 10.0.1.12"

        for s in standbys:
            assert s.get("port") == 5432, \
                f"Standby port must be 5432, got {s.get('port')}"

    def test_replication_user(self):
        data = self._get_data()
        assert "replication_user" in data, "Missing replication_user"
        assert data["replication_user"] == "replicator", \
            f"replication_user must be 'replicator', got '{data['replication_user']}'"

    def test_replication_slots(self):
        data = self._get_data()
        assert "replication_slots" in data, "Missing replication_slots"
        slots = data["replication_slots"]
        assert isinstance(slots, list), "replication_slots must be a list"
        assert "standby1_slot" in slots, "Missing standby1_slot in replication_slots"
        assert "standby2_slot" in slots, "Missing standby2_slot in replication_slots"
        assert len(slots) == 2, \
            f"replication_slots must have exactly 2 entries, got {len(slots)}"
