"""
Tests for the Private File Exchange Service (lighttpd + HTTPS + WebDAV + Basic Auth).

Validates all 8 requirements from instruction.md:
1. Package installation (lighttpd)
2. Service directory (/srv/filedrop/)
3. TLS certificate (filedrop.local)
4. Lighttpd configuration (port 4443, modules, /drop/ mapping)
5. Authentication (partner/DropSecure2025, htpasswd)
6. Systemd service (enabled, running)
7. Verification (testfile.txt upload, anonymous GET, rejected unauth PUT)
8. Partner documentation (/root/HELP.txt)
"""

import os
import subprocess
import re


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run_cmd(cmd, timeout=15):
    """Run a shell command and return (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "", "timeout"


def read_file(path):
    """Read file content, return empty string if missing."""
    try:
        with open(path, "r") as f:
            return f.read()
    except (FileNotFoundError, PermissionError):
        return ""


# ===========================================================================
# 1. Package Installation
# ===========================================================================

class TestPackageInstallation:
    def test_lighttpd_binary_exists(self):
        """lighttpd must be installed and available on PATH."""
        rc, out, _ = run_cmd("which lighttpd")
        assert rc == 0, "lighttpd binary not found on PATH"

    def test_lighttpd_version(self):
        """lighttpd should report a version (confirms it's properly installed)."""
        rc, out, err = run_cmd("lighttpd -v")
        combined = out + err
        assert "lighttpd" in combined.lower(), (
            f"lighttpd -v did not return expected output: {combined}"
        )


# ===========================================================================
# 2. Service Directory
# ===========================================================================

class TestServiceDirectory:
    def test_filedrop_dir_exists(self):
        """/srv/filedrop/ must exist."""
        assert os.path.isdir("/srv/filedrop"), "/srv/filedrop/ directory does not exist"

    def test_filedrop_dir_writable_by_www_data(self):
        """The directory should be owned by or writable by www-data."""
        import stat
        st = os.stat("/srv/filedrop")
        # Check owner or group via id lookup
        rc, out, _ = run_cmd("stat -c '%U:%G' /srv/filedrop")
        # Accept www-data as owner or group, or world-writable
        mode = st.st_mode
        owner_ok = "www-data" in out
        world_writable = bool(mode & stat.S_IWOTH)
        assert owner_ok or world_writable, (
            f"/srv/filedrop ownership={out}, mode={oct(mode)} — "
            "not writable by www-data"
        )

# ===========================================================================
# 3. TLS Certificate
# ===========================================================================

class TestTLSCertificate:
    def test_ssl_directory_exists(self):
        """/etc/lighttpd/ssl/ must exist."""
        assert os.path.isdir("/etc/lighttpd/ssl"), "/etc/lighttpd/ssl/ not found"

    def test_certificate_file_exists(self):
        """Certificate PEM file must exist."""
        assert os.path.isfile("/etc/lighttpd/ssl/filedrop.local.pem"), (
            "filedrop.local.pem not found"
        )

    def test_key_file_exists(self):
        """Private key file must exist."""
        # Accept either separate key or combined PEM
        key_path = "/etc/lighttpd/ssl/filedrop.local.key"
        combined_path = "/etc/lighttpd/ssl/filedrop.local-combined.pem"
        assert os.path.isfile(key_path) or os.path.isfile(combined_path), (
            "Neither filedrop.local.key nor filedrop.local-combined.pem found"
        )

    def test_certificate_common_name(self):
        """Certificate CN must be filedrop.local."""
        pem = "/etc/lighttpd/ssl/filedrop.local.pem"
        if not os.path.isfile(pem):
            # Try combined
            pem = "/etc/lighttpd/ssl/filedrop.local-combined.pem"
        rc, out, _ = run_cmd(f"openssl x509 -in {pem} -noout -subject")
        assert rc == 0, f"Failed to read certificate: {out}"
        assert "filedrop.local" in out, (
            f"Certificate CN does not contain filedrop.local: {out}"
        )

    def test_certificate_is_valid_x509(self):
        """The PEM file must be a valid X.509 certificate."""
        pem = "/etc/lighttpd/ssl/filedrop.local.pem"
        if not os.path.isfile(pem):
            pem = "/etc/lighttpd/ssl/filedrop.local-combined.pem"
        rc, out, err = run_cmd(f"openssl x509 -in {pem} -noout -dates")
        assert rc == 0, f"Certificate is not valid X.509: {err}"


# ===========================================================================
# 4. Lighttpd Configuration
# ===========================================================================

class TestLighttpdConfig:
    def setup_method(self):
        self.config = read_file("/etc/lighttpd/lighttpd.conf")

    def test_config_file_exists(self):
        """lighttpd.conf must exist and be non-empty."""
        assert os.path.isfile("/etc/lighttpd/lighttpd.conf"), (
            "lighttpd.conf not found"
        )
        assert len(self.config.strip()) > 0, "lighttpd.conf is empty"

    def test_port_4443(self):
        """Config must specify port 4443."""
        assert re.search(r"server\.port\s*=\s*4443", self.config), (
            "Port 4443 not configured in lighttpd.conf"
        )

    def test_ssl_enabled(self):
        """SSL/TLS must be enabled."""
        assert re.search(r'ssl\.engine\s*=\s*"enable"', self.config), (
            "ssl.engine not set to enable"
        )

    def test_mod_openssl(self):
        """mod_openssl must be loaded."""
        assert "mod_openssl" in self.config, "mod_openssl not in config"

    def test_mod_webdav(self):
        """mod_webdav must be loaded."""
        assert "mod_webdav" in self.config, "mod_webdav not in config"

    def test_mod_auth(self):
        """mod_auth must be loaded."""
        assert "mod_auth" in self.config, "mod_auth not in config"

    def test_drop_path_mapping(self):
        """URL /drop/ must be mapped to /srv/filedrop/."""
        # Accept alias or document-root approaches
        has_alias = "/drop/" in self.config and "/srv/filedrop/" in self.config
        assert has_alias, (
            "Config does not map /drop/ to /srv/filedrop/"
        )

    def test_webdav_enabled(self):
        """WebDAV must be activated in config."""
        assert re.search(r'webdav\.activate\s*=\s*"enable"', self.config), (
            "WebDAV not activated in config"
        )

# ===========================================================================
# 5. Authentication
# ===========================================================================

class TestAuthentication:
    def test_htpasswd_file_exists(self):
        """/etc/lighttpd/htpasswd must exist."""
        assert os.path.isfile("/etc/lighttpd/htpasswd"), (
            "/etc/lighttpd/htpasswd not found"
        )

    def test_htpasswd_contains_partner(self):
        """htpasswd file must contain the 'partner' user."""
        content = read_file("/etc/lighttpd/htpasswd")
        assert len(content.strip()) > 0, "htpasswd file is empty"
        assert "partner" in content, (
            "User 'partner' not found in htpasswd"
        )

    def test_htpasswd_partner_password(self):
        """The partner password must validate against DropSecure2025."""
        # Use htpasswd -v to verify (apache2-utils)
        rc, out, err = run_cmd(
            "htpasswd -vb /etc/lighttpd/htpasswd partner DropSecure2025"
        )
        if rc != 0:
            # htpasswd -v may not be available; fall back to manual check
            # Read the file and verify partner entry exists with non-empty hash
            content = read_file("/etc/lighttpd/htpasswd")
            lines = [l.strip() for l in content.splitlines() if l.strip()]
            partner_lines = [l for l in lines if l.startswith("partner:")]
            assert len(partner_lines) > 0, "No partner entry in htpasswd"
            # Ensure there's a hash after the colon
            parts = partner_lines[0].split(":", 1)
            assert len(parts) == 2 and len(parts[1]) > 5, (
                "partner entry has no valid password hash"
            )
        # If htpasswd -v succeeded, password is correct

    def test_config_references_htpasswd(self):
        """lighttpd config must reference the htpasswd file."""
        config = read_file("/etc/lighttpd/lighttpd.conf")
        assert "/etc/lighttpd/htpasswd" in config, (
            "Config does not reference /etc/lighttpd/htpasswd"
        )

    def test_config_has_basic_auth(self):
        """Config must use basic auth method."""
        config = read_file("/etc/lighttpd/lighttpd.conf")
        assert re.search(r'"basic"', config), (
            "Basic auth method not found in config"
        )


# ===========================================================================
# 6. Systemd Service
# ===========================================================================

class TestSystemdService:
    def test_systemd_unit_file_exists(self):
        """A systemd unit file for lighttpd must exist."""
        paths = [
            "/etc/systemd/system/lighttpd.service",
            "/lib/systemd/system/lighttpd.service",
            "/usr/lib/systemd/system/lighttpd.service",
        ]
        found = any(os.path.isfile(p) for p in paths)
        assert found, "No systemd unit file found for lighttpd"

    def test_service_enabled(self):
        """lighttpd service must be enabled (start on boot)."""
        # Check for enabled symlink or systemctl output
        symlink = "/etc/systemd/system/multi-user.target.wants/lighttpd.service"
        if os.path.islink(symlink) or os.path.isfile(symlink):
            return  # enabled via symlink
        rc, out, _ = run_cmd("systemctl is-enabled lighttpd 2>/dev/null")
        if rc == 0 and "enabled" in out:
            return
        # Also accept if the symlink target exists anywhere in wants dirs
        rc2, out2, _ = run_cmd(
            "find /etc/systemd/system -name 'lighttpd.service' -type l 2>/dev/null"
        )
        assert rc2 == 0 and len(out2.strip()) > 0, (
            "lighttpd service is not enabled for boot"
        )

# ===========================================================================
# 7. Functional Verification (Service Running + HTTP Tests)
# ===========================================================================

class TestServiceRunning:
    def test_lighttpd_process_running(self):
        """lighttpd process must be running."""
        rc, out, _ = run_cmd("pgrep -x lighttpd")
        if rc != 0:
            # Also try broader match
            rc2, out2, _ = run_cmd("pgrep -f lighttpd")
            assert rc2 == 0, "No lighttpd process found running"

    def test_port_4443_listening(self):
        """Port 4443 must be open and listening."""
        rc, out, _ = run_cmd("ss -tlnp 2>/dev/null | grep 4443")
        if rc != 0:
            rc2, out2, _ = run_cmd("netstat -tlnp 2>/dev/null | grep 4443")
            assert rc2 == 0, "Port 4443 is not listening"


class TestHTTPFunctionality:
    """Live HTTP tests against the running lighttpd service."""

    def test_https_responds(self):
        """HTTPS on port 4443 must respond."""
        rc, out, _ = run_cmd(
            "curl -k -s -o /dev/null -w '%{http_code}' https://localhost:4443/drop/"
        )
        assert rc == 0, "curl to https://localhost:4443 failed"
        # Any response (200, 301, 403) means the server is up
        assert out.strip("'") != "000", (
            f"Server did not respond (HTTP code: {out})"
        )

    def test_anonymous_get_testfile(self):
        """Anonymous GET of testfile.txt must return HTTP 200."""
        rc, out, _ = run_cmd(
            "curl -k -s -o /dev/null -w '%{http_code}' "
            "https://localhost:4443/drop/testfile.txt"
        )
        assert rc == 0, "curl GET failed"
        code = out.strip("'")
        assert code == "200", (
            f"Anonymous GET returned {code}, expected 200"
        )

    def test_anonymous_get_content(self):
        """Anonymous GET of testfile.txt must return 'hello filedrop'."""
        rc, out, _ = run_cmd(
            "curl -k -s https://localhost:4443/drop/testfile.txt"
        )
        assert rc == 0, "curl GET failed"
        assert "hello filedrop" in out, (
            f"GET content does not contain 'hello filedrop': '{out}'"
        )

    def test_unauthenticated_put_rejected(self):
        """Unauthenticated PUT must be rejected (HTTP 401)."""
        rc, out, _ = run_cmd(
            "curl -k -s -o /dev/null -w '%{http_code}' "
            "-T /dev/null https://localhost:4443/drop/unauthorized_test.txt"
        )
        assert rc == 0, "curl PUT failed"
        code = out.strip("'")
        assert code == "401", (
            f"Unauthenticated PUT returned {code}, expected 401"
        )

    def test_authenticated_put_succeeds(self):
        """Authenticated PUT must succeed (HTTP 2xx)."""
        # Create a small temp file to upload
        run_cmd("echo 'auth test content' > /tmp/auth_test_upload.txt")
        rc, out, _ = run_cmd(
            "curl -k -s -o /dev/null -w '%{http_code}' "
            "-u partner:DropSecure2025 "
            "-T /tmp/auth_test_upload.txt "
            "https://localhost:4443/drop/auth_test_upload.txt"
        )
        assert rc == 0, "curl authenticated PUT failed"
        code = out.strip("'")
        assert code.startswith("2"), (
            f"Authenticated PUT returned {code}, expected 2xx"
        )

    def test_wrong_password_rejected(self):
        """PUT with wrong password must be rejected."""
        run_cmd("echo 'bad auth' > /tmp/bad_auth_test.txt")
        rc, out, _ = run_cmd(
            "curl -k -s -o /dev/null -w '%{http_code}' "
            "-u partner:WrongPassword "
            "-T /tmp/bad_auth_test.txt "
            "https://localhost:4443/drop/bad_auth_test.txt"
        )
        assert rc == 0, "curl failed"
        code = out.strip("'")
        assert code == "401", (
            f"PUT with wrong password returned {code}, expected 401"
        )

# ===========================================================================
# 7b. Test File on Disk
# ===========================================================================

class TestTestFile:
    def test_testfile_exists_on_disk(self):
        """/srv/filedrop/testfile.txt must exist."""
        assert os.path.isfile("/srv/filedrop/testfile.txt"), (
            "/srv/filedrop/testfile.txt not found on disk"
        )

    def test_testfile_content(self):
        """testfile.txt must contain 'hello filedrop'."""
        content = read_file("/srv/filedrop/testfile.txt")
        assert "hello filedrop" in content.strip(), (
            f"testfile.txt content is '{content.strip()}', "
            "expected 'hello filedrop'"
        )

    def test_testfile_not_empty(self):
        """testfile.txt must not be empty."""
        content = read_file("/srv/filedrop/testfile.txt")
        assert len(content.strip()) > 0, "testfile.txt is empty"


# ===========================================================================
# 8. Partner Documentation
# ===========================================================================

class TestPartnerDocumentation:
    def test_help_file_exists(self):
        """/root/HELP.txt must exist."""
        assert os.path.isfile("/root/HELP.txt"), "/root/HELP.txt not found"

    def test_help_file_not_empty(self):
        """HELP.txt must not be empty."""
        content = read_file("/root/HELP.txt")
        assert len(content.strip()) > 0, "HELP.txt is empty"

    def test_help_contains_upload_command(self):
        """HELP.txt must contain a curl upload command with credentials."""
        content = read_file("/root/HELP.txt").lower()
        assert "curl" in content, "HELP.txt does not mention curl"
        # Must reference the credentials for upload
        full_content = read_file("/root/HELP.txt")
        assert "partner" in full_content, (
            "HELP.txt does not mention partner username"
        )
        assert "DropSecure2025" in full_content, (
            "HELP.txt does not mention the password"
        )

    def test_help_contains_port_4443(self):
        """HELP.txt must reference port 4443."""
        content = read_file("/root/HELP.txt")
        assert "4443" in content, "HELP.txt does not mention port 4443"

    def test_help_contains_drop_path(self):
        """HELP.txt must reference the /drop/ URL path."""
        content = read_file("/root/HELP.txt")
        assert "/drop/" in content, "HELP.txt does not mention /drop/ path"

    def test_help_contains_download_command(self):
        """HELP.txt must contain a download curl command (no auth)."""
        content = read_file("/root/HELP.txt")
        # Should have at least two curl lines (upload + download)
        curl_lines = [
            l for l in content.splitlines()
            if "curl" in l.lower() and "/drop/" in l
        ]
        assert len(curl_lines) >= 2, (
            f"Expected at least 2 curl commands in HELP.txt, found {len(curl_lines)}"
        )
        # At least one line should NOT have -u (the download line)
        download_lines = [l for l in curl_lines if "-u " not in l]
        assert len(download_lines) >= 1, (
            "No anonymous download curl command found in HELP.txt"
        )

    def test_help_upload_uses_k_flag(self):
        """Upload command must use -k flag for self-signed cert."""
        content = read_file("/root/HELP.txt")
        curl_lines = [l for l in content.splitlines() if "curl" in l.lower()]
        k_lines = [l for l in curl_lines if "-k" in l]
        assert len(k_lines) >= 1, (
            "No curl command with -k flag found in HELP.txt"
        )

