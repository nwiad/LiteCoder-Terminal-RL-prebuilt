"""
Tests for Nginx TLS Configuration Generator.
Validates the 5 output files produced by the solution script
against the primary input.json configuration.
"""

import json
import os
import re

# ---------------------------------------------------------------------------
# Paths – resolved relative to the project root (/app)
# ---------------------------------------------------------------------------
BASE_DIR = "/app"
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
INPUT_FILE = os.path.join(BASE_DIR, "input.json")

NGINX_CONF = os.path.join(OUTPUT_DIR, "nginx_https.conf")
SSL_PARAMS = os.path.join(OUTPUT_DIR, "ssl_params.conf")
CERTBOT_SH = os.path.join(OUTPUT_DIR, "certbot_command.sh")
RENEWAL_CRON = os.path.join(OUTPUT_DIR, "renewal_cron.txt")
SUMMARY_JSON = os.path.join(OUTPUT_DIR, "summary.json")

ALL_OUTPUT_FILES = [NGINX_CONF, SSL_PARAMS, CERTBOT_SH, RENEWAL_CRON, SUMMARY_JSON]


def _load_input():
    with open(INPUT_FILE, "r") as f:
        return json.load(f)


def _read(path):
    with open(path, "r") as f:
        return f.read()


# ===================================================================
# 0. File existence & non-emptiness
# ===================================================================

class TestFileExistence:
    def test_output_directory_exists(self):
        assert os.path.isdir(OUTPUT_DIR), "/app/output/ directory does not exist"

    def test_all_output_files_exist(self):
        for fpath in ALL_OUTPUT_FILES:
            assert os.path.isfile(fpath), f"Missing output file: {fpath}"

    def test_all_output_files_non_empty(self):
        for fpath in ALL_OUTPUT_FILES:
            size = os.path.getsize(fpath)
            assert size > 0, f"Output file is empty: {fpath}"


# ===================================================================
# 1. nginx_https.conf
# ===================================================================

class TestNginxHttpsConf:
    """Validate the main Nginx HTTPS configuration file."""

    def _conf(self):
        return _read(NGINX_CONF)

    def _input(self):
        return _load_input()

    # -- Structural checks --

    def test_balanced_braces(self):
        content = self._conf()
        assert content.count("{") == content.count("}"), \
            "Unbalanced braces in nginx_https.conf"

    def test_unix_line_endings(self):
        content = self._conf()
        assert "\r\n" not in content, "File contains Windows line endings"

    # -- HTTP redirect block --

    def test_listen_port_80(self):
        content = self._conf()
        assert re.search(r"listen\s+80\b", content), \
            "Missing listen 80 directive"
    def test_http_to_https_redirect_301(self):
        content = self._conf()
        assert re.search(r"return\s+301\s+https://", content), \
            "Missing 301 redirect from HTTP to HTTPS"

    def test_server_name_in_http_block(self):
        cfg = self._input()
        content = self._conf()
        domain = cfg["domain"]
        assert domain in content, \
            f"Primary domain '{domain}' not found in nginx config"

    def test_additional_domains_in_server_name(self):
        cfg = self._input()
        content = self._conf()
        for d in cfg.get("additional_domains", []):
            assert d in content, \
                f"Additional domain '{d}' not found in nginx config"

    # -- HTTPS / SSL block --

    def test_listen_port_443_ssl(self):
        content = self._conf()
        assert re.search(r"listen\s+443\s+ssl", content), \
            "Missing listen 443 ssl directive"

    def test_ssl_certificate_path(self):
        cfg = self._input()
        content = self._conf()
        expected = f"{cfg['cert_dir']}/fullchain.pem"
        assert expected in content, \
            f"ssl_certificate should point to {expected}"

    def test_ssl_certificate_key_path(self):
        cfg = self._input()
        content = self._conf()
        expected = f"{cfg['cert_dir']}/privkey.pem"
        assert expected in content, \
            f"ssl_certificate_key should point to {expected}"

    def test_tls_protocols_only_12_and_13(self):
        content = self._conf()
        m = re.search(r"ssl_protocols\s+([^;]+);", content)
        assert m, "Missing ssl_protocols directive"
        protocols = m.group(1).strip()
        assert "TLSv1.2" in protocols, "TLSv1.2 must be listed"
        assert "TLSv1.3" in protocols, "TLSv1.3 must be listed"
        # Must NOT contain older protocols
        assert "TLSv1.0" not in protocols and "SSLv" not in protocols, \
            "Older protocols (TLSv1.0, SSLv*) must not be present"
        # Should not have TLSv1.1 either
        assert "TLSv1.1" not in protocols, "TLSv1.1 must not be present"

    def test_no_weak_ciphers(self):
        content = self._conf()
        m = re.search(r"ssl_ciphers\s+([^;]+);", content)
        assert m, "Missing ssl_ciphers directive"
        ciphers_str = m.group(1).upper()
        for weak in ["NULL", "MD5", "RC4", "DES", "3DES"]:
            assert weak not in ciphers_str, \
                f"Weak cipher component '{weak}' found in ssl_ciphers"

    def test_prefer_server_ciphers(self):
        content = self._conf()
        assert re.search(r"ssl_prefer_server_ciphers\s+on\s*;", content), \
            "Missing ssl_prefer_server_ciphers on"

    def test_acme_challenge_location(self):
        content = self._conf()
        assert "/.well-known/acme-challenge/" in content, \
            "Missing ACME challenge location block"

    def test_webroot_directive(self):
        cfg = self._input()
        content = self._conf()
        assert cfg["webroot"] in content, \
            f"Webroot '{cfg['webroot']}' not found in nginx config"

    # -- Conditional: OCSP stapling --

    def test_ocsp_stapling_when_enabled(self):
        cfg = self._input()
        content = self._conf()
        if cfg.get("enable_ocsp_stapling", False):
            assert re.search(r"ssl_stapling\s+on\s*;", content), \
                "OCSP stapling is enabled but ssl_stapling on not found"
            assert re.search(r"ssl_stapling_verify\s+on\s*;", content), \
                "OCSP stapling is enabled but ssl_stapling_verify on not found"
            expected_chain = f"{cfg['cert_dir']}/chain.pem"
            assert expected_chain in content, \
                f"ssl_trusted_certificate should point to {expected_chain}"

    # -- Conditional: HSTS --

    def test_hsts_when_enabled(self):
        cfg = self._input()
        content = self._conf()
        hsts_max_age = cfg.get("hsts_max_age", 0)
        if hsts_max_age > 0:
            assert "Strict-Transport-Security" in content, \
                "HSTS header missing when hsts_max_age > 0"
            assert str(hsts_max_age) in content, \
                f"HSTS max-age value {hsts_max_age} not found in config"
            assert "includeSubDomains" in content, \
                "HSTS header missing includeSubDomains"

    def test_no_hsts_when_disabled(self):
        cfg = self._input()
        content = self._conf()
        hsts_max_age = cfg.get("hsts_max_age", 0)
        if hsts_max_age == 0:
            assert "Strict-Transport-Security" not in content, \
                "HSTS header should not be present when hsts_max_age is 0"


# ===================================================================
# 2. ssl_params.conf
# ===================================================================

class TestSslParamsConf:
    """Validate the SSL parameters snippet file."""

    def _conf(self):
        return _read(SSL_PARAMS)

    def test_session_timeout_valid_range(self):
        content = self._conf()
        m = re.search(r"ssl_session_timeout\s+(\d+)([hm])\s*;", content)
        assert m, "Missing ssl_session_timeout directive"
        val, unit = int(m.group(1)), m.group(2)
        if unit == "h":
            assert 1 <= val <= 24, "ssl_session_timeout must be 1h-24h"
        elif unit == "m":
            assert 60 <= val <= 1440, "ssl_session_timeout must be 60m-1440m"

    def test_session_cache_shared_ssl(self):
        content = self._conf()
        m = re.search(r"ssl_session_cache\s+shared:SSL:(\d+)([mk])\s*;", content, re.IGNORECASE)
        assert m, "Missing ssl_session_cache shared:SSL directive"
        val, unit = int(m.group(1)), m.group(2).lower()
        if unit == "m":
            assert val >= 10, "ssl_session_cache size must be at least 10m"

    def test_session_tickets_off(self):
        content = self._conf()
        assert re.search(r"ssl_session_tickets\s+off\s*;", content), \
            "Missing ssl_session_tickets off"

    def test_buffer_size_present(self):
        content = self._conf()
        assert re.search(r"ssl_buffer_size\s+\d+[kKmM]?\s*;", content), \
            "Missing ssl_buffer_size directive"


# ===================================================================
# 3. certbot_command.sh
# ===================================================================

class TestCertbotCommandSh:
    """Validate the certbot command shell script."""

    def _script(self):
        return _read(CERTBOT_SH)

    def _input(self):
        return _load_input()

    def test_shebang(self):
        content = self._script()
        assert content.strip().startswith("#!/bin/bash"), \
            "certbot_command.sh must start with #!/bin/bash shebang"

    def test_certbot_certonly(self):
        content = self._script()
        assert "certbot certonly" in content or "certbot  certonly" in content, \
            "Must use 'certbot certonly'"

    def test_webroot_mode(self):
        content = self._script()
        assert "--webroot" in content, "Must use --webroot mode"

    def test_webroot_path(self):
        cfg = self._input()
        content = self._script()
        assert cfg["webroot"] in content, \
            f"--webroot-path must reference {cfg['webroot']}"

    def test_domain_flags(self):
        cfg = self._input()
        content = self._script()
        all_domains = [cfg["domain"]] + cfg.get("additional_domains", [])
        for d in all_domains:
            assert re.search(rf"-d\s+{re.escape(d)}\b", content), \
                f"Missing -d flag for domain '{d}'"

    def test_email_flag(self):
        cfg = self._input()
        content = self._script()
        assert cfg["email"] in content, \
            f"Missing --email with value {cfg['email']}"

    def test_agree_tos(self):
        content = self._script()
        assert "--agree-tos" in content, "Missing --agree-tos flag"

    def test_non_interactive(self):
        content = self._script()
        assert "--non-interactive" in content, "Missing --non-interactive flag"


# ===================================================================
# 4. renewal_cron.txt
# ===================================================================

class TestRenewalCron:
    """Validate the cron entry for certificate renewal."""

    def _cron(self):
        return _read(RENEWAL_CRON).strip()

    def test_non_empty(self):
        content = self._cron()
        assert len(content) > 0, "renewal_cron.txt is empty"

    def test_contains_certbot_renew(self):
        content = self._cron()
        assert "certbot renew" in content or "certbot  renew" in content, \
            "Cron entry must contain 'certbot renew'"

    def test_contains_nginx_reload(self):
        content = self._cron()
        content_lower = content.lower()
        assert "nginx" in content_lower and "reload" in content_lower, \
            "Cron entry must contain nginx reload command"

    def test_runs_at_least_daily(self):
        """Verify the cron schedule runs at least once per day.
        A valid daily-or-more-frequent cron has 5 time fields before the command.
        The day-of-month (field 3) and month (field 4) should be '*' for daily.
        """
        content = self._cron()
        # Extract the first 5 whitespace-separated tokens (cron time fields)
        tokens = content.split()
        assert len(tokens) >= 6, \
            "Cron line must have at least 5 time fields + a command"
        # Fields: minute hour day-of-month month day-of-week
        day_of_month = tokens[2]
        month = tokens[3]
        assert day_of_month == "*", \
            f"Day-of-month field should be '*' for daily schedule, got '{day_of_month}'"
        assert month == "*", \
            f"Month field should be '*' for daily schedule, got '{month}'"


# ===================================================================
# 5. summary.json
# ===================================================================

class TestSummaryJson:
    """Validate the summary JSON output."""

    def _summary(self):
        content = _read(SUMMARY_JSON)
        return json.loads(content)

    def _input(self):
        return _load_input()

    def test_valid_json(self):
        """summary.json must be parseable."""
        content = _read(SUMMARY_JSON)
        data = json.loads(content)
        assert isinstance(data, dict), "summary.json root must be an object"

    def test_required_keys_present(self):
        summary = self._summary()
        required = [
            "domain", "all_domains", "https_port", "http_port",
            "http_redirect", "tls_protocols", "ocsp_stapling",
            "hsts_enabled", "hsts_max_age", "cert_path", "key_path",
            "renewal_method",
        ]
        for key in required:
            assert key in summary, f"Missing required key '{key}' in summary.json"

    def test_domain_matches_input(self):
        cfg = self._input()
        summary = self._summary()
        assert summary["domain"] == cfg["domain"], \
            f"domain mismatch: expected '{cfg['domain']}', got '{summary['domain']}'"

    def test_all_domains_order(self):
        cfg = self._input()
        summary = self._summary()
        expected = [cfg["domain"]] + cfg.get("additional_domains", [])
        assert summary["all_domains"] == expected, \
            f"all_domains mismatch: expected {expected}, got {summary['all_domains']}"

    def test_ports(self):
        summary = self._summary()
        assert summary["https_port"] == 443, "https_port must be 443"
        assert summary["http_port"] == 80, "http_port must be 80"

    def test_http_redirect_true(self):
        summary = self._summary()
        assert summary["http_redirect"] is True, "http_redirect must be true"

    def test_tls_protocols(self):
        summary = self._summary()
        protos = summary["tls_protocols"]
        assert isinstance(protos, list), "tls_protocols must be a list"
        assert "TLSv1.2" in protos, "TLSv1.2 must be in tls_protocols"
        assert "TLSv1.3" in protos, "TLSv1.3 must be in tls_protocols"
        assert len(protos) == 2, "tls_protocols should contain exactly 2 entries"

    def test_ocsp_stapling_matches_input(self):
        cfg = self._input()
        summary = self._summary()
        expected = cfg.get("enable_ocsp_stapling", False)
        assert summary["ocsp_stapling"] == expected, \
            f"ocsp_stapling mismatch: expected {expected}"

    def test_hsts_enabled_matches_input(self):
        cfg = self._input()
        summary = self._summary()
        expected = cfg.get("hsts_max_age", 0) > 0
        assert summary["hsts_enabled"] == expected, \
            f"hsts_enabled mismatch: expected {expected}"

    def test_hsts_max_age_matches_input(self):
        cfg = self._input()
        summary = self._summary()
        expected = cfg.get("hsts_max_age", 0)
        assert summary["hsts_max_age"] == expected, \
            f"hsts_max_age mismatch: expected {expected}, got {summary['hsts_max_age']}"

    def test_cert_path(self):
        cfg = self._input()
        summary = self._summary()
        expected = f"{cfg['cert_dir']}/fullchain.pem"
        assert summary["cert_path"] == expected, \
            f"cert_path mismatch: expected '{expected}'"

    def test_key_path(self):
        cfg = self._input()
        summary = self._summary()
        expected = f"{cfg['cert_dir']}/privkey.pem"
        assert summary["key_path"] == expected, \
            f"key_path mismatch: expected '{expected}'"

    def test_renewal_method(self):
        summary = self._summary()
        assert summary["renewal_method"] == "cron", \
            "renewal_method must be 'cron'"
