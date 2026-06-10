"""
Tests for SSH Key Pair and Encrypted Backup System task.
Validates all 7 steps from instruction.md by checking output artifacts.
"""

import os
import stat
import subprocess
import filecmp


# ============================================================================
# Helper utilities
# ============================================================================

def file_exists_and_nonempty(path):
    """Check file exists and has content."""
    return os.path.isfile(path) and os.path.getsize(path) > 0


def get_file_permissions(path):
    """Return octal permission string like '600' or '644'."""
    st = os.stat(path)
    return oct(stat.S_IMODE(st.st_mode))[-3:]


def read_file_lines(path):
    """Read file and return stripped lines."""
    with open(path, "r") as f:
        return [line.strip() for line in f.readlines()]


def parse_key_value_file(path):
    """Parse a key=value config file, return dict of keys found."""
    result = {}
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                key, _, value = line.partition("=")
                result[key.strip()] = value.strip()
    return result


# ============================================================================
# Step 1: SSH Key Pair
# ============================================================================

class TestSSHKeyPair:
    PRIVATE_KEY = "/app/ssh_keys/id_rsa"
    PUBLIC_KEY = "/app/ssh_keys/id_rsa.pub"

    def test_private_key_exists(self):
        assert file_exists_and_nonempty(self.PRIVATE_KEY), \
            "Private key /app/ssh_keys/id_rsa must exist and be non-empty"

    def test_public_key_exists(self):
        assert file_exists_and_nonempty(self.PUBLIC_KEY), \
            "Public key /app/ssh_keys/id_rsa.pub must exist and be non-empty"

    def test_private_key_permissions(self):
        assert get_file_permissions(self.PRIVATE_KEY) == "600", \
            "Private key must have permissions 600"

    def test_public_key_permissions(self):
        assert get_file_permissions(self.PUBLIC_KEY) == "644", \
            "Public key must have permissions 644"

    def test_private_key_is_rsa_format(self):
        """Verify the private key file starts with a valid RSA/OPENSSH header."""
        with open(self.PRIVATE_KEY, "r") as f:
            header = f.readline().strip()
        valid_headers = [
            "-----BEGIN RSA PRIVATE KEY-----",
            "-----BEGIN OPENSSH PRIVATE KEY-----",
        ]
        assert header in valid_headers, \
            f"Private key must start with a valid PEM/OpenSSH header, got: {header}"

    def test_public_key_is_ssh_rsa(self):
        """Verify the public key contains ssh-rsa key material."""
        with open(self.PUBLIC_KEY, "r") as f:
            content = f.read().strip()
        # Public key should start with ssh-rsa (or could be other format)
        assert content.startswith("ssh-rsa ") or "ssh-rsa" in content, \
            "Public key must contain ssh-rsa key data"

    def test_ssh_key_is_4096_bits(self):
        """Use ssh-keygen -l to verify key length is 4096."""
        result = subprocess.run(
            ["ssh-keygen", "-l", "-f", self.PUBLIC_KEY],
            capture_output=True, text=True
        )
        assert result.returncode == 0, "ssh-keygen -l failed on public key"
        # Output format: "4096 SHA256:... comment (RSA)"
        parts = result.stdout.strip().split()
        assert len(parts) >= 1, "Unexpected ssh-keygen output"
        assert parts[0] == "4096", \
            f"SSH key must be 4096 bits, got {parts[0]}"


# ============================================================================
# Step 2: SSH Daemon Configuration
# ============================================================================

class TestSSHDaemonConfig:
    CONFIG_PATH = "/app/ssh_config/sshd_config"

    REQUIRED_DIRECTIVES = {
        "PermitRootLogin": "no",
        "PasswordAuthentication": "no",
        "PubkeyAuthentication": "yes",
        "Protocol": "2",
        "MaxAuthTries": "3",
        "AllowUsers": "admin",
    }

    def test_sshd_config_exists(self):
        assert file_exists_and_nonempty(self.CONFIG_PATH), \
            "sshd_config must exist and be non-empty"

    def test_sshd_config_permissions(self):
        assert get_file_permissions(self.CONFIG_PATH) == "600", \
            "sshd_config must have permissions 600"

    def test_sshd_config_directives(self):
        """Check all required directives are present with correct values."""
        with open(self.CONFIG_PATH, "r") as f:
            lines = f.readlines()

        # Parse directives: skip comments and blank lines
        found = {}
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            parts = stripped.split(None, 1)
            if len(parts) == 2:
                found[parts[0]] = parts[1]

        for directive, expected_value in self.REQUIRED_DIRECTIVES.items():
            assert directive in found, \
                f"Directive '{directive}' missing from sshd_config"
            assert found[directive] == expected_value, \
                f"Directive '{directive}' expected '{expected_value}', got '{found[directive]}'"


# ============================================================================
# Step 3: Sensitive Test Data
# ============================================================================

class TestSensitiveData:
    DATA_DIR = "/app/sensitive_data"

    def test_database_conf_exists(self):
        path = os.path.join(self.DATA_DIR, "database.conf")
        assert file_exists_and_nonempty(path), "database.conf must exist and be non-empty"

    def test_database_conf_keys(self):
        path = os.path.join(self.DATA_DIR, "database.conf")
        kv = parse_key_value_file(path)
        for key in ["db_host", "db_port", "db_user", "db_password"]:
            assert key in kv, f"database.conf missing required key: {key}"
            assert len(kv[key]) > 0, f"database.conf key '{key}' must have a non-empty value"

    def test_api_keys_conf_exists(self):
        path = os.path.join(self.DATA_DIR, "api_keys.conf")
        assert file_exists_and_nonempty(path), "api_keys.conf must exist and be non-empty"

    def test_api_keys_conf_keys(self):
        path = os.path.join(self.DATA_DIR, "api_keys.conf")
        kv = parse_key_value_file(path)
        for key in ["api_key", "api_secret"]:
            assert key in kv, f"api_keys.conf missing required key: {key}"
            assert len(kv[key]) > 0, f"api_keys.conf key '{key}' must have a non-empty value"

    def test_server_conf_exists(self):
        path = os.path.join(self.DATA_DIR, "server.conf")
        assert file_exists_and_nonempty(path), "server.conf must exist and be non-empty"

    def test_server_conf_keys(self):
        path = os.path.join(self.DATA_DIR, "server.conf")
        kv = parse_key_value_file(path)
        for key in ["server_ip", "server_port", "server_user"]:
            assert key in kv, f"server.conf missing required key: {key}"
            assert len(kv[key]) > 0, f"server.conf key '{key}' must have a non-empty value"


# ============================================================================
# Step 4: GPG Key Pair
# ============================================================================

class TestGPGKeys:
    PUBLIC_KEY = "/app/gpg_keys/backup_public.gpg"
    SECRET_KEY = "/app/gpg_keys/backup_secret.gpg"

    def test_gpg_public_key_exists(self):
        assert file_exists_and_nonempty(self.PUBLIC_KEY), \
            "GPG public key must exist and be non-empty"

    def test_gpg_secret_key_exists(self):
        assert file_exists_and_nonempty(self.SECRET_KEY), \
            "GPG secret key must exist and be non-empty"

    def test_gpg_public_key_valid_format(self):
        """Public key should be a valid GPG key (armored or binary)."""
        with open(self.PUBLIC_KEY, "rb") as f:
            header = f.read(40)
        # Check for armored PGP or binary GPG format
        is_armored = b"-----BEGIN PGP PUBLIC KEY" in header
        # Binary GPG packets start with specific tag bytes (0x98, 0x99, 0xc6, etc.)
        is_binary = len(header) > 0 and (header[0] & 0x80) != 0
        assert is_armored or is_binary, \
            "GPG public key file must be in valid PGP format (armored or binary)"

    def test_gpg_secret_key_valid_format(self):
        """Secret key should be a valid GPG secret key (armored or binary)."""
        with open(self.SECRET_KEY, "rb") as f:
            header = f.read(40)
        is_armored = b"-----BEGIN PGP PRIVATE KEY" in header
        is_binary = len(header) > 0 and (header[0] & 0x80) != 0
        assert is_armored or is_binary, \
            "GPG secret key file must be in valid PGP format (armored or binary)"

    def test_gpg_public_key_contains_identity(self):
        """Verify the exported public key contains the BackupAdmin identity."""
        # Import the key into a temp keyring and check
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            env = os.environ.copy()
            env["GNUPGHOME"] = tmpdir
            os.chmod(tmpdir, 0o700)
            result = subprocess.run(
                ["gpg", "--batch", "--import", self.PUBLIC_KEY],
                capture_output=True, text=True, env=env
            )
            # Now list keys
            list_result = subprocess.run(
                ["gpg", "--batch", "--list-keys", "--with-colons"],
                capture_output=True, text=True, env=env
            )
            output = list_result.stdout
            assert "BackupAdmin" in output or "backup@example.com" in output, \
                "GPG public key must contain BackupAdmin / backup@example.com identity"


# ============================================================================
# Step 5: Encrypted Backup
# ============================================================================

class TestEncryptedBackup:
    BACKUP_PATH = "/app/backups/sensitive_backup.tar.gpg"

    def test_encrypted_backup_exists(self):
        assert file_exists_and_nonempty(self.BACKUP_PATH), \
            "Encrypted backup must exist and be non-empty"

    def test_encrypted_backup_is_gpg_data(self):
        """Verify the file is actual GPG encrypted data, not just a renamed file."""
        with open(self.BACKUP_PATH, "rb") as f:
            header = f.read(10)
        # GPG encrypted data: binary packets start with high bit set (0x80+)
        # or armored format starts with -----BEGIN PGP MESSAGE-----
        is_binary_gpg = len(header) > 0 and (header[0] & 0x80) != 0
        is_armored_gpg = header.startswith(b"-----BEGIN")
        assert is_binary_gpg or is_armored_gpg, \
            "Backup file must be valid GPG encrypted data"

    def test_encrypted_backup_minimum_size(self):
        """Encrypted backup of 3 config files should be at least a few hundred bytes."""
        size = os.path.getsize(self.BACKUP_PATH)
        assert size > 100, \
            f"Encrypted backup seems too small ({size} bytes), likely not a real encrypted archive"

    def test_encrypted_backup_is_not_plain_tar(self):
        """Ensure the file is actually encrypted, not just a plain tar."""
        with open(self.BACKUP_PATH, "rb") as f:
            header = f.read(262)
        # Tar files have magic "ustar" at offset 257
        is_tar = len(header) >= 262 and header[257:262] == b"ustar"
        assert not is_tar, \
            "Backup file appears to be a plain tar archive, not GPG-encrypted"


# ============================================================================
# Step 6: Decryption Verification (restored files)
# ============================================================================

class TestDecryptionVerification:
    ORIGINAL_DIR = "/app/sensitive_data"
    RESTORED_DIR = "/app/backups/restored"
    FILES = ["database.conf", "api_keys.conf", "server.conf"]

    def test_restored_directory_exists(self):
        assert os.path.isdir(self.RESTORED_DIR), \
            "/app/backups/restored/ directory must exist"

    def test_restored_files_exist(self):
        for fname in self.FILES:
            path = os.path.join(self.RESTORED_DIR, fname)
            assert file_exists_and_nonempty(path), \
                f"Restored file {fname} must exist and be non-empty"

    def test_restored_database_conf_matches_original(self):
        """Restored database.conf must be byte-identical to original."""
        orig = os.path.join(self.ORIGINAL_DIR, "database.conf")
        restored = os.path.join(self.RESTORED_DIR, "database.conf")
        assert os.path.isfile(orig), "Original database.conf missing"
        assert os.path.isfile(restored), "Restored database.conf missing"
        assert filecmp.cmp(orig, restored, shallow=False), \
            "Restored database.conf does not match original"

    def test_restored_api_keys_conf_matches_original(self):
        """Restored api_keys.conf must be byte-identical to original."""
        orig = os.path.join(self.ORIGINAL_DIR, "api_keys.conf")
        restored = os.path.join(self.RESTORED_DIR, "api_keys.conf")
        assert os.path.isfile(orig), "Original api_keys.conf missing"
        assert os.path.isfile(restored), "Restored api_keys.conf missing"
        assert filecmp.cmp(orig, restored, shallow=False), \
            "Restored api_keys.conf does not match original"

    def test_restored_server_conf_matches_original(self):
        """Restored server.conf must be byte-identical to original."""
        orig = os.path.join(self.ORIGINAL_DIR, "server.conf")
        restored = os.path.join(self.RESTORED_DIR, "server.conf")
        assert os.path.isfile(orig), "Original server.conf missing"
        assert os.path.isfile(restored), "Restored server.conf missing"
        assert filecmp.cmp(orig, restored, shallow=False), \
            "Restored server.conf does not match original"


# ============================================================================
# Step 7: Documentation
# ============================================================================

class TestDocumentation:
    DOC_PATH = "/app/docs/security_report.txt"

    REQUIRED_SECTIONS = [
        "SSH Key Generation",
        "SSH Daemon Configuration",
        "GPG Encryption",
        "Backup Process",
        "Security Measures",
    ]

    def test_doc_exists(self):
        assert file_exists_and_nonempty(self.DOC_PATH), \
            "security_report.txt must exist and be non-empty"

    def test_doc_minimum_length(self):
        """Documentation must be at least 20 lines."""
        with open(self.DOC_PATH, "r") as f:
            lines = f.readlines()
        assert len(lines) >= 20, \
            f"security_report.txt must be at least 20 lines, got {len(lines)}"

    def test_doc_contains_required_sections(self):
        """Each required section name must appear somewhere in the document."""
        with open(self.DOC_PATH, "r") as f:
            content = f.read()
        for section in self.REQUIRED_SECTIONS:
            assert section in content, \
                f"security_report.txt must contain section: '{section}'"

    def test_doc_is_not_trivial(self):
        """Ensure the doc has real content, not just section headers."""
        with open(self.DOC_PATH, "r") as f:
            content = f.read()
        # Strip whitespace and check total character count
        # 5 section headers alone would be ~100 chars; real doc should be much more
        non_empty_lines = [l for l in content.splitlines() if l.strip()]
        assert len(non_empty_lines) >= 15, \
            f"security_report.txt should have at least 15 non-empty lines of content, got {len(non_empty_lines)}"
