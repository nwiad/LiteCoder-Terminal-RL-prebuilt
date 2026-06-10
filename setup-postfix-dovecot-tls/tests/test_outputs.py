"""
Tests for Mail Server Setup with Postfix, Dovecot, and TLS.

Validates that the agent correctly configured:
- Postfix (main.cf + master.cf)
- Dovecot (SSL, IMAP, auth)
- TLS certificates
- UFW firewall rules
- mailtest system user
- Cron job for queue monitoring
- Documentation file at /app/mail_server_doc.txt
- Running services
"""

import os
import re
import subprocess
import pwd


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def read_file(path):
    """Read a file and return its contents, or None if missing."""
    try:
        with open(path, "r") as f:
            return f.read()
    except (FileNotFoundError, PermissionError):
        return None


def run_cmd(cmd):
    """Run a shell command and return (stdout, returncode)."""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
    return result.stdout + result.stderr, result.returncode


def postfix_main_cf():
    return read_file("/etc/postfix/main.cf")


def postfix_master_cf():
    return read_file("/etc/postfix/master.cf")


# ---------------------------------------------------------------------------
# 1. Postfix main.cf
# ---------------------------------------------------------------------------

class TestPostfixMainCf:

    def test_main_cf_exists(self):
        content = postfix_main_cf()
        assert content is not None, "/etc/postfix/main.cf does not exist"
        assert len(content.strip()) > 0, "/etc/postfix/main.cf is empty"

    def test_myhostname(self):
        content = postfix_main_cf()
        assert content is not None
        assert re.search(r"^\s*myhostname\s*=\s*mail\.example\.tst\s*$", content, re.MULTILINE), \
            "myhostname must be set to mail.example.tst"

    def test_mydomain(self):
        content = postfix_main_cf()
        assert content is not None
        assert re.search(r"^\s*mydomain\s*=\s*example\.tst\s*$", content, re.MULTILINE), \
            "mydomain must be set to example.tst"

    def test_mydestination_includes_domain(self):
        content = postfix_main_cf()
        assert content is not None
        m = re.search(r"^\s*mydestination\s*=\s*(.+)$", content, re.MULTILINE)
        assert m, "mydestination not found in main.cf"
        dest = m.group(1)
        assert "example.tst" in dest, "mydestination must include example.tst"
        assert "mail.example.tst" in dest, "mydestination must include mail.example.tst"

    def test_mynetworks_includes_subnet(self):
        content = postfix_main_cf()
        assert content is not None
        m = re.search(r"^\s*mynetworks\s*=\s*(.+)$", content, re.MULTILINE)
        assert m, "mynetworks not found in main.cf"
        assert "192.168.0.0/24" in m.group(1), "mynetworks must include 192.168.0.0/24"

    def test_smtpd_banner(self):
        content = postfix_main_cf()
        assert content is not None
        # Banner may use $myhostname variable or literal value
        banner_match = re.search(r"^\s*smtpd_banner\s*=\s*(.+)$", content, re.MULTILINE)
        assert banner_match, "smtpd_banner not found in main.cf"
        banner_val = banner_match.group(1)
        assert "mail.example.tst" in banner_val or "$myhostname" in banner_val, \
            "smtpd_banner must contain mail.example.tst or $myhostname"

    def test_tls_cert_file_set(self):
        content = postfix_main_cf()
        assert content is not None
        m = re.search(r"^\s*smtpd_tls_cert_file\s*=\s*(\S+)", content, re.MULTILINE)
        assert m, "smtpd_tls_cert_file not set in main.cf"
        cert_path = m.group(1)
        assert os.path.isfile(cert_path), f"Certificate file {cert_path} does not exist"

    def test_tls_key_file_set(self):
        content = postfix_main_cf()
        assert content is not None
        m = re.search(r"^\s*smtpd_tls_key_file\s*=\s*(\S+)", content, re.MULTILINE)
        assert m, "smtpd_tls_key_file not set in main.cf"
        key_path = m.group(1)
        assert os.path.isfile(key_path), f"Key file {key_path} does not exist"

    def test_tls_security_level_may(self):
        content = postfix_main_cf()
        assert content is not None
        # The global setting should be 'may' (opportunistic on port 25)
        m = re.search(r"^\s*smtpd_tls_security_level\s*=\s*may\s*$", content, re.MULTILINE)
        assert m, "smtpd_tls_security_level must be set to 'may' in main.cf"

    def test_tls_mandatory_protocols_disallow_old(self):
        content = postfix_main_cf()
        assert content is not None
        m = re.search(r"^\s*smtpd_tls_mandatory_protocols\s*=\s*(.+)$", content, re.MULTILINE)
        assert m, "smtpd_tls_mandatory_protocols not set in main.cf"
        proto_val = m.group(1).lower()
        # Must disallow TLSv1 and TLSv1.1
        assert "!tlsv1" in proto_val.replace(" ", ""), \
            "smtpd_tls_mandatory_protocols must disallow TLSv1"
        assert "!tlsv1.1" in proto_val.replace(" ", ""), \
            "smtpd_tls_mandatory_protocols must disallow TLSv1.1"

    def test_recipient_restrictions(self):
        content = postfix_main_cf()
        assert content is not None
        m = re.search(r"^\s*smtpd_recipient_restrictions\s*=\s*(.+)$", content, re.MULTILINE)
        assert m, "smtpd_recipient_restrictions not found in main.cf"
        assert "reject_unauth_destination" in m.group(1), \
            "smtpd_recipient_restrictions must include reject_unauth_destination"

    def test_rate_limit(self):
        content = postfix_main_cf()
        assert content is not None
        m = re.search(r"^\s*smtpd_client_message_rate_limit\s*=\s*(\d+)", content, re.MULTILINE)
        assert m, "smtpd_client_message_rate_limit not set in main.cf"
        assert int(m.group(1)) > 0, "smtpd_client_message_rate_limit must be a positive integer"


# ---------------------------------------------------------------------------
# 2. Postfix master.cf — ports 25, 465, 587
# ---------------------------------------------------------------------------

class TestPostfixMasterCf:

    def test_master_cf_exists(self):
        content = postfix_master_cf()
        assert content is not None, "/etc/postfix/master.cf does not exist"
        assert len(content.strip()) > 0, "/etc/postfix/master.cf is empty"

    def test_smtp_port25_enabled(self):
        content = postfix_master_cf()
        assert content is not None
        # Line starting with 'smtp' (not 'smtps') as inet service
        assert re.search(r"^smtp\s+inet\s", content, re.MULTILINE), \
            "Port 25 (smtp inet) not enabled in master.cf"

    def test_smtps_port465_enabled(self):
        content = postfix_master_cf()
        assert content is not None
        assert re.search(r"^smtps\s+inet\s", content, re.MULTILINE), \
            "Port 465 (smtps inet) not enabled in master.cf"
        # Must have wrappermode=yes somewhere after smtps line
        assert re.search(r"smtpd_tls_wrappermode\s*=\s*yes", content), \
            "smtps must have smtpd_tls_wrappermode=yes"

    def test_submission_port587_enabled(self):
        content = postfix_master_cf()
        assert content is not None
        assert re.search(r"^submission\s+inet\s", content, re.MULTILINE), \
            "Port 587 (submission inet) not enabled in master.cf"
        assert re.search(r"smtpd_tls_security_level\s*=\s*encrypt", content), \
            "submission must have smtpd_tls_security_level=encrypt"


# ---------------------------------------------------------------------------
# 3. Dovecot Configuration
# ---------------------------------------------------------------------------

def _dovecot_conf_files():
    """Collect all dovecot config content from standard locations."""
    paths = [
        "/etc/dovecot/dovecot.conf",
        "/etc/dovecot/conf.d/10-ssl.conf",
        "/etc/dovecot/conf.d/10-master.conf",
        "/etc/dovecot/conf.d/10-auth.conf",
    ]
    combined = ""
    for p in paths:
        c = read_file(p)
        if c:
            combined += c + "\n"
    return combined


class TestDovecotConfig:

    def test_dovecot_conf_exists(self):
        content = read_file("/etc/dovecot/dovecot.conf")
        assert content is not None, "/etc/dovecot/dovecot.conf does not exist"

    def test_protocols_include_imap(self):
        combined = _dovecot_conf_files()
        assert re.search(r"^\s*protocols\s*=\s*.*imap", combined, re.MULTILINE), \
            "Dovecot protocols must include imap"

    def test_imaps_listener_port_993(self):
        combined = _dovecot_conf_files()
        # Look for inet_listener imaps block with port = 993
        assert re.search(r"inet_listener\s+imaps", combined), \
            "inet_listener imaps block not found in Dovecot config"
        assert re.search(r"port\s*=\s*993", combined), \
            "IMAPS listener must be on port 993"

    def test_imaps_listener_ssl_yes(self):
        combined = _dovecot_conf_files()
        # Within the imaps listener block, ssl = yes must appear
        # Use a broad search — the ssl = yes inside the imaps block
        imaps_block = re.search(
            r"inet_listener\s+imaps\s*\{([^}]*)\}", combined, re.DOTALL
        )
        assert imaps_block, "inet_listener imaps block not found"
        assert re.search(r"ssl\s*=\s*yes", imaps_block.group(1)), \
            "IMAPS listener must have ssl = yes"

    def test_plaintext_imap_disabled(self):
        combined = _dovecot_conf_files()
        # Port 143 should be disabled: port = 0 or listener removed
        imap_block = re.search(
            r"inet_listener\s+imap\s*\{([^}]*)\}", combined, re.DOTALL
        )
        if imap_block:
            assert re.search(r"port\s*=\s*0", imap_block.group(1)), \
                "Plaintext IMAP listener must have port = 0"
        # If no imap listener block at all, that's also acceptable (removed)

    def test_ssl_required(self):
        combined = _dovecot_conf_files()
        assert re.search(r"^\s*ssl\s*=\s*required\s*$", combined, re.MULTILINE), \
            "Dovecot ssl must be set to 'required'"
    def test_ssl_cert_exists(self):
        combined = _dovecot_conf_files()
        m = re.search(r"^\s*ssl_cert\s*=\s*<?\s*(\S+)", combined, re.MULTILINE)
        assert m, "ssl_cert not set in Dovecot config"
        cert_path = m.group(1).lstrip("<")
        assert os.path.isfile(cert_path), f"Dovecot ssl_cert file {cert_path} does not exist"

    def test_ssl_key_exists(self):
        combined = _dovecot_conf_files()
        m = re.search(r"^\s*ssl_key\s*=\s*<?\s*(\S+)", combined, re.MULTILINE)
        assert m, "ssl_key not set in Dovecot config"
        key_path = m.group(1).lstrip("<")
        assert os.path.isfile(key_path), f"Dovecot ssl_key file {key_path} does not exist"

    def test_ssl_min_protocol(self):
        combined = _dovecot_conf_files()
        m = re.search(r"^\s*ssl_min_protocol\s*=\s*(\S+)", combined, re.MULTILINE)
        assert m, "ssl_min_protocol not set in Dovecot config"
        assert "TLSv1.2" in m.group(1), "ssl_min_protocol must be TLSv1.2 or higher"

    def test_ssl_cipher_list_set(self):
        combined = _dovecot_conf_files()
        m = re.search(r"^\s*ssl_cipher_list\s*=\s*(.+)$", combined, re.MULTILINE)
        assert m, "ssl_cipher_list not set in Dovecot config"
        assert len(m.group(1).strip()) > 0, "ssl_cipher_list must be non-empty"

    def test_pam_auth_enabled(self):
        combined = _dovecot_conf_files()
        # Either include auth-system.conf.ext or passdb { driver = pam }
        has_system_ext = "auth-system.conf.ext" in combined
        has_pam_passdb = re.search(r"driver\s*=\s*pam", combined)
        assert has_system_ext or has_pam_passdb, \
            "PAM-based auth must be enabled (auth-system.conf.ext or driver=pam)"


# ---------------------------------------------------------------------------
# 4. TLS Certificates — cross-service consistency
# ---------------------------------------------------------------------------

class TestTLSCertificates:

    def test_postfix_cert_file_on_disk(self):
        content = postfix_main_cf()
        assert content is not None
        m = re.search(r"^\s*smtpd_tls_cert_file\s*=\s*(\S+)", content, re.MULTILINE)
        assert m, "smtpd_tls_cert_file not set"
        assert os.path.isfile(m.group(1)), f"Postfix cert {m.group(1)} missing"

    def test_postfix_key_file_on_disk(self):
        content = postfix_main_cf()
        assert content is not None
        m = re.search(r"^\s*smtpd_tls_key_file\s*=\s*(\S+)", content, re.MULTILINE)
        assert m, "smtpd_tls_key_file not set"
        assert os.path.isfile(m.group(1)), f"Postfix key {m.group(1)} missing"

    def test_dovecot_cert_file_on_disk(self):
        combined = _dovecot_conf_files()
        m = re.search(r"^\s*ssl_cert\s*=\s*<?\s*(\S+)", combined, re.MULTILINE)
        assert m, "Dovecot ssl_cert not set"
        cert_path = m.group(1).lstrip("<")
        assert os.path.isfile(cert_path), f"Dovecot cert {cert_path} missing"

    def test_dovecot_key_file_on_disk(self):
        combined = _dovecot_conf_files()
        m = re.search(r"^\s*ssl_key\s*=\s*<?\s*(\S+)", combined, re.MULTILINE)
        assert m, "Dovecot ssl_key not set"
        key_path = m.group(1).lstrip("<")
        assert os.path.isfile(key_path), f"Dovecot key {key_path} missing"


# ---------------------------------------------------------------------------
# 5. UFW Firewall
# ---------------------------------------------------------------------------

class TestUFW:

    def _ufw_status(self):
        out, _ = run_cmd("ufw status")
        return out

    def test_ufw_active(self):
        out = self._ufw_status()
        assert "active" in out.lower(), "UFW must be active"

    def test_port_25_allowed(self):
        out = self._ufw_status()
        assert re.search(r"25.*ALLOW.*192\.168\.0\.0/24", out), \
            "Port 25 must be allowed from 192.168.0.0/24"

    def test_port_465_allowed(self):
        out = self._ufw_status()
        assert re.search(r"465.*ALLOW.*192\.168\.0\.0/24", out), \
            "Port 465 must be allowed from 192.168.0.0/24"

    def test_port_587_allowed(self):
        out = self._ufw_status()
        assert re.search(r"587.*ALLOW.*192\.168\.0\.0/24", out), \
            "Port 587 must be allowed from 192.168.0.0/24"

    def test_port_993_allowed(self):
        out = self._ufw_status()
        assert re.search(r"993.*ALLOW.*192\.168\.0\.0/24", out), \
            "Port 993 must be allowed from 192.168.0.0/24"


# ---------------------------------------------------------------------------
# 6. Test User — mailtest
# ---------------------------------------------------------------------------

class TestMailtestUser:

    def test_user_exists_in_passwd(self):
        passwd = read_file("/etc/passwd")
        assert passwd is not None, "/etc/passwd not readable"
        assert re.search(r"^mailtest:", passwd, re.MULTILINE), \
            "User 'mailtest' must exist in /etc/passwd"

    def test_user_is_not_root(self):
        try:
            info = pwd.getpwnam("mailtest")
            assert info.pw_uid != 0, "mailtest must not be root (UID 0)"
        except KeyError:
            assert False, "User 'mailtest' does not exist"

    def test_user_has_valid_shell(self):
        try:
            info = pwd.getpwnam("mailtest")
            # Accept common shells or nologin
            valid = ["/bin/bash", "/bin/sh", "/usr/sbin/nologin",
                     "/sbin/nologin", "/bin/false", "/usr/bin/false"]
            assert info.pw_shell in valid, \
                f"mailtest shell '{info.pw_shell}' is not a recognized valid shell"
        except KeyError:
            assert False, "User 'mailtest' does not exist"


# ---------------------------------------------------------------------------
# 7. Cron Job — queue monitoring
# ---------------------------------------------------------------------------

class TestCronJob:

    def _get_crontab(self):
        """Get crontab content from multiple sources."""
        out, rc = run_cmd("crontab -l 2>/dev/null")
        # Also check system crontabs
        sys_cron = read_file("/etc/crontab") or ""
        cron_d = ""
        if os.path.isdir("/etc/cron.d"):
            for f in os.listdir("/etc/cron.d"):
                c = read_file(os.path.join("/etc/cron.d", f))
                if c:
                    cron_d += c + "\n"
        return out + sys_cron + cron_d

    def test_cron_job_exists_with_mailq(self):
        combined = self._get_crontab()
        assert "mailq" in combined, \
            "Cron job must invoke 'mailq'"

    def test_cron_job_writes_to_log(self):
        combined = self._get_crontab()
        assert "/var/log/postfix_queue.log" in combined, \
            "Cron job must write to /var/log/postfix_queue.log"

    def test_cron_job_is_hourly(self):
        combined = self._get_crontab()
        # Find lines containing both mailq and postfix_queue.log
        for line in combined.splitlines():
            line = line.strip()
            if "mailq" in line and "postfix_queue.log" in line and not line.startswith("#"):
                # Hourly: first field can be a number or *, second field must be *
                # Common patterns: "0 * * * *", "*/5 * * * *" (every 5 min is not hourly but close)
                # Standard hourly: minute_field * * * *
                fields = line.split()
                if len(fields) >= 5:
                    # Second field (hour) should be * for hourly
                    assert fields[1] == "*", \
                        f"Cron job hour field should be '*' for hourly, got '{fields[1]}'"
                    return
        assert False, "No hourly cron entry found with mailq and postfix_queue.log"


# ---------------------------------------------------------------------------
# 8. Documentation File — /app/mail_server_doc.txt
# ---------------------------------------------------------------------------

class TestDocumentationFile:

    def test_doc_file_exists(self):
        content = read_file("/app/mail_server_doc.txt")
        assert content is not None, "/app/mail_server_doc.txt does not exist"
        assert len(content.strip()) > 0, "/app/mail_server_doc.txt is empty"

    def test_mailtest_uid_present(self):
        content = read_file("/app/mail_server_doc.txt")
        assert content is not None
        m = re.search(r"^MAILTEST_UID=(\d+)\s*$", content, re.MULTILINE)
        assert m, "MAILTEST_UID=<uid> line not found in doc file"
        uid = int(m.group(1))
        assert uid > 0, "MAILTEST_UID must be a positive integer (non-root)"

    def test_mailtest_gid_present(self):
        content = read_file("/app/mail_server_doc.txt")
        assert content is not None
        m = re.search(r"^MAILTEST_GID=(\d+)\s*$", content, re.MULTILINE)
        assert m, "MAILTEST_GID=<gid> line not found in doc file"
        gid = int(m.group(1))
        assert gid > 0, "MAILTEST_GID must be a positive integer"

    def test_dovecot_cipher_list_present(self):
        content = read_file("/app/mail_server_doc.txt")
        assert content is not None
        m = re.search(r"^DOVECOT_CIPHER_LIST=(.+)$", content, re.MULTILINE)
        assert m, "DOVECOT_CIPHER_LIST=<cipher_string> line not found in doc file"
        cipher = m.group(1).strip()
        assert len(cipher) > 0, "DOVECOT_CIPHER_LIST must be non-empty"

    def test_uid_matches_system(self):
        """Cross-validate UID in doc file against actual system user."""
        content = read_file("/app/mail_server_doc.txt")
        assert content is not None
        m = re.search(r"^MAILTEST_UID=(\d+)\s*$", content, re.MULTILINE)
        assert m, "MAILTEST_UID not found"
        doc_uid = int(m.group(1))
        try:
            info = pwd.getpwnam("mailtest")
            assert info.pw_uid == doc_uid, \
                f"Doc UID {doc_uid} does not match system UID {info.pw_uid}"
        except KeyError:
            assert False, "User 'mailtest' does not exist for cross-validation"

    def test_gid_matches_system(self):
        """Cross-validate GID in doc file against actual system user."""
        content = read_file("/app/mail_server_doc.txt")
        assert content is not None
        m = re.search(r"^MAILTEST_GID=(\d+)\s*$", content, re.MULTILINE)
        assert m, "MAILTEST_GID not found"
        doc_gid = int(m.group(1))
        try:
            info = pwd.getpwnam("mailtest")
            assert info.pw_gid == doc_gid, \
                f"Doc GID {doc_gid} does not match system GID {info.pw_gid}"
        except KeyError:
            assert False, "User 'mailtest' does not exist for cross-validation"

    def test_cipher_matches_dovecot_config(self):
        """Cross-validate cipher list in doc file against Dovecot config."""
        content = read_file("/app/mail_server_doc.txt")
        assert content is not None
        m_doc = re.search(r"^DOVECOT_CIPHER_LIST=(.+)$", content, re.MULTILINE)
        assert m_doc, "DOVECOT_CIPHER_LIST not found in doc"
        doc_cipher = m_doc.group(1).strip()

        combined = _dovecot_conf_files()
        m_conf = re.search(r"^\s*ssl_cipher_list\s*=\s*(.+)$", combined, re.MULTILINE)
        assert m_conf, "ssl_cipher_list not found in Dovecot config"
        conf_cipher = m_conf.group(1).strip()

        assert doc_cipher == conf_cipher, \
            f"Doc cipher '{doc_cipher}' does not match Dovecot config cipher '{conf_cipher}'"


# ---------------------------------------------------------------------------
# 9. Services Running
# ---------------------------------------------------------------------------

class TestServicesRunning:

    def test_postfix_running(self):
        # Try systemctl first, fall back to process check
        out, rc = run_cmd("systemctl is-active postfix 2>/dev/null")
        if rc == 0 and "active" in out.strip():
            return
        # Fallback: check if master process is running (postfix main daemon)
        out2, rc2 = run_cmd("pgrep -x master")
        if rc2 == 0 and out2.strip():
            return
        # Another fallback: postfix status
        out3, rc3 = run_cmd("postfix status 2>&1")
        assert "is running" in out3.lower() or rc3 == 0, \
            "Postfix must be running"

    def test_dovecot_running(self):
        # Try systemctl first, fall back to process check
        out, rc = run_cmd("systemctl is-active dovecot 2>/dev/null")
        if rc == 0 and "active" in out.strip():
            return
        # Fallback: check if dovecot process is running
        out2, rc2 = run_cmd("pgrep -x dovecot")
        if rc2 == 0 and out2.strip():
            return
        # Another fallback
        out3, rc3 = run_cmd("pidof dovecot")
        assert rc3 == 0 and out3.strip(), \
            "Dovecot must be running"
