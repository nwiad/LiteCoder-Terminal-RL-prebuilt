"""
Tests for LAMP Stack Automated Backup System.

Validates:
- Backup script existence and executability
- Backup directory structure and permissions
- File backup integrity (tar.gz with correct contents)
- Database backup integrity (sql.gz with valid SQL)
- Log file format and content
- Cron job scheduling
- Backup script exit code behavior
"""

import os
import re
import glob
import gzip
import stat
import subprocess
import tarfile


# ============================================================
# 1. Backup Script Existence and Executability
# ============================================================

class TestBackupScript:
    """Verify /app/backup.sh exists and is properly configured."""

    def test_backup_script_exists(self):
        """backup.sh must exist at /app/backup.sh."""
        assert os.path.isfile("/app/backup.sh"), \
            "/app/backup.sh does not exist"

    def test_backup_script_is_executable(self):
        """backup.sh must have execute permission."""
        st = os.stat("/app/backup.sh")
        assert st.st_mode & stat.S_IXUSR, \
            "/app/backup.sh is not executable by owner"

    def test_backup_script_is_bash(self):
        """backup.sh should be a bash script (shebang line)."""
        with open("/app/backup.sh", "r") as f:
            first_line = f.readline().strip()
        assert first_line.startswith("#!"), \
            "backup.sh missing shebang line"
        assert "bash" in first_line or "sh" in first_line, \
            f"backup.sh shebang does not reference bash/sh: {first_line}"

    def test_backup_script_not_empty(self):
        """backup.sh must have meaningful content (not a stub)."""
        size = os.path.getsize("/app/backup.sh")
        assert size > 100, \
            f"backup.sh is suspiciously small ({size} bytes), likely a stub"


# ============================================================
# 2. Backup Directory Structure and Permissions
# ============================================================

class TestDirectoryStructure:
    """Verify /backup directory tree exists with correct permissions."""

    def test_backup_root_exists(self):
        assert os.path.isdir("/backup"), "/backup directory does not exist"

    def test_files_dir_exists(self):
        assert os.path.isdir("/backup/files"), "/backup/files/ does not exist"

    def test_database_dir_exists(self):
        assert os.path.isdir("/backup/database"), "/backup/database/ does not exist"

    def test_logs_dir_exists(self):
        assert os.path.isdir("/backup/logs"), "/backup/logs/ does not exist"

    def test_backup_dir_permissions(self):
        """Backup directories should have 750 permissions."""
        for d in ["/backup", "/backup/files", "/backup/database", "/backup/logs"]:
            if os.path.isdir(d):
                mode = oct(os.stat(d).st_mode & 0o777)
                assert mode == "0o750", \
                    f"{d} has permissions {mode}, expected 0o750"


# ============================================================
# 3. File Backup Integrity
# ============================================================

class TestFileBackup:
    """Verify file backups in /backup/files/."""

    def _get_file_backups(self):
        return sorted(glob.glob("/backup/files/files_backup_*.tar.gz"))

    def test_at_least_one_file_backup_exists(self):
        backups = self._get_file_backups()
        assert len(backups) >= 1, \
            "No file backups found in /backup/files/"

    def test_file_backup_naming_convention(self):
        """Backup filenames must match files_backup_YYYYMMDD_HHMMSS.tar.gz."""
        backups = self._get_file_backups()
        assert len(backups) >= 1, "No file backups to check naming"
        pattern = re.compile(
            r"files_backup_\d{8}_\d{6}\.tar\.gz$"
        )
        for path in backups:
            basename = os.path.basename(path)
            assert pattern.search(basename), \
                f"File backup name '{basename}' does not match expected pattern"

    def test_file_backup_is_valid_tarball(self):
        """The tar.gz file must be a valid gzip-compressed tar archive."""
        backups = self._get_file_backups()
        assert len(backups) >= 1, "No file backups to validate"
        latest = backups[-1]
        assert os.path.getsize(latest) > 0, \
            f"File backup {latest} is empty (0 bytes)"
        assert tarfile.is_tarfile(latest), \
            f"{latest} is not a valid tar archive"

    def test_file_backup_contains_index_php(self):
        """Extracted archive must contain index.php."""
        backups = self._get_file_backups()
        assert len(backups) >= 1, "No file backups to inspect"
        latest = backups[-1]
        with tarfile.open(latest, "r:gz") as tf:
            names = tf.getnames()
        found = any("index.php" in n for n in names)
        assert found, \
            f"index.php not found in archive. Contents: {names[:20]}"

    def test_file_backup_contains_config_php(self):
        """Extracted archive must contain config.php."""
        backups = self._get_file_backups()
        assert len(backups) >= 1, "No file backups to inspect"
        latest = backups[-1]
        with tarfile.open(latest, "r:gz") as tf:
            names = tf.getnames()
        found = any("config.php" in n for n in names)
        assert found, \
            f"config.php not found in archive. Contents: {names[:20]}"


# ============================================================
# 4. Database Backup Integrity
# ============================================================

class TestDatabaseBackup:
    """Verify database backups in /backup/database/."""

    def _get_db_backups(self):
        return sorted(glob.glob("/backup/database/db_backup_*.sql.gz"))

    def test_at_least_one_db_backup_exists(self):
        backups = self._get_db_backups()
        assert len(backups) >= 1, \
            "No database backups found in /backup/database/"

    def test_db_backup_naming_convention(self):
        """Backup filenames must match db_backup_YYYYMMDD_HHMMSS.sql.gz."""
        backups = self._get_db_backups()
        assert len(backups) >= 1, "No db backups to check naming"
        pattern = re.compile(
            r"db_backup_\d{8}_\d{6}\.sql\.gz$"
        )
        for path in backups:
            basename = os.path.basename(path)
            assert pattern.search(basename), \
                f"DB backup name '{basename}' does not match expected pattern"

    def test_db_backup_is_valid_gzip(self):
        """The .sql.gz file must be a valid gzip file with content."""
        backups = self._get_db_backups()
        assert len(backups) >= 1, "No db backups to validate"
        latest = backups[-1]
        assert os.path.getsize(latest) > 0, \
            f"DB backup {latest} is empty (0 bytes)"
        # Try to decompress — will raise if invalid gzip
        with gzip.open(latest, "rb") as f:
            data = f.read()
        assert len(data) > 0, \
            f"DB backup {latest} decompresses to empty content"

    def test_db_backup_contains_customers_table(self):
        """Decompressed SQL must reference the customers table."""
        backups = self._get_db_backups()
        assert len(backups) >= 1, "No db backups to inspect"
        latest = backups[-1]
        with gzip.open(latest, "rb") as f:
            sql = f.read().decode("utf-8", errors="replace").lower()
        assert "customers" in sql, \
            "Decompressed SQL does not contain 'customers' table reference"

    def test_db_backup_contains_orders_table(self):
        """Decompressed SQL must reference the orders table."""
        backups = self._get_db_backups()
        assert len(backups) >= 1, "No db backups to inspect"
        latest = backups[-1]
        with gzip.open(latest, "rb") as f:
            sql = f.read().decode("utf-8", errors="replace").lower()
        assert "orders" in sql, \
            "Decompressed SQL does not contain 'orders' table reference"

    def test_db_backup_contains_sql_statements(self):
        """Decompressed SQL must contain actual SQL (CREATE or INSERT)."""
        backups = self._get_db_backups()
        assert len(backups) >= 1, "No db backups to inspect"
        latest = backups[-1]
        with gzip.open(latest, "rb") as f:
            sql = f.read().decode("utf-8", errors="replace").lower()
        has_create = "create table" in sql or "create " in sql
        has_insert = "insert" in sql
        assert has_create or has_insert, \
            "Decompressed SQL contains no CREATE or INSERT statements — not a valid mysqldump"

    def test_db_backup_has_meaningful_size(self):
        """DB backup should have meaningful content, not just a gzip header."""
        backups = self._get_db_backups()
        assert len(backups) >= 1, "No db backups to check size"
        latest = backups[-1]
        with gzip.open(latest, "rb") as f:
            sql = f.read()
        # A real mysqldump of 2 tables with data should be > 200 bytes
        assert len(sql) > 200, \
            f"Decompressed SQL is only {len(sql)} bytes — too small for a real dump"


# ============================================================
# 5. Logging
# ============================================================

class TestBackupLog:
    """Verify /backup/logs/backup.log format and content."""

    LOG_PATH = "/backup/logs/backup.log"

    def test_log_file_exists(self):
        assert os.path.isfile(self.LOG_PATH), \
            f"{self.LOG_PATH} does not exist"

    def test_log_file_not_empty(self):
        assert os.path.getsize(self.LOG_PATH) > 0, \
            f"{self.LOG_PATH} is empty"

    def test_log_has_at_least_two_success_lines(self):
        """After a successful run, log must have >= 2 SUCCESS entries
        (one for files, one for database)."""
        with open(self.LOG_PATH, "r") as f:
            content = f.read()
        success_count = content.upper().count("SUCCESS")
        assert success_count >= 2, \
            f"Expected at least 2 SUCCESS entries, found {success_count}"

    def test_log_entries_have_timestamp(self):
        """Each log line should start with a YYYY-MM-DD HH:MM:SS timestamp."""
        ts_pattern = re.compile(
            r"\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}"
        )
        with open(self.LOG_PATH, "r") as f:
            lines = [l.strip() for l in f if l.strip()]
        assert len(lines) >= 1, "Log file has no non-empty lines"
        for line in lines:
            assert ts_pattern.search(line), \
                f"Log line missing timestamp: '{line}'"

    def test_log_entries_have_status(self):
        """Each log line must contain SUCCESS or FAILURE."""
        with open(self.LOG_PATH, "r") as f:
            lines = [l.strip() for l in f if l.strip()]
        assert len(lines) >= 1, "Log file has no non-empty lines"
        for line in lines:
            upper = line.upper()
            assert "SUCCESS" in upper or "FAILURE" in upper, \
                f"Log line missing SUCCESS/FAILURE status: '{line}'"

    def test_log_mentions_files_backup(self):
        """Log should mention the files backup."""
        with open(self.LOG_PATH, "r") as f:
            content = f.read().lower()
        assert "file" in content, \
            "Log does not mention file backup"

    def test_log_mentions_database_backup(self):
        """Log should mention the database backup."""
        with open(self.LOG_PATH, "r") as f:
            content = f.read().lower()
        assert "database" in content or "db" in content, \
            "Log does not mention database backup"


# ============================================================
# 6. Cron Job Scheduling
# ============================================================

class TestCronJob:
    """Verify cron job is configured for root user."""

    def test_cron_entry_exists(self):
        """crontab -l must show an entry referencing /app/backup.sh."""
        result = subprocess.run(
            ["crontab", "-l"],
            capture_output=True, text=True
        )
        # crontab -l may return 1 if no crontab exists
        output = result.stdout + result.stderr
        assert "/app/backup.sh" in output, \
            f"No cron entry found for /app/backup.sh. crontab output: {output}"

    def test_cron_runs_at_2am(self):
        """Cron entry must schedule the job at 2:00 AM daily."""
        result = subprocess.run(
            ["crontab", "-l"],
            capture_output=True, text=True
        )
        output = result.stdout
        # Look for a line with minute=0, hour=2 and /app/backup.sh
        # Standard cron: 0 2 * * * /app/backup.sh
        pattern = re.compile(r"^\s*0\s+2\s+.*?/app/backup\.sh", re.MULTILINE)
        assert pattern.search(output), \
            f"Cron entry does not schedule at 2:00 AM. crontab output: {output}"


# ============================================================
# 7. Backup Script Exit Code
# ============================================================

class TestBackupScriptExecution:
    """Verify backup.sh runs correctly and returns proper exit code."""

    def test_backup_script_exits_zero_on_success(self):
        """Running backup.sh with MariaDB up should exit 0."""
        # Ensure MariaDB is running before executing
        subprocess.run(["service", "mariadb", "start"],
                       capture_output=True, timeout=15)
        import time
        time.sleep(2)

        result = subprocess.run(
            ["/app/backup.sh"],
            capture_output=True, text=True, timeout=60
        )
        assert result.returncode == 0, \
            f"backup.sh exited with code {result.returncode}.\n" \
            f"stdout: {result.stdout[:500]}\nstderr: {result.stderr[:500]}"

    def test_backup_creates_new_files_on_rerun(self):
        """Running backup.sh again should create additional backup files."""
        # Count existing backups
        file_before = len(glob.glob("/backup/files/files_backup_*.tar.gz"))
        db_before = len(glob.glob("/backup/database/db_backup_*.sql.gz"))

        # Small delay to ensure different timestamp
        import time
        time.sleep(1)

        subprocess.run(["service", "mariadb", "start"],
                       capture_output=True, timeout=15)
        time.sleep(1)

        result = subprocess.run(
            ["/app/backup.sh"],
            capture_output=True, text=True, timeout=60
        )

        file_after = len(glob.glob("/backup/files/files_backup_*.tar.gz"))
        db_after = len(glob.glob("/backup/database/db_backup_*.sql.gz"))

        assert file_after > file_before, \
            "Re-running backup.sh did not create a new file backup"
        assert db_after > db_before, \
            "Re-running backup.sh did not create a new database backup"

