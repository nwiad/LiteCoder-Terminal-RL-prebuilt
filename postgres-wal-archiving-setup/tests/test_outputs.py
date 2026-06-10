"""
Tests for PostgreSQL WAL Archiving Setup task.
Validates all 9 requirements from instruction.md.
"""

import os
import subprocess
import stat
import re


def run_cmd(cmd, timeout=30):
    """Run a shell command and return (returncode, stdout, stderr)."""
    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True, timeout=timeout
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def psql_query(query, db="postgres"):
    """Run a psql query as the postgres user and return stdout."""
    cmd = f'su - postgres -c "psql -t -A -d {db} -c \\"{query}\\""'
    rc, out, err = run_cmd(cmd)
    return out


# ===========================================================================
# Requirement 1: PostgreSQL is installed and running
# ===========================================================================

class TestPostgresRunning:
    def test_pg_isready(self):
        """PostgreSQL must be running and accepting connections."""
        rc, out, _ = run_cmd("su - postgres -c 'pg_isready'")
        assert rc == 0, f"pg_isready failed: {out}"

    def test_psql_accessible(self):
        """Can execute a simple query via psql."""
        result = psql_query("SELECT 1;")
        assert "1" in result, f"Expected '1' in psql output, got: {result}"

    def test_pg_version_14_or_later(self):
        """PostgreSQL version must be 14 or later."""
        result = psql_query("SHOW server_version;")
        # Extract major version number
        match = re.search(r"(\d+)", result)
        assert match, f"Could not parse PG version from: {result}"
        major = int(match.group(1))
        assert major >= 14, f"PostgreSQL version {major} is less than 14"


# ===========================================================================
# Requirement 2: Backup user and SSH key
# ===========================================================================
class TestBackupUser:
    def test_backupuser_exists(self):
        """System user 'backupuser' must exist."""
        rc, out, _ = run_cmd("id backupuser")
        assert rc == 0, f"backupuser does not exist: {out}"

    def test_ssh_private_key_exists(self):
        """SSH private key must exist (Ed25519 or RSA)."""
        ed25519 = os.path.isfile("/home/backupuser/.ssh/id_ed25519")
        rsa = os.path.isfile("/home/backupuser/.ssh/id_rsa")
        assert ed25519 or rsa, "No SSH private key found at id_ed25519 or id_rsa"

    def test_ssh_private_key_permissions(self):
        """SSH private key must have permissions 600."""
        for keyfile in ["/home/backupuser/.ssh/id_ed25519", "/home/backupuser/.ssh/id_rsa"]:
            if os.path.isfile(keyfile):
                mode = oct(os.stat(keyfile).st_mode & 0o777)
                assert mode == "0o600", f"{keyfile} has permissions {mode}, expected 0o600"
                return
        assert False, "No SSH private key found to check permissions"

    def test_ssh_public_key_exists(self):
        """SSH public key must exist alongside the private key."""
        ed25519_pub = os.path.isfile("/home/backupuser/.ssh/id_ed25519.pub")
        rsa_pub = os.path.isfile("/home/backupuser/.ssh/id_rsa.pub")
        assert ed25519_pub or rsa_pub, "No SSH public key found"

    def test_authorized_keys_configured(self):
        """authorized_keys must contain the public key for passwordless SSH."""
        auth_keys_path = "/home/backupuser/.ssh/authorized_keys"
        assert os.path.isfile(auth_keys_path), "authorized_keys file missing"
        with open(auth_keys_path, "r") as f:
            content = f.read().strip()
        assert len(content) > 0, "authorized_keys is empty"
        # Verify it contains a valid key type
        assert any(kt in content for kt in ["ssh-ed25519", "ssh-rsa"]), \
            "authorized_keys does not contain a recognized SSH key type"


# ===========================================================================
# Requirement 3: Archive directory
# ===========================================================================

class TestArchiveDirectory:
    ARCHIVE_DIR = "/var/lib/postgresql/wal_archive"

    def test_archive_dir_exists(self):
        """Archive directory must exist."""
        assert os.path.isdir(self.ARCHIVE_DIR), f"{self.ARCHIVE_DIR} does not exist"

    def test_archive_dir_owner(self):
        """Archive directory must be owned by postgres."""
        rc, out, _ = run_cmd(f"stat -c '%U' {self.ARCHIVE_DIR}")
        assert out == "postgres", f"Archive dir owned by '{out}', expected 'postgres'"

    def test_archive_dir_permissions(self):
        """Archive directory must have permissions 700."""
        mode = oct(os.stat(self.ARCHIVE_DIR).st_mode & 0o777)
        assert mode == "0o700", f"Archive dir has permissions {mode}, expected 0o700"


# ===========================================================================
# Requirement 4: PostgreSQL WAL archiving configuration
# ===========================================================================
class TestWALConfig:
    def test_wal_level(self):
        """wal_level must be 'replica' or 'logical'."""
        result = psql_query("SELECT setting FROM pg_settings WHERE name='wal_level';")
        assert result in ("replica", "logical"), \
            f"wal_level is '{result}', expected 'replica' or 'logical'"

    def test_archive_mode(self):
        """archive_mode must be 'on'."""
        result = psql_query("SELECT setting FROM pg_settings WHERE name='archive_mode';")
        assert result == "on", f"archive_mode is '{result}', expected 'on'"

    def test_archive_command_has_placeholders(self):
        """archive_command must contain %p and %f placeholders."""
        result = psql_query("SELECT setting FROM pg_settings WHERE name='archive_command';")
        assert "%p" in result, f"archive_command missing %p: {result}"
        assert "%f" in result, f"archive_command missing %f: {result}"

    def test_archive_command_references_archive_dir(self):
        """archive_command must reference the WAL archive directory."""
        result = psql_query("SELECT setting FROM pg_settings WHERE name='archive_command';")
        assert "/var/lib/postgresql/wal_archive" in result or "wal_archive" in result, \
            f"archive_command does not reference wal_archive: {result}"

    def test_max_wal_senders(self):
        """max_wal_senders must be at least 3."""
        result = psql_query("SELECT setting FROM pg_settings WHERE name='max_wal_senders';")
        assert result.isdigit(), f"max_wal_senders is not a number: {result}"
        assert int(result) >= 3, f"max_wal_senders is {result}, expected >= 3"


# ===========================================================================
# Requirement 5: Archive command script
# ===========================================================================

class TestArchiveScript:
    SCRIPT_PATH = "/usr/local/bin/archive_wal.sh"

    def test_script_exists(self):
        """archive_wal.sh must exist."""
        assert os.path.isfile(self.SCRIPT_PATH), f"{self.SCRIPT_PATH} does not exist"

    def test_script_is_executable(self):
        """archive_wal.sh must be executable."""
        assert os.path.isfile(self.SCRIPT_PATH), f"{self.SCRIPT_PATH} does not exist"
        mode = os.stat(self.SCRIPT_PATH).st_mode
        assert mode & stat.S_IXUSR, f"{self.SCRIPT_PATH} is not executable by owner"

    def test_script_owned_by_postgres(self):
        """archive_wal.sh must be owned by postgres."""
        rc, out, _ = run_cmd(f"stat -c '%U' {self.SCRIPT_PATH}")
        assert out == "postgres", f"archive_wal.sh owned by '{out}', expected 'postgres'"

    def test_script_references_archive_dir(self):
        """archive_wal.sh must reference the archive directory."""
        with open(self.SCRIPT_PATH, "r") as f:
            content = f.read()
        assert "/var/lib/postgresql/wal_archive" in content, \
            "archive_wal.sh does not reference /var/lib/postgresql/wal_archive"

    def test_script_has_error_handling(self):
        """archive_wal.sh must include basic error handling (exit with non-zero)."""
        with open(self.SCRIPT_PATH, "r") as f:
            content = f.read()
        # Check for exit with non-zero code pattern
        has_error_exit = ("exit 1" in content or "set -e" in content
                          or "exit $?" in content or "|| exit" in content)
        assert has_error_exit, "archive_wal.sh lacks error handling (no exit 1/set -e found)"

    def test_script_is_not_empty(self):
        """archive_wal.sh must not be empty."""
        size = os.path.getsize(self.SCRIPT_PATH)
        assert size > 50, f"archive_wal.sh is suspiciously small ({size} bytes)"


# ===========================================================================
# Requirement 6: WAL files archived
# ===========================================================================

class TestWALArchived:
    ARCHIVE_DIR = "/var/lib/postgresql/wal_archive"

    def test_wal_files_present(self):
        """At least one WAL file must be in the archive directory."""
        if not os.path.isdir(self.ARCHIVE_DIR):
            assert False, f"{self.ARCHIVE_DIR} does not exist"
        files = os.listdir(self.ARCHIVE_DIR)
        assert len(files) >= 1, \
            f"No WAL files found in {self.ARCHIVE_DIR}. Contents: {files}"

    def test_wal_files_nonzero_size(self):
        """Archived WAL files must have non-zero size."""
        files = os.listdir(self.ARCHIVE_DIR)
        assert len(files) > 0, "No WAL files to check"
        for f in files:
            fpath = os.path.join(self.ARCHIVE_DIR, f)
            if os.path.isfile(fpath):
                size = os.path.getsize(fpath)
                assert size > 0, f"WAL file {f} has zero size"
                return  # At least one valid file is enough
        assert False, "No regular files found in archive directory"


# ===========================================================================
# Requirement 7: Test database ecommerce_test
# ===========================================================================
class TestEcommerceDatabase:
    DB = "ecommerce_test"

    def test_database_exists(self):
        """Database 'ecommerce_test' must exist."""
        result = psql_query("SELECT datname FROM pg_database WHERE datname='ecommerce_test';")
        assert "ecommerce_test" in result, f"Database ecommerce_test not found: {result}"

    def test_orders_table_exists(self):
        """Table 'orders' must exist in ecommerce_test."""
        result = psql_query(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema='public' AND table_name='orders';",
            db=self.DB,
        )
        assert "orders" in result, f"Table 'orders' not found: {result}"

    def test_orders_has_id_column(self):
        """orders table must have an 'id' column."""
        result = psql_query(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='orders' AND column_name='id';",
            db=self.DB,
        )
        assert "id" in result, "Column 'id' not found in orders table"

    def test_orders_has_product_name_column(self):
        """orders table must have a 'product_name' column."""
        result = psql_query(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='orders' AND column_name='product_name';",
            db=self.DB,
        )
        assert "product_name" in result, "Column 'product_name' not found in orders table"

    def test_orders_has_quantity_column(self):
        """orders table must have a 'quantity' column."""
        result = psql_query(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='orders' AND column_name='quantity';",
            db=self.DB,
        )
        assert "quantity" in result, "Column 'quantity' not found in orders table"

    def test_orders_has_created_at_column(self):
        """orders table must have a 'created_at' column."""
        result = psql_query(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='orders' AND column_name='created_at';",
            db=self.DB,
        )
        assert "created_at" in result, "Column 'created_at' not found in orders table"

    def test_orders_has_at_least_3_rows(self):
        """orders table must have at least 3 rows."""
        result = psql_query("SELECT count(*) FROM orders;", db=self.DB)
        assert result.isdigit(), f"Unexpected count result: {result}"
        assert int(result) >= 3, f"orders has {result} rows, expected >= 3"

    def test_orders_id_is_primary_key(self):
        """orders.id should be a primary key (serial)."""
        result = psql_query(
            "SELECT constraint_type FROM information_schema.table_constraints "
            "WHERE table_name='orders' AND constraint_type='PRIMARY KEY';",
            db=self.DB,
        )
        assert "PRIMARY KEY" in result, "No PRIMARY KEY constraint found on orders table"

    def test_orders_data_is_meaningful(self):
        """orders rows must have non-null product_name and positive quantity."""
        result = psql_query(
            "SELECT count(*) FROM orders WHERE product_name IS NOT NULL "
            "AND length(product_name) > 0 AND quantity > 0;",
            db=self.DB,
        )
        assert result.isdigit() and int(result) >= 3, \
            f"Expected >= 3 valid rows with non-null product_name and quantity > 0, got {result}"


# ===========================================================================
# Requirement 8: Backup and recovery documentation
# ===========================================================================

class TestDocumentation:
    DOC_PATH = "/app/backup_recovery_procedures.txt"

    def test_doc_file_exists(self):
        """backup_recovery_procedures.txt must exist."""
        assert os.path.isfile(self.DOC_PATH), f"{self.DOC_PATH} does not exist"

    def test_doc_is_nonempty(self):
        """Documentation file must be non-empty."""
        size = os.path.getsize(self.DOC_PATH)
        assert size > 0, "Documentation file is empty"

    def test_doc_has_at_least_10_lines(self):
        """Documentation must have at least 10 lines."""
        with open(self.DOC_PATH, "r") as f:
            lines = f.readlines()
        assert len(lines) >= 10, f"Documentation has {len(lines)} lines, expected >= 10"

    def test_doc_mentions_base_backup(self):
        """Documentation must describe how to perform a base backup."""
        with open(self.DOC_PATH, "r") as f:
            content = f.read().lower()
        assert "base backup" in content or "pg_basebackup" in content or "base_backup" in content, \
            "Documentation does not mention base backup procedures"

    def test_doc_mentions_recovery(self):
        """Documentation must describe point-in-time recovery."""
        with open(self.DOC_PATH, "r") as f:
            content = f.read().lower()
        has_recovery = ("recovery" in content or "restore" in content or "pitr" in content)
        assert has_recovery, "Documentation does not mention recovery/restore procedures"


# ===========================================================================
# Requirement 9: WAL monitoring cron job and script
# ===========================================================================
class TestMonitoringCron:
    MONITOR_SCRIPT = "/usr/local/bin/monitor_wal.sh"
    LOG_FILE = "/var/log/wal_monitor.log"

    def test_monitor_script_exists(self):
        """monitor_wal.sh must exist."""
        assert os.path.isfile(self.MONITOR_SCRIPT), f"{self.MONITOR_SCRIPT} does not exist"

    def test_monitor_script_is_executable(self):
        """monitor_wal.sh must be executable."""
        assert os.path.isfile(self.MONITOR_SCRIPT), f"{self.MONITOR_SCRIPT} does not exist"
        mode = os.stat(self.MONITOR_SCRIPT).st_mode
        assert mode & stat.S_IXUSR, f"{self.MONITOR_SCRIPT} is not executable by owner"

    def test_monitor_script_references_archive_dir(self):
        """monitor_wal.sh must check the archive directory."""
        with open(self.MONITOR_SCRIPT, "r") as f:
            content = f.read()
        assert "wal_archive" in content or "/var/lib/postgresql" in content, \
            "monitor_wal.sh does not reference the archive directory"

    def test_monitor_script_writes_to_log(self):
        """monitor_wal.sh must reference the log file path."""
        with open(self.MONITOR_SCRIPT, "r") as f:
            content = f.read()
        assert "/var/log/wal_monitor.log" in content or "wal_monitor" in content, \
            "monitor_wal.sh does not reference /var/log/wal_monitor.log"

    def test_monitor_script_not_empty(self):
        """monitor_wal.sh must not be trivially small."""
        size = os.path.getsize(self.MONITOR_SCRIPT)
        assert size > 50, f"monitor_wal.sh is suspiciously small ({size} bytes)"

    def test_cron_job_exists_for_postgres(self):
        """A cron job must exist in the postgres user's crontab."""
        rc, out, err = run_cmd("crontab -u postgres -l")
        assert rc == 0, f"Failed to read postgres crontab: {err}"
        # Filter out comment lines
        active_lines = [
            line for line in out.splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        assert len(active_lines) >= 1, "No active cron entries found for postgres user"

    def test_cron_job_runs_at_least_hourly(self):
        """Cron job must run at least once per hour."""
        rc, out, _ = run_cmd("crontab -u postgres -l")
        if rc != 0:
            assert False, "Cannot read postgres crontab"
        active_lines = [
            line for line in out.splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        # Check that at least one cron entry has a schedule that runs at least hourly
        # Valid patterns: */N where N <= 60, or specific minutes, or * in minute field
        found_hourly = False
        for line in active_lines:
            parts = line.split()
            if len(parts) >= 5:
                minute_field = parts[0]
                # Runs at least hourly if minute field is *, */N (N<=60), or a number
                if minute_field == "*":
                    found_hourly = True
                    break
                if minute_field.startswith("*/"):
                    try:
                        interval = int(minute_field[2:])
                        if interval <= 60:
                            found_hourly = True
                            break
                    except ValueError:
                        pass
                # A specific minute like "0" or "30" means once per hour
                if minute_field.isdigit():
                    found_hourly = True
                    break
                # Comma-separated minutes like "0,30" also run at least hourly
                if "," in minute_field:
                    found_hourly = True
                    break
        assert found_hourly, f"No cron entry runs at least hourly. Entries: {active_lines}"

    def test_cron_references_monitor_script(self):
        """Cron job must reference a monitoring script or command."""
        rc, out, _ = run_cmd("crontab -u postgres -l")
        if rc != 0:
            assert False, "Cannot read postgres crontab"
        content = out.lower()
        has_ref = ("monitor" in content or "wal" in content
                   or "/usr/local/bin/" in content)
        assert has_ref, f"Cron job does not reference a monitoring script: {out}"
