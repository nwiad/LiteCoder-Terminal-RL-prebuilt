"""
Tests for Deploy Secure LEMP Stack task.

Validates that the agent correctly created deploy.sh, verify.sh,
and that the deployment produced all required configurations, files,
and security hardening as specified in instruction.md.
"""

import os
import re
import stat
import subprocess


# =============================================================================
# Helper utilities
# =============================================================================

def file_exists(path):
    return os.path.isfile(path)

def dir_exists(path):
    return os.path.isdir(path)

def is_symlink(path):
    return os.path.islink(path)

def read_file(path):
    """Read file content, return empty string if missing."""
    try:
        with open(path, "r") as f:
            return f.read()
    except (FileNotFoundError, PermissionError, UnicodeDecodeError):
        return ""

def is_executable(path):
    """Check if file has executable permission."""
    if not os.path.isfile(path):
        return False
    st = os.stat(path)
    return bool(st.st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH))

def run_cmd(cmd, timeout=10):
    """Run a shell command and return (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "", "timeout"
    except Exception as e:
        return -1, "", str(e)


# =============================================================================
# 1. Script existence, executability, and shebang
# =============================================================================

class TestScriptFiles:
    def test_deploy_sh_exists(self):
        assert file_exists("/app/deploy.sh"), "deploy.sh must exist at /app/deploy.sh"

    def test_deploy_sh_executable(self):
        assert is_executable("/app/deploy.sh"), "deploy.sh must be executable"

    def test_deploy_sh_shebang(self):
        content = read_file("/app/deploy.sh")
        assert content.startswith("#!/bin/bash"), "deploy.sh must start with #!/bin/bash shebang"

    def test_verify_sh_exists(self):
        assert file_exists("/app/verify.sh"), "verify.sh must exist at /app/verify.sh"

    def test_verify_sh_executable(self):
        assert is_executable("/app/verify.sh"), "verify.sh must be executable"

    def test_verify_sh_shebang(self):
        content = read_file("/app/verify.sh")
        assert content.startswith("#!/bin/bash"), "verify.sh must start with #!/bin/bash shebang"


# =============================================================================
# 2. Deployment Report
# =============================================================================

class TestDeploymentReport:
    REPORT_PATH = "/app/deployment_report.txt"

    def test_report_exists(self):
        assert file_exists(self.REPORT_PATH), "deployment_report.txt must exist"

    def test_report_not_empty(self):
        content = read_file(self.REPORT_PATH)
        assert len(content.strip()) > 0, "deployment_report.txt must not be empty"

    def test_report_nginx_installed(self):
        content = read_file(self.REPORT_PATH)
        assert re.search(r"^nginx\s*=\s*installed\s*$", content, re.MULTILINE), \
            "Report must contain 'nginx=installed'"

    def test_report_mariadb_installed(self):
        content = read_file(self.REPORT_PATH)
        assert re.search(r"^mariadb\s*=\s*installed\s*$", content, re.MULTILINE), \
            "Report must contain 'mariadb=installed'"

    def test_report_php_fpm_installed(self):
        content = read_file(self.REPORT_PATH)
        assert re.search(r"^php-fpm\s*=\s*installed\s*$", content, re.MULTILINE), \
            "Report must contain 'php-fpm=installed'"

    def test_report_ufw_active(self):
        content = read_file(self.REPORT_PATH)
        assert re.search(r"^ufw\s*=\s*active\s*$", content, re.MULTILINE), \
            "Report must contain 'ufw=active'"

    def test_report_fail2ban_installed(self):
        content = read_file(self.REPORT_PATH)
        assert re.search(r"^fail2ban\s*=\s*installed\s*$", content, re.MULTILINE), \
            "Report must contain 'fail2ban=installed'"

    def test_report_ssl_configured(self):
        content = read_file(self.REPORT_PATH)
        assert re.search(r"^ssl\s*=\s*configured\s*$", content, re.MULTILINE), \
            "Report must contain 'ssl=configured'"

    def test_report_firewall_ports(self):
        content = read_file(self.REPORT_PATH)
        assert re.search(r"^firewall_ports\s*=\s*22\s*,\s*80\s*,\s*443\s*$", content, re.MULTILINE), \
            "Report must contain 'firewall_ports=22,80,443'"

    def test_report_has_all_seven_lines(self):
        content = read_file(self.REPORT_PATH)
        lines = [l.strip() for l in content.strip().splitlines() if l.strip()]
        # Must have at least 7 key=value lines
        kv_lines = [l for l in lines if "=" in l]
        assert len(kv_lines) >= 7, f"Report must have at least 7 key=value lines, found {len(kv_lines)}"



# =============================================================================
# 3. Nginx Configuration
# =============================================================================

class TestNginxConfig:
    CONFIG_PATH = "/etc/nginx/sites-available/webapp"

    def test_nginx_config_exists(self):
        assert file_exists(self.CONFIG_PATH), "Nginx config must exist at /etc/nginx/sites-available/webapp"

    def test_nginx_config_not_empty(self):
        content = read_file(self.CONFIG_PATH)
        assert len(content.strip()) > 50, "Nginx config must have meaningful content"

    def test_nginx_listen_80(self):
        content = read_file(self.CONFIG_PATH)
        assert re.search(r"listen\s+80", content), "Nginx config must listen on port 80"

    def test_nginx_listen_443(self):
        content = read_file(self.CONFIG_PATH)
        assert re.search(r"listen\s+443", content), "Nginx config must listen on port 443"

    def test_nginx_ssl_certificate(self):
        content = read_file(self.CONFIG_PATH)
        assert re.search(r"ssl_certificate\s+/etc/ssl/certs/webapp\.crt", content), \
            "Nginx config must reference SSL cert at /etc/ssl/certs/webapp.crt"

    def test_nginx_ssl_key(self):
        content = read_file(self.CONFIG_PATH)
        assert re.search(r"ssl_certificate_key\s+/etc/ssl/private/webapp\.key", content), \
            "Nginx config must reference SSL key at /etc/ssl/private/webapp.key"

    def test_nginx_fastcgi_pass(self):
        content = read_file(self.CONFIG_PATH)
        assert re.search(r"fastcgi_pass", content), \
            "Nginx config must include fastcgi_pass directive for PHP-FPM"

    def test_nginx_server_name(self):
        content = read_file(self.CONFIG_PATH)
        assert re.search(r"server_name\s+localhost", content), \
            "Nginx config must set server_name to localhost"

    def test_nginx_document_root(self):
        content = read_file(self.CONFIG_PATH)
        assert re.search(r"root\s+/var/www/webapp", content), \
            "Nginx config must set document root to /var/www/webapp"

    def test_site_enabled_symlink(self):
        symlink_path = "/etc/nginx/sites-enabled/webapp"
        assert is_symlink(symlink_path) or file_exists(symlink_path), \
            "webapp must be enabled in /etc/nginx/sites-enabled/"



# =============================================================================
# 4. SSL Certificates
# =============================================================================

class TestSSLCertificates:
    def test_ssl_cert_exists(self):
        assert file_exists("/etc/ssl/certs/webapp.crt"), "SSL cert must exist at /etc/ssl/certs/webapp.crt"

    def test_ssl_key_exists(self):
        assert file_exists("/etc/ssl/private/webapp.key"), "SSL key must exist at /etc/ssl/private/webapp.key"

    def test_ssl_cert_not_empty(self):
        content = read_file("/etc/ssl/certs/webapp.crt")
        assert "BEGIN CERTIFICATE" in content, "SSL cert must be a valid PEM certificate"

    def test_ssl_key_not_empty(self):
        content = read_file("/etc/ssl/private/webapp.key")
        assert "BEGIN" in content and "KEY" in content, "SSL key must be a valid PEM key"

    def test_ssl_cert_cn_localhost(self):
        """Verify the certificate has CN=localhost using openssl."""
        rc, stdout, _ = run_cmd(
            "openssl x509 -in /etc/ssl/certs/webapp.crt -noout -subject 2>/dev/null"
        )
        if rc == 0:
            assert "localhost" in stdout, \
                f"SSL cert CN must be localhost, got: {stdout}"
        else:
            # openssl might not be available; check cert file is non-trivial
            content = read_file("/etc/ssl/certs/webapp.crt")
            assert len(content) > 100, "SSL cert must have substantial content"

    def test_ssl_cert_is_self_signed(self):
        """Verify the cert issuer matches subject (self-signed)."""
        rc_subj, subj, _ = run_cmd(
            "openssl x509 -in /etc/ssl/certs/webapp.crt -noout -subject 2>/dev/null"
        )
        rc_iss, issuer, _ = run_cmd(
            "openssl x509 -in /etc/ssl/certs/webapp.crt -noout -issuer 2>/dev/null"
        )
        if rc_subj == 0 and rc_iss == 0:
            # For self-signed, subject and issuer should both contain localhost
            assert "localhost" in issuer, \
                "Self-signed cert issuer should contain localhost"


# =============================================================================
# 5. PHP Files and Document Root
# =============================================================================

class TestPHPFiles:
    def test_document_root_exists(self):
        assert dir_exists("/var/www/webapp"), "/var/www/webapp directory must exist"

    def test_index_php_exists(self):
        assert file_exists("/var/www/webapp/index.php"), "index.php must exist"

    def test_index_php_content(self):
        content = read_file("/var/www/webapp/index.php")
        assert "LEMP Stack Operational" in content, \
            "index.php must output 'LEMP Stack Operational'"

    def test_index_php_is_php(self):
        content = read_file("/var/www/webapp/index.php")
        assert "<?php" in content or "<?" in content, \
            "index.php must contain PHP code"

    def test_info_php_exists(self):
        assert file_exists("/var/www/webapp/info.php"), "info.php must exist"

    def test_info_php_content(self):
        content = read_file("/var/www/webapp/info.php")
        assert "phpinfo()" in content, \
            "info.php must contain phpinfo() call"

    def test_document_root_ownership(self):
        """Check /var/www/webapp is owned by www-data."""
        rc, stdout, _ = run_cmd("stat -c '%U:%G' /var/www/webapp 2>/dev/null")
        if rc == 0:
            assert "www-data" in stdout, \
                f"/var/www/webapp must be owned by www-data, got: {stdout}"



# =============================================================================
# 6. Fail2ban Configuration
# =============================================================================

class TestFail2ban:
    JAIL_PATH = "/etc/fail2ban/jail.local"

    def test_jail_local_exists(self):
        assert file_exists(self.JAIL_PATH), "fail2ban jail.local must exist"

    def test_jail_local_not_empty(self):
        content = read_file(self.JAIL_PATH)
        assert len(content.strip()) > 20, "jail.local must have meaningful content"

    def test_sshd_jail_defined(self):
        content = read_file(self.JAIL_PATH)
        assert re.search(r"\[\s*sshd\s*\]", content), \
            "jail.local must define [sshd] jail"

    def test_nginx_http_auth_jail_defined(self):
        content = read_file(self.JAIL_PATH)
        assert re.search(r"\[\s*nginx-http-auth\s*\]", content), \
            "jail.local must define [nginx-http-auth] jail"

    def test_sshd_enabled(self):
        content = read_file(self.JAIL_PATH)
        # Find the sshd section and check enabled = true
        sshd_match = re.search(
            r"\[\s*sshd\s*\](.*?)(?=\[|\Z)", content, re.DOTALL
        )
        assert sshd_match, "sshd jail section not found"
        section = sshd_match.group(1)
        assert re.search(r"enabled\s*=\s*true", section, re.IGNORECASE), \
            "sshd jail must be enabled"

    def test_sshd_maxretry(self):
        content = read_file(self.JAIL_PATH)
        sshd_match = re.search(
            r"\[\s*sshd\s*\](.*?)(?=\[|\Z)", content, re.DOTALL
        )
        assert sshd_match, "sshd jail section not found"
        section = sshd_match.group(1)
        assert re.search(r"maxretry\s*=\s*3", section), \
            "sshd jail must have maxretry = 3"

    def test_sshd_bantime(self):
        content = read_file(self.JAIL_PATH)
        sshd_match = re.search(
            r"\[\s*sshd\s*\](.*?)(?=\[|\Z)", content, re.DOTALL
        )
        assert sshd_match, "sshd jail section not found"
        section = sshd_match.group(1)
        assert re.search(r"bantime\s*=\s*3600", section), \
            "sshd jail must have bantime = 3600"

    def test_nginx_http_auth_enabled(self):
        content = read_file(self.JAIL_PATH)
        nginx_match = re.search(
            r"\[\s*nginx-http-auth\s*\](.*?)(?=\[|\Z)", content, re.DOTALL
        )
        assert nginx_match, "nginx-http-auth jail section not found"
        section = nginx_match.group(1)
        assert re.search(r"enabled\s*=\s*true", section, re.IGNORECASE), \
            "nginx-http-auth jail must be enabled"

    def test_nginx_http_auth_maxretry(self):
        content = read_file(self.JAIL_PATH)
        nginx_match = re.search(
            r"\[\s*nginx-http-auth\s*\](.*?)(?=\[|\Z)", content, re.DOTALL
        )
        assert nginx_match, "nginx-http-auth jail section not found"
        section = nginx_match.group(1)
        assert re.search(r"maxretry\s*=\s*3", section), \
            "nginx-http-auth jail must have maxretry = 3"

    def test_nginx_http_auth_bantime(self):
        content = read_file(self.JAIL_PATH)
        nginx_match = re.search(
            r"\[\s*nginx-http-auth\s*\](.*?)(?=\[|\Z)", content, re.DOTALL
        )
        assert nginx_match, "nginx-http-auth jail section not found"
        section = nginx_match.group(1)
        assert re.search(r"bantime\s*=\s*3600", section), \
            "nginx-http-auth jail must have bantime = 3600"



# =============================================================================
# 7. UFW Firewall
# =============================================================================

class TestUFW:
    def test_ufw_installed(self):
        """Check ufw binary exists."""
        rc, _, _ = run_cmd("which ufw")
        assert rc == 0, "ufw must be installed"

    def test_ufw_status_active(self):
        """Check UFW reports active status."""
        rc, stdout, _ = run_cmd("ufw status 2>/dev/null")
        if rc == 0:
            assert re.search(r"active", stdout, re.IGNORECASE), \
                f"UFW must be active, got: {stdout}"

    def test_ufw_allows_ssh(self):
        """Check port 22 is allowed."""
        rc, stdout, _ = run_cmd("ufw status 2>/dev/null")
        if rc == 0:
            assert re.search(r"22(/tcp)?\s+ALLOW", stdout, re.IGNORECASE), \
                "UFW must allow port 22 (SSH)"

    def test_ufw_allows_http(self):
        """Check port 80 is allowed."""
        rc, stdout, _ = run_cmd("ufw status 2>/dev/null")
        if rc == 0:
            assert re.search(r"80(/tcp)?\s+ALLOW", stdout, re.IGNORECASE), \
                "UFW must allow port 80 (HTTP)"

    def test_ufw_allows_https(self):
        """Check port 443 is allowed."""
        rc, stdout, _ = run_cmd("ufw status 2>/dev/null")
        if rc == 0:
            assert re.search(r"443(/tcp)?\s+ALLOW", stdout, re.IGNORECASE), \
                "UFW must allow port 443 (HTTPS)"

    def test_ufw_default_deny_incoming(self):
        """Check default incoming policy is deny."""
        rc, stdout, _ = run_cmd("ufw status verbose 2>/dev/null")
        if rc == 0:
            assert re.search(r"Default:.*deny.*incoming", stdout, re.IGNORECASE), \
                "UFW default incoming policy must be deny"


# =============================================================================
# 8. Package Installation (binaries exist)
# =============================================================================

class TestPackagesInstalled:
    def test_nginx_binary(self):
        rc, _, _ = run_cmd("which nginx")
        assert rc == 0, "nginx binary must be installed"

    def test_mariadb_binary(self):
        """MariaDB or mysql client binary must exist."""
        rc1, _, _ = run_cmd("which mariadb")
        rc2, _, _ = run_cmd("which mysql")
        assert rc1 == 0 or rc2 == 0, "mariadb or mysql binary must be installed"

    def test_php_fpm_binary(self):
        """php-fpm binary must exist somewhere."""
        rc, stdout, _ = run_cmd(
            "find /usr/sbin /usr/bin -name 'php-fpm*' -type f 2>/dev/null | head -1"
        )
        if rc == 0 and stdout:
            assert len(stdout) > 0
        else:
            # Fallback: check dpkg
            rc2, stdout2, _ = run_cmd("dpkg -l | grep php.*fpm")
            assert rc2 == 0 and "php" in stdout2, "php-fpm must be installed"

    def test_fail2ban_binary(self):
        rc, _, _ = run_cmd("which fail2ban-client || which fail2ban-server")
        assert rc == 0, "fail2ban must be installed"


# =============================================================================
# 9. Verification Script Output
# =============================================================================

class TestVerifyScript:
    """Run verify.sh and check its output contains all PASS results."""

    def _run_verify(self):
        rc, stdout, stderr = run_cmd("bash /app/verify.sh 2>/dev/null", timeout=30)
        return rc, stdout

    def test_verify_script_runs(self):
        rc, stdout = self._run_verify()
        assert rc == 0 or len(stdout) > 0, "verify.sh must produce output"

    def test_verify_nginx_installed_pass(self):
        _, stdout = self._run_verify()
        assert "NGINX_INSTALLED=PASS" in stdout, \
            "verify.sh must report NGINX_INSTALLED=PASS"

    def test_verify_mariadb_installed_pass(self):
        _, stdout = self._run_verify()
        assert "MARIADB_INSTALLED=PASS" in stdout, \
            "verify.sh must report MARIADB_INSTALLED=PASS"

    def test_verify_ssl_cert_pass(self):
        _, stdout = self._run_verify()
        assert "SSL_CERT_EXISTS=PASS" in stdout, \
            "verify.sh must report SSL_CERT_EXISTS=PASS"

    def test_verify_ssl_key_pass(self):
        _, stdout = self._run_verify()
        assert "SSL_KEY_EXISTS=PASS" in stdout, \
            "verify.sh must report SSL_KEY_EXISTS=PASS"

    def test_verify_nginx_config_pass(self):
        _, stdout = self._run_verify()
        assert "NGINX_CONFIG_EXISTS=PASS" in stdout, \
            "verify.sh must report NGINX_CONFIG_EXISTS=PASS"

    def test_verify_site_enabled_pass(self):
        _, stdout = self._run_verify()
        assert "SITE_ENABLED=PASS" in stdout, \
            "verify.sh must report SITE_ENABLED=PASS"

    def test_verify_document_root_pass(self):
        _, stdout = self._run_verify()
        assert "DOCUMENT_ROOT_EXISTS=PASS" in stdout, \
            "verify.sh must report DOCUMENT_ROOT_EXISTS=PASS"

    def test_verify_index_php_pass(self):
        _, stdout = self._run_verify()
        assert "INDEX_PHP_EXISTS=PASS" in stdout, \
            "verify.sh must report INDEX_PHP_EXISTS=PASS"

    def test_verify_info_php_pass(self):
        _, stdout = self._run_verify()
        assert "INFO_PHP_EXISTS=PASS" in stdout, \
            "verify.sh must report INFO_PHP_EXISTS=PASS"

    def test_verify_fail2ban_jail_pass(self):
        _, stdout = self._run_verify()
        assert "FAIL2BAN_JAIL_EXISTS=PASS" in stdout, \
            "verify.sh must report FAIL2BAN_JAIL_EXISTS=PASS"

    def test_verify_report_exists_pass(self):
        _, stdout = self._run_verify()
        assert "REPORT_EXISTS=PASS" in stdout, \
            "verify.sh must report REPORT_EXISTS=PASS"

    def test_verify_has_all_13_checks(self):
        """verify.sh must output at least 13 CHECK=PASS/FAIL lines."""
        _, stdout = self._run_verify()
        check_lines = re.findall(r"^\w+=(?:PASS|FAIL)$", stdout, re.MULTILINE)
        assert len(check_lines) >= 13, \
            f"verify.sh must output at least 13 check lines, found {len(check_lines)}"

    def test_verify_no_failures_except_ufw(self):
        """All checks except possibly UFW_ENABLED should PASS.
        UFW may not work in all container environments."""
        _, stdout = self._run_verify()
        fail_lines = re.findall(r"^(\w+)=FAIL$", stdout, re.MULTILINE)
        # Allow UFW_ENABLED to fail in container environments
        non_ufw_fails = [f for f in fail_lines if f != "UFW_ENABLED"]
        assert len(non_ufw_fails) == 0, \
            f"These checks should not fail: {non_ufw_fails}"
