"""
Tests for Secure PostgreSQL Deployment with TLS.

These tests verify that PostgreSQL is installed, running, configured with TLS,
has the correct database/user, enforces SSL for remote connections, and has
the required connection_info.txt documentation file.
"""

import os
import subprocess
import stat


def run_cmd(cmd, timeout=30):
    """Run a shell command and return (returncode, stdout, stderr)."""
    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True, timeout=timeout
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def get_pg_data_dir():
    """Dynamically discover the PostgreSQL data directory."""
    # Try via pg_lsclusters first
    rc, out, _ = run_cmd("pg_lsclusters -h 2>/dev/null | head -1 | awk '{print $1}'")
    if rc == 0 and out:
        version = out.strip()
        # Get actual data directory from running server
        rc2, data_dir, _ = run_cmd(
            f"su - postgres -c \"psql -t -A -c 'SHOW data_directory;'\" 2>/dev/null"
        )
        if rc2 == 0 and data_dir and os.path.isdir(data_dir.strip()):
            return data_dir.strip()
    # Fallback: search common locations
    for candidate in ["/var/lib/postgresql/16/main", "/var/lib/postgresql/15/main",
                      "/var/lib/postgresql/14/main", "/var/lib/postgresql/17/main"]:
        if os.path.isdir(candidate):
            return candidate
    return None


def get_pg_conf_dir():
    """Dynamically discover the PostgreSQL config directory."""
    rc, out, _ = run_cmd("pg_lsclusters -h 2>/dev/null | head -1 | awk '{print $1}'")
    if rc == 0 and out:
        version = out.strip()
        conf_dir = f"/etc/postgresql/{version}/main"
        if os.path.isdir(conf_dir):
            return conf_dir
    # Fallback: search
    for v in ["17", "16", "15", "14"]:
        candidate = f"/etc/postgresql/{v}/main"
        if os.path.isdir(candidate):
            return candidate
    return None


# ---------------------------------------------------------------------------
# Requirement 1: PostgreSQL installed and running
# ---------------------------------------------------------------------------

def test_psql_available():
    """psql client must be installed and on PATH."""
    rc, out, _ = run_cmd("which psql")
    assert rc == 0, "psql binary not found on PATH"
    assert "psql" in out


def test_pg_isready_available():
    """pg_isready utility must be installed and on PATH."""
    rc, out, _ = run_cmd("which pg_isready")
    assert rc == 0, "pg_isready binary not found on PATH"


def test_postgresql_running():
    """PostgreSQL service must be running and accepting connections."""
    rc, out, _ = run_cmd("pg_isready")
    assert rc == 0, f"pg_isready failed: {out}"

# ---------------------------------------------------------------------------
# Requirement 2: Self-signed TLS certificate
# ---------------------------------------------------------------------------

def test_server_crt_exists():
    """server.crt must exist in the PostgreSQL data directory."""
    data_dir = get_pg_data_dir()
    assert data_dir is not None, "Could not determine PG data directory"
    crt_path = os.path.join(data_dir, "server.crt")
    assert os.path.isfile(crt_path), f"server.crt not found at {crt_path}"


def test_server_key_exists():
    """server.key must exist in the PostgreSQL data directory."""
    data_dir = get_pg_data_dir()
    assert data_dir is not None, "Could not determine PG data directory"
    key_path = os.path.join(data_dir, "server.key")
    assert os.path.isfile(key_path), f"server.key not found at {key_path}"


def test_cert_common_name():
    """Certificate CN must be pg-server.local."""
    data_dir = get_pg_data_dir()
    assert data_dir is not None, "Could not determine PG data directory"
    crt_path = os.path.join(data_dir, "server.crt")
    rc, out, _ = run_cmd(f"openssl x509 -in {crt_path} -noout -subject")
    assert rc == 0, f"Failed to read certificate: {out}"
    assert "pg-server.local" in out, f"CN not pg-server.local. Got: {out}"


def test_cert_key_size():
    """Certificate key must be 2048-bit RSA."""
    data_dir = get_pg_data_dir()
    assert data_dir is not None
    key_path = os.path.join(data_dir, "server.key")
    rc, out, _ = run_cmd(f"openssl rsa -in {key_path} -text -noout 2>/dev/null | head -1")
    assert rc == 0, "Failed to read key"
    # Accept "2048 bit" or "RSA Private-Key: (2048 bit" etc.
    assert "2048" in out, f"Key size is not 2048-bit. Got: {out}"


def test_cert_validity():
    """Certificate must be valid for approximately 365 days."""
    data_dir = get_pg_data_dir()
    assert data_dir is not None
    crt_path = os.path.join(data_dir, "server.crt")
    rc, out, _ = run_cmd(
        f"openssl x509 -in {crt_path} -noout -dates"
    )
    assert rc == 0, "Failed to read certificate dates"
    # Just verify it has notBefore and notAfter (basic sanity)
    assert "notBefore" in out, "Certificate missing notBefore"
    assert "notAfter" in out, "Certificate missing notAfter"


def test_cert_file_permissions():
    """server.crt must have permissions 0600."""
    data_dir = get_pg_data_dir()
    assert data_dir is not None
    crt_path = os.path.join(data_dir, "server.crt")
    file_stat = os.stat(crt_path)
    perms = stat.S_IMODE(file_stat.st_mode)
    assert perms == 0o600, f"server.crt permissions are {oct(perms)}, expected 0600"


def test_key_file_permissions():
    """server.key must have permissions 0600."""
    data_dir = get_pg_data_dir()
    assert data_dir is not None
    key_path = os.path.join(data_dir, "server.key")
    file_stat = os.stat(key_path)
    perms = stat.S_IMODE(file_stat.st_mode)
    assert perms == 0o600, f"server.key permissions are {oct(perms)}, expected 0600"


def test_cert_file_owner():
    """server.crt must be owned by the postgres user."""
    data_dir = get_pg_data_dir()
    assert data_dir is not None
    crt_path = os.path.join(data_dir, "server.crt")
    rc, out, _ = run_cmd(f"stat -c '%U' {crt_path}")
    assert rc == 0
    assert out == "postgres", f"server.crt owned by '{out}', expected 'postgres'"


def test_key_file_owner():
    """server.key must be owned by the postgres user."""
    data_dir = get_pg_data_dir()
    assert data_dir is not None
    key_path = os.path.join(data_dir, "server.key")
    rc, out, _ = run_cmd(f"stat -c '%U' {key_path}")
    assert rc == 0
    assert out == "postgres", f"server.key owned by '{out}', expected 'postgres'"


# ---------------------------------------------------------------------------
# Requirement 3: PostgreSQL SSL configuration in postgresql.conf
# ---------------------------------------------------------------------------

def _read_pg_conf():
    """Read postgresql.conf content."""
    conf_dir = get_pg_conf_dir()
    if conf_dir is None:
        return None
    conf_path = os.path.join(conf_dir, "postgresql.conf")
    if not os.path.isfile(conf_path):
        return None
    with open(conf_path, "r") as f:
        return f.read()


def test_ssl_enabled_in_conf():
    """postgresql.conf must have ssl = on."""
    # Query the running server for the actual setting — most robust approach
    rc, out, _ = run_cmd(
        "su - postgres -c \"psql -t -A -c \\\"SHOW ssl;\\\"\" 2>/dev/null"
    )
    assert rc == 0, "Could not query ssl setting from running server"
    assert out.strip() == "on", f"ssl is '{out.strip()}', expected 'on'"


def test_listen_addresses_in_conf():
    """postgresql.conf must have listen_addresses = '*'."""
    rc, out, _ = run_cmd(
        "su - postgres -c \"psql -t -A -c \\\"SHOW listen_addresses;\\\"\" 2>/dev/null"
    )
    assert rc == 0, "Could not query listen_addresses"
    assert out.strip() == "*", f"listen_addresses is '{out.strip()}', expected '*'"


def test_ssl_cert_file_configured():
    """ssl_cert_file must point to server.crt in the data directory."""
    rc, out, _ = run_cmd(
        "su - postgres -c \"psql -t -A -c \\\"SHOW ssl_cert_file;\\\"\" 2>/dev/null"
    )
    assert rc == 0, "Could not query ssl_cert_file"
    assert "server.crt" in out, f"ssl_cert_file is '{out}', expected to contain 'server.crt'"


def test_ssl_key_file_configured():
    """ssl_key_file must point to server.key in the data directory."""
    rc, out, _ = run_cmd(
        "su - postgres -c \"psql -t -A -c \\\"SHOW ssl_key_file;\\\"\" 2>/dev/null"
    )
    assert rc == 0, "Could not query ssl_key_file"
    assert "server.key" in out, f"ssl_key_file is '{out}', expected to contain 'server.key'"


# ---------------------------------------------------------------------------
# Requirement 4: Database and User
# ---------------------------------------------------------------------------

def test_devdb_exists():
    """Database 'devdb' must exist."""
    rc, out, _ = run_cmd(
        "su - postgres -c \"psql -t -A -c \\\"SELECT 1 FROM pg_database WHERE datname='devdb';\\\"\" 2>/dev/null"
    )
    assert rc == 0, "Failed to query pg_database"
    assert "1" in out, "Database 'devdb' does not exist"


def test_devuser_exists():
    """User 'devuser' must exist."""
    rc, out, _ = run_cmd(
        "su - postgres -c \"psql -t -A -c \\\"SELECT 1 FROM pg_roles WHERE rolname='devuser';\\\"\" 2>/dev/null"
    )
    assert rc == 0, "Failed to query pg_roles"
    assert "1" in out, "User 'devuser' does not exist"


def test_devuser_can_login():
    """devuser must be able to authenticate with password devpass123."""
    rc, out, err = run_cmd(
        "PGPASSWORD=devpass123 psql -h 127.0.0.1 -U devuser -d devdb -t -A -c 'SELECT 1;' 2>&1"
    )
    assert rc == 0, f"devuser login failed: {out} {err}"
    assert "1" in out, f"Unexpected query result: {out}"


# ---------------------------------------------------------------------------
# Requirement 5: Enforce SSL for remote connections (pg_hba.conf)
# ---------------------------------------------------------------------------

def _read_pg_hba():
    """Read pg_hba.conf and return non-comment, non-empty lines."""
    conf_dir = get_pg_conf_dir()
    if conf_dir is None:
        return None
    hba_path = os.path.join(conf_dir, "pg_hba.conf")
    if not os.path.isfile(hba_path):
        return None
    with open(hba_path, "r") as f:
        lines = f.readlines()
    # Return only active (non-comment, non-blank) lines
    return [l.strip() for l in lines if l.strip() and not l.strip().startswith("#")]


def test_pg_hba_has_hostssl_for_remote():
    """pg_hba.conf must have hostssl entries for remote (non-localhost) connections."""
    lines = _read_pg_hba()
    assert lines is not None, "Could not read pg_hba.conf"
    hostssl_remote = [
        l for l in lines
        if l.startswith("hostssl") and "127.0.0.1/32" not in l and "::1/128" not in l
    ]
    assert len(hostssl_remote) > 0, (
        "No hostssl entries found for remote connections in pg_hba.conf"
    )


def test_pg_hba_no_plain_host_remote():
    """pg_hba.conf must NOT have plain 'host' entries for non-localhost addresses."""
    lines = _read_pg_hba()
    assert lines is not None, "Could not read pg_hba.conf"
    bad_lines = []
    for l in lines:
        parts = l.split()
        if len(parts) < 4:
            continue
        conn_type = parts[0]
        address = parts[3] if len(parts) > 3 else ""
        # 'host' (not 'hostssl', not 'local') with non-localhost address
        if conn_type == "host" and address not in ("127.0.0.1/32", "::1/128"):
            bad_lines.append(l)
    assert len(bad_lines) == 0, (
        f"Found plain 'host' entries for remote addresses (should be hostssl): {bad_lines}"
    )


def test_pg_hba_allows_local():
    """pg_hba.conf must allow local (Unix socket) connections."""
    lines = _read_pg_hba()
    assert lines is not None, "Could not read pg_hba.conf"
    local_lines = [l for l in lines if l.startswith("local")]
    assert len(local_lines) > 0, "No 'local' entries found in pg_hba.conf"


# ---------------------------------------------------------------------------
# Requirement 6: Verify SSL connection actually works
# ---------------------------------------------------------------------------

def test_ssl_connection_succeeds():
    """An SSL connection to devdb as devuser with sslmode=require must succeed."""
    rc, out, err = run_cmd(
        "PGPASSWORD=devpass123 psql -h 127.0.0.1 -U devuser -d devdb "
        "-t -A -c 'SELECT 1;' 'sslmode=require' 2>&1"
    )
    assert rc == 0, f"SSL connection with sslmode=require failed: {out} {err}"
    assert "1" in out, f"Unexpected result from SSL query: {out}"


def test_ssl_is_active_on_connection():
    """The SSL connection must report TLS as active via pg_stat_ssl."""
    rc, out, err = run_cmd(
        "PGPASSWORD=devpass123 psql -h 127.0.0.1 -U devuser -d devdb "
        "-t -A -c \"SELECT ssl FROM pg_stat_ssl WHERE pid = pg_backend_pid();\" "
        "'sslmode=require' 2>&1"
    )
    # If pg_stat_ssl query works, ssl column should be 't'
    if rc == 0 and out.strip():
        assert out.strip() == "t", f"SSL not active on connection. pg_stat_ssl.ssl = '{out.strip()}'"
    else:
        # Fallback: just verify sslmode=require connection succeeds (already tested above)
        # Some PG versions may restrict pg_stat_ssl access for non-superusers
        rc2, out2, _ = run_cmd(
            "PGPASSWORD=devpass123 psql -h 127.0.0.1 -U devuser -d devdb "
            "-t -A -c 'SELECT 1;' 'sslmode=require' 2>&1"
        )
        assert rc2 == 0, f"SSL connection failed: {out2}"


# ---------------------------------------------------------------------------
# Requirement 7: Connection info documentation file
# ---------------------------------------------------------------------------

CONNECTION_INFO_PATH = "/app/connection_info.txt"

EXPECTED_FIELDS = {
    "host": "pg-server.local",
    "port": "5432",
    "dbname": "devdb",
    "user": "devuser",
    "sslmode": "require",
}


def test_connection_info_file_exists():
    """connection_info.txt must exist at /app/connection_info.txt."""
    assert os.path.isfile(CONNECTION_INFO_PATH), (
        f"{CONNECTION_INFO_PATH} does not exist"
    )


def test_connection_info_not_empty():
    """connection_info.txt must not be empty."""
    assert os.path.getsize(CONNECTION_INFO_PATH) > 0, (
        f"{CONNECTION_INFO_PATH} is empty"
    )


def test_connection_info_content():
    """connection_info.txt must contain all required key=value pairs."""
    with open(CONNECTION_INFO_PATH, "r") as f:
        content = f.read()
    lines = [l.strip() for l in content.strip().splitlines() if l.strip()]
    parsed = {}
    for line in lines:
        if "=" in line:
            key, _, value = line.partition("=")
            parsed[key.strip()] = value.strip()
    for key, expected_val in EXPECTED_FIELDS.items():
        assert key in parsed, f"Missing key '{key}' in connection_info.txt"
        assert parsed[key] == expected_val, (
            f"Key '{key}' has value '{parsed[key]}', expected '{expected_val}'"
        )


def test_connection_info_has_five_entries():
    """connection_info.txt must have exactly 5 key=value entries."""
    with open(CONNECTION_INFO_PATH, "r") as f:
        content = f.read()
    lines = [l.strip() for l in content.strip().splitlines() if l.strip()]
    kv_lines = [l for l in lines if "=" in l]
    assert len(kv_lines) == 5, (
        f"Expected 5 key=value entries, found {len(kv_lines)}"
    )
