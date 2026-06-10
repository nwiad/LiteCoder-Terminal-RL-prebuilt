"""
Tests for Nginx SSL Load Balancer task.
Validates all 5 output files: SSL cert, SSL key, Nginx config,
validation result, and config summary JSON.
"""

import os
import json
import re
import subprocess

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SSL_CERT = "/app/ssl/server.crt"
SSL_KEY = "/app/ssl/server.key"
NGINX_CONF = "/app/nginx/load_balancer.conf"
VALIDATION_RESULT = "/app/nginx/validation_result.txt"
CONFIG_SUMMARY = "/app/nginx/config_summary.json"


# ===========================================================================
# Helper utilities
# ===========================================================================

def _read_file(path):
    """Read file content, return empty string if missing."""
    if not os.path.isfile(path):
        return ""
    with open(path, "r", errors="replace") as f:
        return f.read()


def _nginx_conf_content():
    return _read_file(NGINX_CONF)


# ===========================================================================
# 1. SSL Certificate tests
# ===========================================================================

class TestSSLCertificate:

    def test_cert_file_exists(self):
        assert os.path.isfile(SSL_CERT), f"SSL certificate not found at {SSL_CERT}"

    def test_cert_file_not_empty(self):
        assert os.path.getsize(SSL_CERT) > 0, "SSL certificate file is empty"

    def test_cert_is_pem_format(self):
        content = _read_file(SSL_CERT)
        assert "BEGIN CERTIFICATE" in content, "Certificate is not in PEM format"
        assert "END CERTIFICATE" in content, "Certificate PEM block not properly closed"

    def test_cert_cn_matches_domain(self):
        """Verify the certificate CN contains ecommerce.example.com."""
        try:
            from cryptography import x509
            from cryptography.x509.oid import NameOID
            with open(SSL_CERT, "rb") as f:
                cert = x509.load_pem_x509_certificate(f.read())
            cn_attrs = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
            assert len(cn_attrs) > 0, "Certificate has no CN attribute"
            cn_value = cn_attrs[0].value
            assert cn_value == "ecommerce.example.com", (
                f"Certificate CN is '{cn_value}', expected 'ecommerce.example.com'"
            )
        except ImportError:
            # Fallback: use openssl CLI
            result = subprocess.run(
                ["openssl", "x509", "-in", SSL_CERT, "-noout", "-subject"],
                capture_output=True, text=True
            )
            assert "ecommerce.example.com" in result.stdout, (
                f"CN not found in certificate subject: {result.stdout}"
            )

    def test_cert_is_rsa_2048(self):
        """Verify the certificate uses an RSA 2048-bit key."""
        try:
            from cryptography import x509
            from cryptography.hazmat.primitives.asymmetric import rsa as rsa_mod
            with open(SSL_CERT, "rb") as f:
                cert = x509.load_pem_x509_certificate(f.read())
            pub_key = cert.public_key()
            assert isinstance(pub_key, rsa_mod.RSAPublicKey), "Certificate key is not RSA"
            assert pub_key.key_size == 2048, (
                f"Key size is {pub_key.key_size}, expected 2048"
            )
        except ImportError:
            result = subprocess.run(
                ["openssl", "x509", "-in", SSL_CERT, "-noout", "-text"],
                capture_output=True, text=True
            )
            assert "RSA" in result.stdout, "Certificate does not use RSA key"
            assert "2048" in result.stdout, "Certificate key size is not 2048-bit"


# ===========================================================================
# 2. SSL Key tests
# ===========================================================================

class TestSSLKey:

    def test_key_file_exists(self):
        assert os.path.isfile(SSL_KEY), f"SSL key not found at {SSL_KEY}"

    def test_key_file_not_empty(self):
        assert os.path.getsize(SSL_KEY) > 0, "SSL key file is empty"

    def test_key_is_pem_format(self):
        content = _read_file(SSL_KEY)
        # Accept both "RSA PRIVATE KEY" and "PRIVATE KEY" (PKCS#8)
        assert "PRIVATE KEY" in content, "Key file is not in PEM format"

    def test_key_is_rsa_2048(self):
        """Verify the private key is RSA 2048-bit."""
        try:
            from cryptography.hazmat.primitives.serialization import load_pem_private_key
            from cryptography.hazmat.primitives.asymmetric import rsa as rsa_mod
            with open(SSL_KEY, "rb") as f:
                key = load_pem_private_key(f.read(), password=None)
            assert isinstance(key, rsa_mod.RSAPrivateKey), "Key is not RSA"
            assert key.key_size == 2048, f"Key size is {key.key_size}, expected 2048"
        except ImportError:
            result = subprocess.run(
                ["openssl", "rsa", "-in", SSL_KEY, "-text", "-noout"],
                capture_output=True, text=True
            )
            combined = result.stdout + result.stderr
            assert "2048" in combined or "RSA" in combined, "Key does not appear to be RSA 2048"


# ===========================================================================
# 3. Nginx Configuration tests
# ===========================================================================

class TestNginxConfig:

    def test_config_file_exists(self):
        assert os.path.isfile(NGINX_CONF), f"Nginx config not found at {NGINX_CONF}"

    def test_config_file_not_empty(self):
        assert os.path.getsize(NGINX_CONF) > 100, "Nginx config file is suspiciously small"

    # --- Upstream block ---

    def test_upstream_block_exists(self):
        conf = _nginx_conf_content()
        assert re.search(r"upstream\s+backend_servers\s*\{", conf), (
            "Missing 'upstream backend_servers' block"
        )

    def test_least_conn_algorithm(self):
        conf = _nginx_conf_content()
        assert re.search(r"least_conn\s*;", conf), (
            "Missing 'least_conn' load balancing algorithm in config"
        )

    def test_backend_server1(self):
        conf = _nginx_conf_content()
        assert re.search(r"server\s+server1\.backend\.local:8080", conf), (
            "Missing server1.backend.local:8080 in upstream"
        )

    def test_backend_server2(self):
        conf = _nginx_conf_content()
        assert re.search(r"server\s+server2\.backend\.local:8080", conf), (
            "Missing server2.backend.local:8080 in upstream"
        )

    def test_backend_server3(self):
        conf = _nginx_conf_content()
        assert re.search(r"server\s+server3\.backend\.local:8080", conf), (
            "Missing server3.backend.local:8080 in upstream"
        )

    # --- Health checks ---

    def test_max_fails_configured(self):
        conf = _nginx_conf_content()
        matches = re.findall(r"max_fails\s*=\s*3", conf)
        assert len(matches) >= 3, (
            f"Expected max_fails=3 on all 3 backend servers, found {len(matches)} occurrences"
        )

    def test_fail_timeout_configured(self):
        conf = _nginx_conf_content()
        matches = re.findall(r"fail_timeout\s*=\s*30s", conf)
        assert len(matches) >= 3, (
            f"Expected fail_timeout=30s on all 3 backend servers, found {len(matches)} occurrences"
        )

    # --- HTTPS server block ---

    def test_listen_443_ssl(self):
        conf = _nginx_conf_content()
        assert re.search(r"listen\s+443\s+ssl", conf), (
            "Missing 'listen 443 ssl' directive"
        )

    def test_server_name(self):
        conf = _nginx_conf_content()
        assert re.search(r"server_name\s+ecommerce\.example\.com", conf), (
            "Missing 'server_name ecommerce.example.com'"
        )

    def test_ssl_certificate_path(self):
        conf = _nginx_conf_content()
        assert re.search(r"ssl_certificate\s+/app/ssl/server\.crt\s*;", conf), (
            "Missing or incorrect ssl_certificate path"
        )

    def test_ssl_certificate_key_path(self):
        conf = _nginx_conf_content()
        assert re.search(r"ssl_certificate_key\s+/app/ssl/server\.key\s*;", conf), (
            "Missing or incorrect ssl_certificate_key path"
        )

    def test_ssl_protocols(self):
        conf = _nginx_conf_content()
        assert re.search(r"ssl_protocols\s+.*TLSv1\.2", conf), "Missing TLSv1.2 in ssl_protocols"
        assert re.search(r"ssl_protocols\s+.*TLSv1\.3", conf), "Missing TLSv1.3 in ssl_protocols"

    def test_proxy_pass_to_upstream(self):
        conf = _nginx_conf_content()
        assert re.search(r"proxy_pass\s+https?://backend_servers", conf), (
            "Missing proxy_pass to backend_servers upstream"
        )

    # --- Security headers ---

    def test_hsts_header(self):
        conf = _nginx_conf_content()
        assert re.search(
            r"add_header\s+Strict-Transport-Security\s+.*max-age=31536000.*includeSubDomains",
            conf
        ), "Missing or incorrect Strict-Transport-Security header"

    def test_x_frame_options_header(self):
        conf = _nginx_conf_content()
        assert re.search(r"add_header\s+X-Frame-Options\s+DENY", conf), (
            "Missing 'add_header X-Frame-Options DENY'"
        )

    def test_x_content_type_options_header(self):
        conf = _nginx_conf_content()
        assert re.search(r"add_header\s+X-Content-Type-Options\s+nosniff", conf), (
            "Missing 'add_header X-Content-Type-Options nosniff'"
        )

    # --- Proxy headers ---

    def test_proxy_header_host(self):
        conf = _nginx_conf_content()
        assert re.search(r"proxy_set_header\s+Host\s+\$host", conf), (
            "Missing 'proxy_set_header Host $host'"
        )

    def test_proxy_header_x_real_ip(self):
        conf = _nginx_conf_content()
        assert re.search(r"proxy_set_header\s+X-Real-IP\s+\$remote_addr", conf), (
            "Missing 'proxy_set_header X-Real-IP $remote_addr'"
        )

    def test_proxy_header_x_forwarded_for(self):
        conf = _nginx_conf_content()
        assert re.search(
            r"proxy_set_header\s+X-Forwarded-For\s+\$proxy_add_x_forwarded_for",
            conf
        ), "Missing 'proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for'"

    def test_proxy_header_x_forwarded_proto(self):
        conf = _nginx_conf_content()
        assert re.search(r"proxy_set_header\s+X-Forwarded-Proto\s+\$scheme", conf), (
            "Missing 'proxy_set_header X-Forwarded-Proto $scheme'"
        )

    # --- HTTP redirect block ---

    def test_listen_80(self):
        conf = _nginx_conf_content()
        assert re.search(r"listen\s+80\s*;", conf), "Missing 'listen 80' directive"

    def test_http_to_https_redirect(self):
        conf = _nginx_conf_content()
        assert re.search(r"return\s+301\s+https://", conf), (
            "Missing HTTP-to-HTTPS 301 redirect"
        )


# ===========================================================================
# 4. Validation Result tests
# ===========================================================================

class TestValidationResult:

    def test_validation_file_exists(self):
        assert os.path.isfile(VALIDATION_RESULT), (
            f"Validation result not found at {VALIDATION_RESULT}"
        )

    def test_validation_file_not_empty(self):
        assert os.path.getsize(VALIDATION_RESULT) > 0, "Validation result file is empty"

    def test_syntax_is_ok(self):
        content = _read_file(VALIDATION_RESULT)
        assert "syntax is ok" in content, (
            f"Validation result does not contain 'syntax is ok'. Content: {content[:500]}"
        )

    def test_validation_references_config_file(self):
        """The nginx -t output typically mentions the config file path."""
        content = _read_file(VALIDATION_RESULT)
        # nginx -t output usually says "nginx: the configuration file /path/to/file syntax is ok"
        assert "load_balancer.conf" in content or "syntax is ok" in content, (
            "Validation output doesn't reference the config file"
        )


# ===========================================================================
# 5. Config Summary JSON tests
# ===========================================================================

class TestConfigSummaryJSON:

    def test_json_file_exists(self):
        assert os.path.isfile(CONFIG_SUMMARY), (
            f"Config summary not found at {CONFIG_SUMMARY}"
        )

    def test_json_file_not_empty(self):
        assert os.path.getsize(CONFIG_SUMMARY) > 0, "Config summary file is empty"

    def test_valid_json(self):
        content = _read_file(CONFIG_SUMMARY)
        try:
            json.loads(content)
        except json.JSONDecodeError as e:
            assert False, f"Config summary is not valid JSON: {e}"

    def _load_json(self):
        with open(CONFIG_SUMMARY, "r") as f:
            return json.load(f)

    def test_domain_field(self):
        data = self._load_json()
        assert data.get("domain") == "ecommerce.example.com", (
            f"domain is '{data.get('domain')}', expected 'ecommerce.example.com'"
        )

    def test_ssl_certificate_field(self):
        data = self._load_json()
        assert data.get("ssl_certificate") == "/app/ssl/server.crt", (
            f"ssl_certificate is '{data.get('ssl_certificate')}'"
        )

    def test_ssl_key_field(self):
        data = self._load_json()
        assert data.get("ssl_key") == "/app/ssl/server.key", (
            f"ssl_key is '{data.get('ssl_key')}'"
        )

    def test_ssl_protocols_field(self):
        data = self._load_json()
        protocols = data.get("ssl_protocols", [])
        assert isinstance(protocols, list), "ssl_protocols should be a list"
        assert "TLSv1.2" in protocols, "TLSv1.2 missing from ssl_protocols"
        assert "TLSv1.3" in protocols, "TLSv1.3 missing from ssl_protocols"

    def test_load_balancing_algorithm_field(self):
        data = self._load_json()
        assert data.get("load_balancing_algorithm") == "least_conn", (
            f"load_balancing_algorithm is '{data.get('load_balancing_algorithm')}'"
        )

    def test_backend_servers_field(self):
        data = self._load_json()
        servers = data.get("backend_servers", [])
        assert isinstance(servers, list), "backend_servers should be a list"
        assert len(servers) == 3, f"Expected 3 backend servers, got {len(servers)}"
        expected = {
            "server1.backend.local:8080",
            "server2.backend.local:8080",
            "server3.backend.local:8080",
        }
        actual = set(servers)
        assert actual == expected, (
            f"Backend servers mismatch. Expected {expected}, got {actual}"
        )

    def test_health_check_field(self):
        data = self._load_json()
        hc = data.get("health_check", {})
        assert isinstance(hc, dict), "health_check should be a dict"
        assert hc.get("max_fails") == 3, (
            f"health_check.max_fails is {hc.get('max_fails')}, expected 3"
        )
        ft = hc.get("fail_timeout", "")
        assert ft == "30s", (
            f"health_check.fail_timeout is '{ft}', expected '30s'"
        )

    def test_security_headers_field(self):
        data = self._load_json()
        headers = data.get("security_headers", [])
        assert isinstance(headers, list), "security_headers should be a list"
        required = {
            "Strict-Transport-Security",
            "X-Frame-Options",
            "X-Content-Type-Options",
        }
        actual = set(headers)
        assert required.issubset(actual), (
            f"Missing security headers. Required: {required}, got: {actual}"
        )

    def test_http_redirect_field(self):
        data = self._load_json()
        assert data.get("http_redirect_to_https") is True, (
            f"http_redirect_to_https is {data.get('http_redirect_to_https')}, expected true"
        )


# ===========================================================================
# 6. Cross-validation: cert + key match each other
# ===========================================================================

class TestCertKeyConsistency:

    def test_cert_and_key_match(self):
        """Verify the certificate's public key matches the private key."""
        if not (os.path.isfile(SSL_CERT) and os.path.isfile(SSL_KEY)):
            assert False, "Cannot verify cert/key match: files missing"
        # Use openssl to extract modulus from both and compare
        cert_mod = subprocess.run(
            ["openssl", "x509", "-noout", "-modulus", "-in", SSL_CERT],
            capture_output=True, text=True
        )
        key_mod = subprocess.run(
            ["openssl", "rsa", "-noout", "-modulus", "-in", SSL_KEY],
            capture_output=True, text=True
        )
        assert cert_mod.stdout.strip() != "", "Could not extract modulus from certificate"
        assert key_mod.stdout.strip() != "", "Could not extract modulus from key"
        assert cert_mod.stdout.strip() == key_mod.stdout.strip(), (
            "Certificate and private key do not match (modulus mismatch)"
        )
