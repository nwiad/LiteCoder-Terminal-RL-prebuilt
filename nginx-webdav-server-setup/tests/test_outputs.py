"""
Tests for Nginx WebDAV Server Setup task.

Verifies:
- File/directory structure and permissions
- SSL certificate properties
- Htpasswd file with hashed passwords
- Nginx configuration correctness
- Nginx service state
- Functional HTTP tests (auth, access control, WebDAV operations)
"""

import os
import subprocess
import stat
import re
import time


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run(cmd, **kwargs):
    """Run a shell command and return CompletedProcess."""
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, **kwargs)


def curl(url, user=None, method="GET", data=None, extra_args=""):
    """Issue a curl request and return (http_code, body)."""
    parts = ["curl", "-s", "-k", "-o", "/dev/null", "-w", "%{http_code}"]
    if user:
        parts += ["-u", user]
    if method != "GET":
        parts += ["-X", method]
    if data is not None:
        parts += ["-d", data]
    if extra_args:
        parts += extra_args.split()
    parts.append(url)
    result = subprocess.run(parts, capture_output=True, text=True, timeout=10)
    return int(result.stdout.strip())


def curl_body(url, user=None):
    """Issue a curl request and return (http_code, body)."""
    parts = ["curl", "-s", "-k", "-w", "\n%{http_code}"]
    if user:
        parts += ["-u", user]
    parts.append(url)
    result = subprocess.run(parts, capture_output=True, text=True, timeout=10)
    lines = result.stdout.rsplit("\n", 1)
    body = lines[0] if len(lines) > 1 else ""
    code = int(lines[-1].strip())
    return code, body


# ===========================================================================
# 1. Directory structure tests
# ===========================================================================

class TestDirectoryStructure:
    """Verify WebDAV directories exist with correct ownership and permissions."""

    def test_webdav_root_exists(self):
        assert os.path.isdir("/srv/webdav"), "/srv/webdav directory must exist"

    def test_alice_dir_exists(self):
        assert os.path.isdir("/srv/webdav/alice"), "/srv/webdav/alice directory must exist"

    def test_bob_dir_exists(self):
        assert os.path.isdir("/srv/webdav/bob"), "/srv/webdav/bob directory must exist"

    def test_webdav_root_ownership(self):
        st = os.stat("/srv/webdav")
        import pwd, grp
        owner = pwd.getpwuid(st.st_uid).pw_name
        group = grp.getgrgid(st.st_gid).gr_name
        assert owner == "www-data", f"Owner should be www-data, got {owner}"
        assert group == "www-data", f"Group should be www-data, got {group}"

    def test_alice_dir_ownership(self):
        st = os.stat("/srv/webdav/alice")
        import pwd, grp
        owner = pwd.getpwuid(st.st_uid).pw_name
        group = grp.getgrgid(st.st_gid).gr_name
        assert owner == "www-data", f"Owner should be www-data, got {owner}"
        assert group == "www-data", f"Group should be www-data, got {group}"

    def test_bob_dir_ownership(self):
        st = os.stat("/srv/webdav/bob")
        import pwd, grp
        owner = pwd.getpwuid(st.st_uid).pw_name
        group = grp.getgrgid(st.st_gid).gr_name
        assert owner == "www-data", f"Owner should be www-data, got {owner}"
        assert group == "www-data", f"Group should be www-data, got {group}"

    def test_webdav_root_permissions(self):
        st = os.stat("/srv/webdav")
        mode = stat.S_IMODE(st.st_mode)
        assert mode == 0o755, f"Permissions should be 0755, got {oct(mode)}"

    def test_alice_dir_permissions(self):
        st = os.stat("/srv/webdav/alice")
        mode = stat.S_IMODE(st.st_mode)
        assert mode == 0o755, f"Permissions should be 0755, got {oct(mode)}"

    def test_bob_dir_permissions(self):
        st = os.stat("/srv/webdav/bob")
        mode = stat.S_IMODE(st.st_mode)
        assert mode == 0o755, f"Permissions should be 0755, got {oct(mode)}"


# ===========================================================================
# 2. Htpasswd tests
# ===========================================================================

class TestHtpasswd:
    """Verify htpasswd file exists with hashed passwords for alice and bob."""

    def test_htpasswd_exists(self):
        assert os.path.isfile("/etc/nginx/.htpasswd"), "htpasswd file must exist"

    def test_htpasswd_not_empty(self):
        size = os.path.getsize("/etc/nginx/.htpasswd")
        assert size > 0, "htpasswd file must not be empty"

    def test_htpasswd_contains_alice(self):
        with open("/etc/nginx/.htpasswd") as f:
            content = f.read()
        assert re.search(r"^alice:", content, re.MULTILINE), "htpasswd must contain alice"

    def test_htpasswd_contains_bob(self):
        with open("/etc/nginx/.htpasswd") as f:
            content = f.read()
        assert re.search(r"^bob:", content, re.MULTILINE), "htpasswd must contain bob"

    def test_passwords_are_hashed(self):
        """Passwords must not be stored in plaintext."""
        with open("/etc/nginx/.htpasswd") as f:
            content = f.read()
        # Plaintext passwords would appear literally after the colon
        assert "alice:alice_pass" not in content, "alice password must be hashed"
        assert "bob:bob_pass" not in content, "bob password must be hashed"
        # Each line should have user:hash format where hash is non-trivial
        for line in content.strip().splitlines():
            parts = line.split(":", 1)
            assert len(parts) == 2, f"Invalid htpasswd line: {line}"
            assert len(parts[1]) > 10, f"Password hash too short, likely not hashed: {line}"


# ===========================================================================
# 3. SSL certificate tests
# ===========================================================================

class TestSSLCertificate:
    """Verify self-signed SSL certificate and key exist with correct CN."""

    def test_cert_exists(self):
        assert os.path.isfile("/etc/nginx/ssl/webdav.crt"), "SSL certificate must exist"

    def test_key_exists(self):
        assert os.path.isfile("/etc/nginx/ssl/webdav.key"), "SSL key must exist"

    def test_cert_not_empty(self):
        assert os.path.getsize("/etc/nginx/ssl/webdav.crt") > 0, "Certificate must not be empty"

    def test_key_not_empty(self):
        assert os.path.getsize("/etc/nginx/ssl/webdav.key") > 0, "Key must not be empty"

    def test_cert_cn_is_localhost(self):
        """Certificate subject CN must be localhost."""
        result = run("openssl x509 -in /etc/nginx/ssl/webdav.crt -noout -subject")
        assert result.returncode == 0, "Failed to read certificate"
        subject = result.stdout.strip()
        assert "CN" in subject and "localhost" in subject, \
            f"Certificate CN must be localhost, got: {subject}"

    def test_cert_is_valid_x509(self):
        """Certificate must be a valid X.509 certificate."""
        result = run("openssl x509 -in /etc/nginx/ssl/webdav.crt -noout -text")
        assert result.returncode == 0, "Certificate is not valid X.509"

    def test_key_is_valid(self):
        """Key must be a valid RSA/EC private key."""
        result = run("openssl pkey -in /etc/nginx/ssl/webdav.key -noout")
        assert result.returncode == 0, "Key file is not a valid private key"


# ===========================================================================
# 4. Nginx configuration tests
# ===========================================================================

class TestNginxConfig:
    """Verify Nginx configuration file content and validity."""

    def test_config_file_exists(self):
        assert os.path.isfile("/etc/nginx/sites-enabled/webdav"), \
            "Nginx config must exist at /etc/nginx/sites-enabled/webdav"

    def test_default_site_removed(self):
        assert not os.path.exists("/etc/nginx/sites-enabled/default"), \
            "Default site must be removed"

    def test_config_passes_nginx_t(self):
        result = run("nginx -t")
        # nginx -t outputs to stderr
        combined = result.stdout + result.stderr
        assert result.returncode == 0, f"nginx -t failed: {combined}"

    def _read_config(self):
        with open("/etc/nginx/sites-enabled/webdav") as f:
            return f.read()

    def test_listens_on_443_ssl(self):
        cfg = self._read_config()
        assert re.search(r"listen\s+443\s+ssl", cfg), \
            "Config must listen on port 443 with SSL"

    def test_server_name_localhost(self):
        cfg = self._read_config()
        assert re.search(r"server_name\s+localhost", cfg), \
            "server_name must be localhost"

    def test_ssl_certificate_path(self):
        cfg = self._read_config()
        assert "/etc/nginx/ssl/webdav.crt" in cfg, \
            "Config must reference SSL certificate"

    def test_ssl_key_path(self):
        cfg = self._read_config()
        assert "/etc/nginx/ssl/webdav.key" in cfg, \
            "Config must reference SSL key"

    def test_dav_methods(self):
        cfg = self._read_config()
        assert re.search(r"dav_methods\s+.*PUT", cfg), "Must have PUT in dav_methods"
        assert re.search(r"dav_methods\s+.*DELETE", cfg), "Must have DELETE in dav_methods"
        assert re.search(r"dav_methods\s+.*MKNOD", cfg), "Must have MKNOD in dav_methods"
        assert re.search(r"dav_methods\s+.*COPY", cfg), "Must have COPY in dav_methods"
        assert re.search(r"dav_methods\s+.*MOVE", cfg), "Must have MOVE in dav_methods"

    def test_dav_ext_methods(self):
        cfg = self._read_config()
        assert re.search(r"dav_ext_methods\s+.*PROPFIND", cfg), "Must have PROPFIND"
        assert re.search(r"dav_ext_methods\s+.*OPTIONS", cfg), "Must have OPTIONS"

    def test_auth_basic_realm(self):
        cfg = self._read_config()
        assert re.search(r'auth_basic\s+"WebDAV"', cfg) or \
               re.search(r"auth_basic\s+'WebDAV'", cfg) or \
               re.search(r"auth_basic\s+WebDAV", cfg), \
            'auth_basic realm must be "WebDAV"'

    def test_htpasswd_referenced(self):
        cfg = self._read_config()
        assert "/etc/nginx/.htpasswd" in cfg, "Config must reference htpasswd file"

    def test_autoindex_on(self):
        cfg = self._read_config()
        assert re.search(r"autoindex\s+on", cfg), "autoindex must be on"

    def test_create_full_put_path_on(self):
        cfg = self._read_config()
        assert re.search(r"create_full_put_path\s+on", cfg), "create_full_put_path must be on"

    def test_client_body_temp_path(self):
        cfg = self._read_config()
        assert "/tmp/nginx_dav" in cfg, "client_body_temp_path must be /tmp/nginx_dav"

    def test_dav_access(self):
        cfg = self._read_config()
        assert re.search(r"dav_access\s+user:rw\s+group:r", cfg), \
            "dav_access must be user:rw group:r"

    def test_location_webdav_alice(self):
        cfg = self._read_config()
        assert re.search(r"location\s+/webdav/alice/", cfg), \
            "Must have location block for /webdav/alice/"

    def test_location_webdav_bob(self):
        cfg = self._read_config()
        assert re.search(r"location\s+/webdav/bob/", cfg), \
            "Must have location block for /webdav/bob/"


# ===========================================================================
# 5. Nginx service state tests
# ===========================================================================

class TestNginxService:
    """Verify Nginx is running."""

    def test_nginx_process_running(self):
        result = run("pgrep -x nginx")
        assert result.returncode == 0, "Nginx process must be running"

    def test_nginx_listening_on_443(self):
        """Nginx must be listening on port 443."""
        result = run("ss -tlnp | grep ':443'")
        assert result.returncode == 0 and "443" in result.stdout, \
            "Nginx must be listening on port 443"


# ===========================================================================
# 6. Functional HTTP tests (the core verification)
# ===========================================================================

class TestFunctionalHTTP:
    """
    End-to-end HTTP tests using curl against the running server.
    These are the most important tests — they verify the actual behavior.
    """

    # --- Authentication tests ---

    def test_unauthenticated_returns_401(self):
        """Unauthenticated request to /webdav/ must return 401."""
        code = curl("https://localhost/webdav/")
        assert code == 401, f"Unauthenticated request should return 401, got {code}"

    def test_unauthenticated_alice_dir_returns_401(self):
        """Unauthenticated request to /webdav/alice/ must return 401."""
        code = curl("https://localhost/webdav/alice/")
        assert code == 401, f"Unauthenticated request should return 401, got {code}"

    def test_unauthenticated_bob_dir_returns_401(self):
        """Unauthenticated request to /webdav/bob/ must return 401."""
        code = curl("https://localhost/webdav/bob/")
        assert code == 401, f"Unauthenticated request should return 401, got {code}"

    def test_wrong_password_returns_401(self):
        """Wrong password must return 401."""
        code = curl("https://localhost/webdav/alice/", user="alice:wrong_pass")
        assert code == 401, f"Wrong password should return 401, got {code}"

    # --- Alice access tests ---

    def test_alice_access_own_dir(self):
        """Alice accessing /webdav/alice/ should get 200 or 207."""
        code = curl("https://localhost/webdav/alice/", user="alice:alice_pass")
        assert code in (200, 207), \
            f"Alice accessing own dir should return 200/207, got {code}"

    def test_alice_blocked_from_bob_dir(self):
        """Alice accessing /webdav/bob/ must get 403."""
        code = curl("https://localhost/webdav/bob/", user="alice:alice_pass")
        assert code == 403, \
            f"Alice accessing bob's dir should return 403, got {code}"

    # --- Bob access tests ---

    def test_bob_access_own_dir(self):
        """Bob accessing /webdav/bob/ should get 200 or 207."""
        code = curl("https://localhost/webdav/bob/", user="bob:bob_pass")
        assert code in (200, 207), \
            f"Bob accessing own dir should return 200/207, got {code}"

    def test_bob_blocked_from_alice_dir(self):
        """Bob accessing /webdav/alice/ must get 403."""
        code = curl("https://localhost/webdav/alice/", user="bob:bob_pass")
        assert code == 403, \
            f"Bob accessing alice's dir should return 403, got {code}"

    # --- WebDAV operation tests ---

    def test_alice_put_file(self):
        """Alice should be able to PUT a file in her directory."""
        code = curl(
            "https://localhost/webdav/alice/test_put.txt",
            user="alice:alice_pass",
            method="PUT",
            data="hello from alice",
        )
        assert code in (201, 204), \
            f"Alice PUT should return 201/204, got {code}"

    def test_alice_put_file_persisted(self):
        """File uploaded by alice must exist on disk."""
        # First ensure the file is uploaded
        curl(
            "https://localhost/webdav/alice/verify_persist.txt",
            user="alice:alice_pass",
            method="PUT",
            data="persistence check",
        )
        time.sleep(0.5)
        assert os.path.isfile("/srv/webdav/alice/verify_persist.txt"), \
            "Uploaded file must exist on disk at /srv/webdav/alice/verify_persist.txt"
        with open("/srv/webdav/alice/verify_persist.txt") as f:
            content = f.read()
        assert "persistence check" in content, \
            f"File content mismatch, got: {content!r}"

    def test_bob_put_file(self):
        """Bob should be able to PUT a file in his directory."""
        code = curl(
            "https://localhost/webdav/bob/test_put.txt",
            user="bob:bob_pass",
            method="PUT",
            data="hello from bob",
        )
        assert code in (201, 204), \
            f"Bob PUT should return 201/204, got {code}"

    def test_alice_cannot_put_in_bob_dir(self):
        """Alice must not be able to PUT files in Bob's directory."""
        code = curl(
            "https://localhost/webdav/bob/alice_intruder.txt",
            user="alice:alice_pass",
            method="PUT",
            data="should fail",
        )
        assert code == 403, \
            f"Alice PUT in bob's dir should return 403, got {code}"

    def test_bob_cannot_put_in_alice_dir(self):
        """Bob must not be able to PUT files in Alice's directory."""
        code = curl(
            "https://localhost/webdav/alice/bob_intruder.txt",
            user="bob:bob_pass",
            method="PUT",
            data="should fail",
        )
        assert code == 403, \
            f"Bob PUT in alice's dir should return 403, got {code}"

    def test_alice_delete_file(self):
        """Alice should be able to DELETE a file in her directory."""
        # First create a file to delete
        curl(
            "https://localhost/webdav/alice/to_delete.txt",
            user="alice:alice_pass",
            method="PUT",
            data="delete me",
        )
        time.sleep(0.5)
        code = curl(
            "https://localhost/webdav/alice/to_delete.txt",
            user="alice:alice_pass",
            method="DELETE",
        )
        assert code in (200, 204), \
            f"Alice DELETE should return 200/204, got {code}"

    def test_webdav_root_accessible_by_both(self):
        """Both users should be able to access /webdav/ root."""
        code_alice = curl("https://localhost/webdav/", user="alice:alice_pass")
        code_bob = curl("https://localhost/webdav/", user="bob:bob_pass")
        assert code_alice in (200, 207), \
            f"Alice accessing /webdav/ should return 200/207, got {code_alice}"
        assert code_bob in (200, 207), \
            f"Bob accessing /webdav/ should return 200/207, got {code_bob}"
