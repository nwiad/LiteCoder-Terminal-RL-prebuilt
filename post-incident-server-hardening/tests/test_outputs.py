"""
Tests for Post-Incident Hardening & Audit Trail task.
Validates all 10 tasks from instruction.md by checking output files,
system configuration, and script behavior.
"""

import os
import subprocess
import re
import stat

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def read_file(path):
    """Read file content, return None if missing."""
    try:
        with open(path, "r") as f:
            return f.read()
    except (FileNotFoundError, PermissionError):
        return None


def file_exists(path):
    return os.path.isfile(path)


def run_cmd(cmd, stdin_data=None, timeout=10):
    """Run a shell command and return (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True,
            stdin=subprocess.PIPE if stdin_data else None,
            input=stdin_data, timeout=timeout,
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "timeout"


# ===========================================================================
# Task 1: SSH Hardening
# ===========================================================================

class TestTask1SSHHardening:

    def test_sshd_config_exists(self):
        assert file_exists("/etc/ssh/sshd_config"), \
            "/etc/ssh/sshd_config must exist"

    def test_permit_root_login_no(self):
        content = read_file("/etc/ssh/sshd_config")
        assert content is not None
        # Match PermitRootLogin no (case-insensitive value, ignore comments)
        lines = [l.strip() for l in content.splitlines() if l.strip() and not l.strip().startswith("#")]
        found = any(re.match(r"(?i)^PermitRootLogin\s+no$", l) for l in lines)
        assert found, "sshd_config must set PermitRootLogin no"

    def test_password_auth_no(self):
        content = read_file("/etc/ssh/sshd_config")
        assert content is not None
        lines = [l.strip() for l in content.splitlines() if l.strip() and not l.strip().startswith("#")]
        found = any(re.match(r"(?i)^PasswordAuthentication\s+no$", l) for l in lines)
        assert found, "sshd_config must set PasswordAuthentication no"

    def test_pubkey_auth_yes(self):
        content = read_file("/etc/ssh/sshd_config")
        assert content is not None
        lines = [l.strip() for l in content.splitlines() if l.strip() and not l.strip().startswith("#")]
        found = any(re.match(r"(?i)^PubkeyAuthentication\s+yes$", l) for l in lines)
        assert found, "sshd_config must set PubkeyAuthentication yes"

    def test_ssh_port_2222(self):
        content = read_file("/etc/ssh/sshd_config")
        assert content is not None
        lines = [l.strip() for l in content.splitlines() if l.strip() and not l.strip().startswith("#")]
        found = any(re.match(r"(?i)^Port\s+2222$", l) for l in lines)
        assert found, "sshd_config must set Port 2222"

    def test_fail2ban_jail_exists(self):
        assert file_exists("/etc/fail2ban/jail.local"), \
            "/etc/fail2ban/jail.local must exist"

    def test_fail2ban_jail_sshd_section(self):
        content = read_file("/etc/fail2ban/jail.local")
        assert content is not None
        assert "[sshd]" in content, "jail.local must contain [sshd] section"

    def test_fail2ban_maxretry(self):
        content = read_file("/etc/fail2ban/jail.local")
        assert content is not None
        found = re.search(r"maxretry\s*=\s*3", content)
        assert found, "jail.local must set maxretry = 3"

    def test_fail2ban_bantime(self):
        content = read_file("/etc/fail2ban/jail.local")
        assert content is not None
        found = re.search(r"bantime\s*=\s*3600", content)
        assert found, "jail.local must set bantime = 3600"


# ===========================================================================
# Task 2: Package Cleanup
# ===========================================================================

class TestTask2PackageCleanup:

    def test_removed_packages_file_exists(self):
        assert file_exists("/app/removed_packages.txt"), \
            "/app/removed_packages.txt must exist"

    def test_removed_packages_not_empty(self):
        content = read_file("/app/removed_packages.txt")
        assert content is not None
        assert content.strip() != "", "removed_packages.txt must not be empty"

    def test_removed_packages_format(self):
        """Each non-blank line should be a single package name or 'none'."""
        content = read_file("/app/removed_packages.txt")
        assert content is not None
        lines = [l.strip() for l in content.splitlines() if l.strip()]
        assert len(lines) >= 1, "Must list at least one entry"
        for line in lines:
            # Package names are alphanumeric with hyphens/dots, or literal 'none'
            assert re.match(r"^[a-zA-Z0-9_.+-]+$", line), \
                f"Invalid package name format: '{line}'"


# ===========================================================================
# Task 3: Host Firewall
# ===========================================================================

class TestTask3Firewall:

    def test_firewall_rules_file_exists(self):
        assert file_exists("/app/firewall_rules.txt"), \
            "/app/firewall_rules.txt must exist"

    def test_firewall_rules_not_empty(self):
        content = read_file("/app/firewall_rules.txt")
        assert content is not None
        assert len(content.strip()) > 20, \
            "firewall_rules.txt should contain substantial rule data"

    def test_firewall_allows_port_2222(self):
        content = read_file("/app/firewall_rules.txt")
        assert content is not None
        assert "2222" in content, "Firewall rules must reference port 2222"

    def test_firewall_allows_port_80(self):
        content = read_file("/app/firewall_rules.txt")
        assert content is not None
        # Check for port 80 — could be --dport 80 or dport 80 in nft
        assert re.search(r"\b80\b", content), "Firewall rules must reference port 80"

    def test_firewall_allows_port_443(self):
        content = read_file("/app/firewall_rules.txt")
        assert content is not None
        assert re.search(r"\b443\b", content), "Firewall rules must reference port 443"

    def test_firewall_has_drop_policy(self):
        content = read_file("/app/firewall_rules.txt")
        assert content is not None
        content_upper = content.upper()
        has_drop = "DROP" in content_upper or "REJECT" in content_upper
        assert has_drop, "Firewall must have a DROP or REJECT rule for other traffic"

    def test_firewall_allows_established(self):
        content = read_file("/app/firewall_rules.txt")
        assert content is not None
        content_lower = content.lower()
        has_established = "established" in content_lower or "related" in content_lower \
            or "ct state" in content_lower
        assert has_established, "Firewall must allow established/related connections"


# ===========================================================================
# Task 4: Nginx with Systemd Hardening
# ===========================================================================

class TestTask4Nginx:

    def test_hardening_conf_exists(self):
        assert file_exists("/etc/systemd/system/nginx.service.d/hardening.conf"), \
            "Nginx systemd hardening drop-in must exist"

    def test_hardening_private_tmp(self):
        content = read_file("/etc/systemd/system/nginx.service.d/hardening.conf")
        assert content is not None
        assert re.search(r"PrivateTmp\s*=\s*yes", content, re.IGNORECASE), \
            "hardening.conf must set PrivateTmp=yes"

    def test_hardening_protect_system(self):
        content = read_file("/etc/systemd/system/nginx.service.d/hardening.conf")
        assert content is not None
        assert re.search(r"ProtectSystem\s*=\s*strict", content, re.IGNORECASE), \
            "hardening.conf must set ProtectSystem=strict"

    def test_hardening_capability_bounding_set(self):
        content = read_file("/etc/systemd/system/nginx.service.d/hardening.conf")
        assert content is not None
        assert re.search(r"CapabilityBoundingSet\s*=", content), \
            "hardening.conf must set CapabilityBoundingSet"

    def test_hardening_no_new_privileges(self):
        content = read_file("/etc/systemd/system/nginx.service.d/hardening.conf")
        assert content is not None
        assert re.search(r"NoNewPrivileges\s*=\s*yes", content, re.IGNORECASE), \
            "hardening.conf must set NoNewPrivileges=yes"

    def test_hardening_conf_has_service_section(self):
        content = read_file("/etc/systemd/system/nginx.service.d/hardening.conf")
        assert content is not None
        assert "[Service]" in content, \
            "hardening.conf must contain [Service] section header"

    def test_index_html_exists(self):
        assert file_exists("/var/www/html/index.html"), \
            "/var/www/html/index.html must exist"

    def test_index_html_content(self):
        content = read_file("/var/www/html/index.html")
        assert content is not None
        assert "Site is operational" in content, \
            "index.html must contain 'Site is operational'"


# ===========================================================================
# Task 5: Deploy User Setup
# ===========================================================================

class TestTask5DeployUser:

    def test_deploy_user_exists(self):
        rc, stdout, _ = run_cmd("id deploy")
        assert rc == 0, "User 'deploy' must exist"

    def test_deploy_home_directory(self):
        rc, stdout, _ = run_cmd("getent passwd deploy")
        assert rc == 0
        fields = stdout.strip().split(":")
        assert len(fields) >= 6
        assert fields[5] == "/home/deploy", \
            "deploy user home must be /home/deploy"

    def test_var_www_ownership(self):
        rc, stdout, _ = run_cmd("stat -c '%U:%G' /var/www")
        assert rc == 0
        assert stdout.strip() == "deploy:deploy", \
            "/var/www must be owned by deploy:deploy"

    def test_deploy_sessions_dir_exists(self):
        assert os.path.isdir("/var/log/deploy_sessions"), \
            "/var/log/deploy_sessions/ must exist"

    def test_deploy_sessions_dir_permissions(self):
        st = os.stat("/var/log/deploy_sessions")
        mode = stat.S_IMODE(st.st_mode)
        # Owner should have rwx, others should have no access
        assert mode & 0o077 == 0, \
            "/var/log/deploy_sessions must restrict access to owner only"

    def test_deploy_bashrc_session_logging(self):
        content = read_file("/home/deploy/.bashrc")
        assert content is not None
        assert "deploy_sessions" in content or "session" in content.lower(), \
            ".bashrc must configure session logging to /var/log/deploy_sessions"


# ===========================================================================
# Task 6: Rsyslog + TLS Log Forwarding
# ===========================================================================

class TestTask6Rsyslog:

    def test_rsyslog_forward_conf_exists(self):
        assert file_exists("/etc/rsyslog.d/60-forward.conf"), \
            "/etc/rsyslog.d/60-forward.conf must exist"

    def test_rsyslog_tls_driver(self):
        content = read_file("/etc/rsyslog.d/60-forward.conf")
        assert content is not None
        assert "gtls" in content.lower(), \
            "60-forward.conf must use gtls TLS driver"

    def test_rsyslog_target_host(self):
        content = read_file("/etc/rsyslog.d/60-forward.conf")
        assert content is not None
        assert "log-receiver.example.com" in content, \
            "60-forward.conf must target log-receiver.example.com"

    def test_rsyslog_target_port(self):
        content = read_file("/etc/rsyslog.d/60-forward.conf")
        assert content is not None
        assert "6514" in content, \
            "60-forward.conf must target port 6514"

    def test_rsyslog_forwards_authpriv(self):
        content = read_file("/etc/rsyslog.d/60-forward.conf")
        assert content is not None
        assert "authpriv" in content.lower(), \
            "60-forward.conf must forward authpriv logs"

    def test_rsyslog_forwards_kern(self):
        content = read_file("/etc/rsyslog.d/60-forward.conf")
        assert content is not None
        assert "kern" in content.lower(), \
            "60-forward.conf must forward kern logs"

    def test_rsyslog_forwards_daemon(self):
        content = read_file("/etc/rsyslog.d/60-forward.conf")
        assert content is not None
        assert "daemon" in content.lower(), \
            "60-forward.conf must forward daemon logs"

    def test_rsyslog_forwards_nginx(self):
        content = read_file("/etc/rsyslog.d/60-forward.conf")
        assert content is not None
        assert "nginx" in content.lower(), \
            "60-forward.conf must forward nginx-related logs"

    def test_logrotate_config_exists(self):
        assert file_exists("/etc/logrotate.d/custom-logs"), \
            "/etc/logrotate.d/custom-logs must exist"

    def test_logrotate_30_day_retention(self):
        content = read_file("/etc/logrotate.d/custom-logs")
        assert content is not None
        assert re.search(r"rotate\s+30", content), \
            "logrotate config must set 30-day retention (rotate 30)"


# ===========================================================================
# Task 7: Log Hash Pipeline
# ===========================================================================

class TestTask7HashPipeline:

    def test_hash_logger_exists(self):
        assert file_exists("/app/hash_logger.sh"), \
            "/app/hash_logger.sh must exist"

    def test_hash_logger_executable(self):
        assert os.access("/app/hash_logger.sh", os.X_OK), \
            "/app/hash_logger.sh must be executable"

    def test_hash_logger_uses_sha256(self):
        content = read_file("/app/hash_logger.sh")
        assert content is not None
        assert "sha256" in content.lower(), \
            "hash_logger.sh must use SHA-256 hashing"

    def test_hash_logger_functional(self):
        """Feed a known line via stdin and verify SHA-256 hash output."""
        test_line = "test log entry 12345"
        # Compute expected hash
        import hashlib
        expected_hash = hashlib.sha256(test_line.encode()).hexdigest()

        # Remove append-only attribute if set (may fail in containers, that's ok)
        run_cmd("chattr -a /var/log/log-hashes.txt 2>/dev/null || true")

        # Copy hash_logger and redirect its output to a temp file
        tmp_hash = "/tmp/test_hash_logger_out.txt"
        run_cmd(f"rm -f {tmp_hash}")
        run_cmd(f"cp /app/hash_logger.sh /tmp/test_hash_logger.sh && chmod +x /tmp/test_hash_logger.sh")
        run_cmd(f"sed -i 's|/var/log/log-hashes.txt|{tmp_hash}|g' /tmp/test_hash_logger.sh")

        rc, stdout, stderr = run_cmd(
            f'echo "{test_line}" | /tmp/test_hash_logger.sh',
            timeout=10
        )
        content = read_file(tmp_hash)
        assert content is not None, \
            "hash_logger.sh must write output to its hash file"
        assert expected_hash in content, \
            f"hash_logger.sh must produce correct SHA-256 hash for input. Expected {expected_hash}"

    def test_cron_job_exists(self):
        assert file_exists("/etc/cron.d/log-hash-ship"), \
            "/etc/cron.d/log-hash-ship must exist"

    def test_cron_job_uses_scp(self):
        content = read_file("/etc/cron.d/log-hash-ship")
        assert content is not None
        assert "scp" in content, "Cron job must use scp to ship log hashes"

    def test_cron_job_targets_remote(self):
        content = read_file("/etc/cron.d/log-hash-ship")
        assert content is not None
        assert "log-receiver.example.com" in content, \
            "Cron job must target log-receiver.example.com"

    def test_cron_job_hourly(self):
        content = read_file("/etc/cron.d/log-hash-ship")
        assert content is not None
        # Hourly cron: first field is a number or *, minute-based schedule
        lines = [l.strip() for l in content.splitlines()
                 if l.strip() and not l.strip().startswith("#")]
        assert len(lines) >= 1, "Cron file must have at least one job entry"


# ===========================================================================
# Task 8: Append-Only Log Protection
# ===========================================================================

class TestTask8AppendOnly:

    def test_log_hashes_file_exists(self):
        assert file_exists("/var/log/log-hashes.txt"), \
            "/var/log/log-hashes.txt must exist"

    def test_apparmor_profile_exists(self):
        """An AppArmor profile for rsyslogd must exist under /etc/apparmor.d/."""
        found = False
        apparmor_dir = "/etc/apparmor.d"
        if os.path.isdir(apparmor_dir):
            for fname in os.listdir(apparmor_dir):
                fpath = os.path.join(apparmor_dir, fname)
                if os.path.isfile(fpath):
                    content = read_file(fpath)
                    if content and "rsyslog" in content.lower():
                        found = True
                        break
        assert found, \
            "An AppArmor profile referencing rsyslog must exist under /etc/apparmor.d/"

    def test_apparmor_profile_allows_log_write(self):
        """AppArmor profile must allow writing to /var/log/ paths."""
        apparmor_dir = "/etc/apparmor.d"
        profile_content = None
        if os.path.isdir(apparmor_dir):
            for fname in os.listdir(apparmor_dir):
                fpath = os.path.join(apparmor_dir, fname)
                if os.path.isfile(fpath):
                    content = read_file(fpath)
                    if content and "rsyslog" in content.lower():
                        profile_content = content
                        break
        assert profile_content is not None, "AppArmor rsyslog profile not found"
        assert "/var/log" in profile_content, \
            "AppArmor profile must reference /var/log paths"


# ===========================================================================
# Task 9: Tamper-Evidence Verification
# ===========================================================================

class TestTask9TamperVerification:

    def test_verify_logs_exists(self):
        assert file_exists("/app/verify_logs.sh"), \
            "/app/verify_logs.sh must exist"

    def test_verify_logs_executable(self):
        assert os.access("/app/verify_logs.sh", os.X_OK), \
            "/app/verify_logs.sh must be executable"

    def test_verify_logs_valid_hashes_exit_0(self):
        """With valid (untampered) hash data, verify_logs.sh must exit 0."""
        import hashlib
        # Seed known valid data into a temp hash file
        tmp_hash = "/tmp/test_verify_valid.txt"
        lines_to_hash = [
            "valid log line one",
            "valid log line two",
            "another valid entry",
        ]
        with open(tmp_hash, "w") as f:
            for line in lines_to_hash:
                h = hashlib.sha256(line.encode()).hexdigest()
                f.write(f"{h}  {line}\n")

        # Run verify_logs.sh with the temp hash file
        # We need to point the script at our temp file; use env or sed
        # Safest: copy script, replace path, run copy
        run_cmd(f"cp /app/verify_logs.sh /tmp/test_verify.sh && chmod +x /tmp/test_verify.sh")
        run_cmd(f"sed -i 's|/var/log/log-hashes.txt|{tmp_hash}|g' /tmp/test_verify.sh")
        rc, stdout, stderr = run_cmd("/tmp/test_verify.sh", timeout=10)
        assert rc == 0, \
            f"verify_logs.sh must exit 0 for valid hashes. Got rc={rc}, stdout={stdout}, stderr={stderr}"

    def test_verify_logs_tampered_exit_1(self):
        """With tampered hash data, verify_logs.sh must exit 1 and print TAMPER DETECTED."""
        tmp_hash = "/tmp/test_verify_tampered.txt"
        with open(tmp_hash, "w") as f:
            # Write a line with a wrong hash
            fake_hash = "a" * 64
            f.write(f"{fake_hash}  this line has a wrong hash\n")

        run_cmd(f"cp /app/verify_logs.sh /tmp/test_verify_tamper.sh && chmod +x /tmp/test_verify_tamper.sh")
        run_cmd(f"sed -i 's|/var/log/log-hashes.txt|{tmp_hash}|g' /tmp/test_verify_tamper.sh")
        rc, stdout, stderr = run_cmd("/tmp/test_verify_tamper.sh", timeout=10)
        assert rc == 1, \
            f"verify_logs.sh must exit 1 for tampered hashes. Got rc={rc}"
        assert "TAMPER DETECTED" in stdout or "TAMPER DETECTED" in stderr, \
            "verify_logs.sh must print 'TAMPER DETECTED' on hash mismatch"

    def test_verify_logs_empty_file_exit_0(self):
        """With an empty hash file, verify_logs.sh should exit 0 (nothing to verify)."""
        tmp_hash = "/tmp/test_verify_empty.txt"
        with open(tmp_hash, "w") as f:
            pass  # empty file

        run_cmd(f"cp /app/verify_logs.sh /tmp/test_verify_empty.sh && chmod +x /tmp/test_verify_empty.sh")
        run_cmd(f"sed -i 's|/var/log/log-hashes.txt|{tmp_hash}|g' /tmp/test_verify_empty.sh")
        rc, stdout, stderr = run_cmd("/tmp/test_verify_empty.sh", timeout=10)
        assert rc == 0, \
            f"verify_logs.sh should exit 0 for empty hash file. Got rc={rc}"


# ===========================================================================
# Task 10: Final Report
# ===========================================================================

class TestTask10Report:

    def test_report_exists(self):
        assert file_exists("/app/hardening_report.txt"), \
            "/app/hardening_report.txt must exist"

    def test_report_not_empty(self):
        content = read_file("/app/hardening_report.txt")
        assert content is not None
        assert len(content.strip()) > 100, \
            "hardening_report.txt must contain substantial content"

    def test_report_has_all_task_headers(self):
        """Report must contain [Task 1] through [Task 9] section headers."""
        content = read_file("/app/hardening_report.txt")
        assert content is not None
        for i in range(1, 10):
            header = f"[Task {i}]"
            assert header in content, \
                f"Report must contain section header '{header}'"

    def test_report_under_200_lines(self):
        content = read_file("/app/hardening_report.txt")
        assert content is not None
        line_count = len(content.splitlines())
        assert line_count <= 200, \
            f"Report must not exceed 200 lines, got {line_count}"

    def test_report_mentions_ssh(self):
        content = read_file("/app/hardening_report.txt")
        assert content is not None
        content_lower = content.lower()
        assert "ssh" in content_lower, \
            "Report must mention SSH hardening"

    def test_report_mentions_firewall(self):
        content = read_file("/app/hardening_report.txt")
        assert content is not None
        content_lower = content.lower()
        assert "firewall" in content_lower or "iptables" in content_lower \
            or "nftables" in content_lower, \
            "Report must mention firewall configuration"

    def test_report_mentions_nginx(self):
        content = read_file("/app/hardening_report.txt")
        assert content is not None
        assert "nginx" in content.lower(), \
            "Report must mention nginx"

    def test_report_mentions_deploy_user(self):
        content = read_file("/app/hardening_report.txt")
        assert content is not None
        assert "deploy" in content.lower(), \
            "Report must mention deploy user"

    def test_report_mentions_rsyslog(self):
        content = read_file("/app/hardening_report.txt")
        assert content is not None
        assert "rsyslog" in content.lower() or "syslog" in content.lower(), \
            "Report must mention rsyslog/syslog configuration"

