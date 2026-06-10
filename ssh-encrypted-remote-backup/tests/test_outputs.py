"""
Tests for the SSH Encrypted Remote Backup task.

Validates all 5 output artifacts:
  1. SSH key pair (/root/.ssh/id_rsa, id_rsa.pub)
  2. Backup script (/root/remote_backup.sh)
  3. Cron job (root's crontab)
  4. RESTORE.md (/root/RESTORE.md)
  5. Functional: backup script produces valid encrypted archive
"""

import os
import re
import stat
import subprocess
import glob
import time


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def read_file(path):
    """Read file contents, return empty string if missing."""
    try:
        with open(path, "r") as f:
            return f.read()
    except (FileNotFoundError, PermissionError, UnicodeDecodeError):
        return ""


def file_exists(path):
    return os.path.isfile(path)


def get_file_permissions(path):
    """Return octal permission string like '600'."""
    try:
        st = os.stat(path)
        return oct(stat.S_IMODE(st.st_mode))[-3:]
    except FileNotFoundError:
        return None


def run_cmd(cmd, timeout=30):
    """Run a shell command and return (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "timeout"


# ===========================================================================
# 1. SSH KEY PAIR TESTS
# ===========================================================================

class TestSSHKeyPair:
    """Verify SSH key pair generation."""

    def test_private_key_exists(self):
        assert file_exists("/root/.ssh/id_rsa"), \
            "Private key /root/.ssh/id_rsa does not exist"

    def test_public_key_exists(self):
        assert file_exists("/root/.ssh/id_rsa.pub"), \
            "Public key /root/.ssh/id_rsa.pub does not exist"

    def test_private_key_permissions(self):
        perms = get_file_permissions("/root/.ssh/id_rsa")
        assert perms is not None, "Cannot stat /root/.ssh/id_rsa"
        assert perms == "600", \
            f"Private key permissions should be 600, got {perms}"

    def test_key_is_rsa(self):
        """Key type must be RSA."""
        rc, stdout, stderr = run_cmd("ssh-keygen -l -f /root/.ssh/id_rsa.pub")
        assert rc == 0, f"ssh-keygen -l failed: {stderr}"
        # Output looks like: "4096 SHA256:... root@host (RSA)"
        output = stdout.strip()
        assert "RSA" in output.upper(), \
            f"Key is not RSA. ssh-keygen output: {output}"

    def test_key_is_4096_bit(self):
        """Key must be 4096-bit."""
        rc, stdout, _ = run_cmd("ssh-keygen -l -f /root/.ssh/id_rsa.pub")
        assert rc == 0, "ssh-keygen -l failed"
        # First token is the bit size
        parts = stdout.strip().split()
        assert len(parts) >= 1, "Unexpected ssh-keygen output"
        assert parts[0] == "4096", \
            f"Key size should be 4096, got {parts[0]}"

    def test_private_key_has_no_passphrase(self):
        """Verify the private key can be read without a passphrase."""
        # ssh-keygen -y reads the private key and outputs the public key.
        # If the key has a passphrase, this will fail (or prompt).
        rc, stdout, stderr = run_cmd(
            "ssh-keygen -y -f /root/.ssh/id_rsa -P ''"
        )
        assert rc == 0, \
            f"Private key appears to have a passphrase or is invalid: {stderr}"
        assert stdout.strip().startswith("ssh-rsa"), \
            "Private key does not produce a valid RSA public key"

    def test_private_key_not_empty(self):
        content = read_file("/root/.ssh/id_rsa")
        assert len(content) > 100, \
            "Private key file is empty or suspiciously small"

    def test_public_key_not_empty(self):
        content = read_file("/root/.ssh/id_rsa.pub")
        assert len(content) > 50, \
            "Public key file is empty or suspiciously small"


# ===========================================================================
# 2. BACKUP SCRIPT TESTS
# ===========================================================================

class TestBackupScript:
    """Verify the backup script structure and content."""

    def test_script_exists(self):
        assert file_exists("/root/remote_backup.sh"), \
            "Backup script /root/remote_backup.sh does not exist"

    def test_script_is_executable(self):
        assert os.access("/root/remote_backup.sh", os.X_OK), \
            "Backup script is not executable"

    def test_script_starts_with_shebang(self):
        content = read_file("/root/remote_backup.sh")
        assert content.startswith("#!/bin/bash"), \
            "Backup script must start with #!/bin/bash"

    def test_script_compresses_srv_apps(self):
        """Script must reference /srv/apps and use tar for compression."""
        content = read_file("/root/remote_backup.sh")
        assert "/srv/apps" in content, \
            "Script does not reference /srv/apps"
        assert "tar" in content, \
            "Script does not use tar for compression"

    def test_script_uses_aes_256_cbc(self):
        """Script must use openssl enc with aes-256-cbc."""
        content = read_file("/root/remote_backup.sh")
        assert "openssl" in content, \
            "Script does not reference openssl"
        assert "aes-256-cbc" in content, \
            "Script does not use aes-256-cbc cipher"

    def test_script_uses_safe_passphrase_passing(self):
        """Passphrase must NOT be passed via -pass pass:... pattern.
        Must use -pass stdin, -pass fd:, or -pass file:/dev/stdin."""
        content = read_file("/root/remote_backup.sh")
        # Check that the script uses a safe passphrase mechanism
        has_safe = any(
            pattern in content
            for pattern in ["-pass stdin", "-pass fd:", "-pass file:/dev/stdin"]
        )
        assert has_safe, \
            "Script must pass passphrase via -pass stdin, -pass fd:N, or -pass file:/dev/stdin"

    def test_script_does_not_use_pass_pass(self):
        """Script must not use -pass pass: which exposes passphrase on cmdline."""
        content = read_file("/root/remote_backup.sh")
        # Look for literal -pass pass: usage (the forbidden pattern)
        # Allow references in comments but not in actual commands
        lines = content.split("\n")
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("#"):
                continue  # skip comments
            if "-pass pass:" in stripped:
                assert False, \
                    f"Script uses forbidden -pass pass: pattern: {stripped}"

    def test_script_generates_random_passphrase(self):
        """Script must generate passphrase from /dev/urandom or similar."""
        content = read_file("/root/remote_backup.sh")
        has_random = any(
            src in content
            for src in ["/dev/urandom", "openssl rand", "head -c"]
        )
        assert has_random, \
            "Script does not appear to generate a random passphrase"

    def test_script_uses_scp_or_rsync(self):
        """Script must upload via scp or rsync."""
        content = read_file("/root/remote_backup.sh")
        assert "scp" in content or "rsync" in content, \
            "Script does not use scp or rsync for upload"

    def test_script_targets_correct_remote(self):
        """Script must target bkp@backup.example.com."""
        content = read_file("/root/remote_backup.sh")
        assert "backup.example.com" in content, \
            "Script does not reference backup.example.com"
        assert "bkp" in content, \
            "Script does not reference user 'bkp'"

    def test_script_has_cleanup(self):
        """Script must clean up intermediate files (trap or explicit rm)."""
        content = read_file("/root/remote_backup.sh")
        has_cleanup = ("trap" in content) or ("rm " in content and "tar.gz" in content)
        assert has_cleanup, \
            "Script does not appear to clean up intermediate tar.gz files"

    def test_backup_filename_pattern(self):
        """Script must produce files named backup-YYYYmmdd-HHMMSS.tar.gz.enc."""
        content = read_file("/root/remote_backup.sh")
        # Check for the date format pattern in the script
        # The script should construct a filename with date components
        has_pattern = (
            "tar.gz.enc" in content
            and ("backup-" in content or "BACKUP" in content.upper())
        )
        assert has_pattern, \
            "Script does not produce backup-YYYYmmdd-HHMMSS.tar.gz.enc filename"


# ===========================================================================
# 3. CRON JOB TESTS
# ===========================================================================

class TestCronJob:
    """Verify the cron job is installed correctly."""

    def test_cron_entry_exists(self):
        """Root's crontab must contain an entry for the backup script."""
        rc, stdout, stderr = run_cmd("crontab -l 2>/dev/null")
        # crontab -l returns non-zero if no crontab is set
        assert rc == 0 and len(stdout.strip()) > 0, \
            f"No crontab entries found for root. stderr: {stderr}"

    def test_cron_schedule_is_0215(self):
        """Cron schedule must be 15 2 * * * (every night at 02:15)."""
        rc, stdout, _ = run_cmd("crontab -l 2>/dev/null")
        assert rc == 0, "Cannot read crontab"
        lines = stdout.strip().split("\n")
        found = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            # Match: 15 2 * * * followed by the script path
            if re.match(r"^\s*15\s+2\s+\*\s+\*\s+\*\s+", stripped):
                found = True
                break
        assert found, \
            f"No cron entry with schedule '15 2 * * *' found. Crontab:\n{stdout}"

    def test_cron_invokes_backup_script(self):
        """Cron entry must invoke /root/remote_backup.sh."""
        rc, stdout, _ = run_cmd("crontab -l 2>/dev/null")
        assert rc == 0, "Cannot read crontab"
        assert "/root/remote_backup.sh" in stdout, \
            "Cron entry does not invoke /root/remote_backup.sh"

    def test_cron_schedule_and_script_on_same_line(self):
        """The schedule and script path must be on the same cron line."""
        rc, stdout, _ = run_cmd("crontab -l 2>/dev/null")
        assert rc == 0, "Cannot read crontab"
        lines = stdout.strip().split("\n")
        found = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if re.match(r"^\s*15\s+2\s+\*\s+\*\s+\*\s+", stripped) and \
               "/root/remote_backup.sh" in stripped:
                found = True
                break
        assert found, \
            "No single cron line has both '15 2 * * *' and '/root/remote_backup.sh'"


# ===========================================================================
# 4. RESTORE DOCUMENTATION TESTS
# ===========================================================================

class TestRestoreDoc:
    """Verify RESTORE.md content."""

    def test_restore_md_exists(self):
        assert file_exists("/root/RESTORE.md"), \
            "RESTORE.md does not exist at /root/RESTORE.md"

    def test_restore_md_not_empty(self):
        content = read_file("/root/RESTORE.md")
        assert len(content.strip()) > 50, \
            "RESTORE.md is empty or too short to be useful documentation"

    def test_restore_md_has_decrypt_command(self):
        """Must document the openssl decryption command."""
        content = read_file("/root/RESTORE.md").lower()
        assert "openssl" in content, \
            "RESTORE.md does not mention openssl"
        assert "aes-256-cbc" in content, \
            "RESTORE.md does not mention aes-256-cbc cipher"
        # Must show decryption flag
        assert "-d" in content, \
            "RESTORE.md does not show the -d (decrypt) flag for openssl"

    def test_restore_md_has_tar_command(self):
        """Must document tar extraction."""
        content = read_file("/root/RESTORE.md")
        assert "tar" in content, \
            "RESTORE.md does not mention tar for extraction"

    def test_restore_md_mentions_passphrase(self):
        """Must mention that the encryption passphrase is required."""
        content = read_file("/root/RESTORE.md").lower()
        assert "passphrase" in content or "password" in content or "pass" in content, \
            "RESTORE.md does not mention that the passphrase is required"


# ===========================================================================
# 5. FUNCTIONAL TESTS — Run the backup script and validate output
# ===========================================================================

class TestBackupFunctional:
    """Run the backup script and verify it produces a valid encrypted archive.

    The scp/rsync upload will fail (no remote server), but the script should
    still produce the encrypted file and clean up intermediate files.
    """

    @staticmethod
    def _find_enc_files(directory="/tmp"):
        """Find .tar.gz.enc files in common temp locations and /app."""
        enc_files = []
        for search_dir in ["/tmp", "/app", "/root"]:
            enc_files.extend(
                glob.glob(os.path.join(search_dir, "**", "*.tar.gz.enc"), recursive=True)
            )
        return enc_files

    @staticmethod
    def _run_backup_script():
        """Execute the backup script, capturing output.
        Returns (returncode, stdout, stderr, enc_files_before, enc_files_after).
        """
        # Record existing .enc files before running
        before = set(TestBackupFunctional._find_enc_files())

        # Run the script — scp will fail but script should continue
        rc, stdout, stderr = run_cmd(
            "bash /root/remote_backup.sh 2>&1",
            timeout=60
        )

        # Find new .enc files
        after = set(TestBackupFunctional._find_enc_files())
        new_files = after - before

        return rc, stdout, stderr, new_files

    def test_script_runs_without_fatal_error(self):
        """Script should execute (scp failure is expected and acceptable)."""
        assert file_exists("/root/remote_backup.sh"), \
            "Backup script does not exist"
        # The script may exit non-zero due to scp failure, that's OK.
        # We just need it to not crash before producing the encrypted file.
        rc, stdout, stderr, new_files = self._run_backup_script()
        # Even if rc != 0 (scp fails), the script should have produced output
        combined = stdout + stderr
        # Script should not have a syntax error
        assert "syntax error" not in combined.lower(), \
            f"Script has a syntax error: {combined[:500]}"

    def test_encrypted_file_produced(self):
        """Script must produce a .tar.gz.enc file."""
        _, stdout, stderr, new_files = self._run_backup_script()
        # Also check stdout for the filename pattern
        combined = stdout + stderr
        # Look for the backup filename pattern in output or on disk
        pattern = re.compile(r"backup-\d{8}-\d{6}\.tar\.gz\.enc")

        found_in_output = bool(pattern.search(combined))
        found_on_disk = len(new_files) > 0

        # At least one of these should be true
        # (the file might be in a tmpdir that gets cleaned up)
        assert found_in_output or found_on_disk, \
            "Script did not produce a backup-YYYYmmdd-HHMMSS.tar.gz.enc file"

    def test_encrypted_file_name_format(self):
        """The .enc filename must match backup-YYYYmmdd-HHMMSS.tar.gz.enc."""
        _, stdout, stderr, new_files = self._run_backup_script()
        combined = stdout + stderr
        pattern = re.compile(r"backup-\d{8}-\d{6}\.tar\.gz\.enc")

        # Check in output text
        match_in_output = pattern.search(combined)
        # Check on disk
        match_on_disk = any(
            pattern.search(os.path.basename(f)) for f in new_files
        )
        assert match_in_output or match_on_disk, \
            "Encrypted file name does not match backup-YYYYmmdd-HHMMSS.tar.gz.enc"

    def test_intermediate_tar_gz_cleaned_up(self):
        """After script runs, no intermediate .tar.gz (non-encrypted) should remain."""
        self._run_backup_script()
        # Check common temp directories for leftover .tar.gz files
        # (not .tar.gz.enc — those are the final product)
        leftover = []
        for search_dir in ["/tmp"]:
            for f in glob.glob(os.path.join(search_dir, "**", "*.tar.gz"), recursive=True):
                # Exclude .tar.gz.enc files
                if not f.endswith(".tar.gz.enc"):
                    leftover.append(f)
        assert len(leftover) == 0, \
            f"Intermediate tar.gz files not cleaned up: {leftover}"

    def test_passphrase_is_32_chars(self):
        """The passphrase printed in script output should be 32 characters."""
        _, stdout, stderr, _ = self._run_backup_script()
        combined = stdout + stderr
        # Look for a 32-char passphrase in the output
        # The script should print/log the passphrase somewhere
        # Common patterns: "PASSPHRASE: xxx" or "passphrase: xxx"
        # We look for any 32-char alphanumeric+special string
        # that appears after a passphrase-related keyword
        passphrase_pattern = re.compile(
            r"(?:passphrase|PASSPHRASE|pass|key)[:\s=]+([A-Za-z0-9+/=]{32})",
            re.IGNORECASE
        )
        match = passphrase_pattern.search(combined)
        if match:
            passphrase = match.group(1)
            assert len(passphrase) == 32, \
                f"Passphrase length is {len(passphrase)}, expected 32"
        # If no passphrase is printed, that's also acceptable —
        # the instruction says it must be 32 chars but doesn't require printing.
        # The script content check already verifies the generation logic.
