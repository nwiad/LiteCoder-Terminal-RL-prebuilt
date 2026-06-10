"""
Tests for Nginx SSL Load Balancer Setup task.

Validates:
1. File structure under /app/
2. SSL certificate properties (RSA 2048+, CN=localhost, validity)
3. Nginx configuration directives (upstream, SSL, redirect, proxy headers, logging)
4. Docker Compose structure (services, ports, volumes, network)
5. Backend Dockerfile existence and structure
6. Documentation content (service table, algorithm, SSL, health checks)
"""

import os
import re
import subprocess
import yaml

APP_DIR = "/app"


# ============================================================================
# Helper functions
# ============================================================================

def read_file(path):
    """Read file content, return empty string if missing."""
    try:
        with open(path, "r") as f:
            return f.read()
    except (FileNotFoundError, IsADirectoryError, PermissionError):
        return ""


def run_cmd(cmd):
    """Run a shell command and return stdout."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=15
        )
        return result.stdout + result.stderr
    except Exception:
        return ""


# ============================================================================
# 1. File existence tests
# ============================================================================

class TestFileStructure:
    """Verify all required files exist under /app/."""

    def test_docker_compose_exists(self):
        assert os.path.isfile(os.path.join(APP_DIR, "docker-compose.yml")), \
            "docker-compose.yml must exist at /app/docker-compose.yml"

    def test_nginx_conf_exists(self):
        assert os.path.isfile(os.path.join(APP_DIR, "nginx", "nginx.conf")), \
            "nginx.conf must exist at /app/nginx/nginx.conf"

    def test_ssl_cert_exists(self):
        assert os.path.isfile(os.path.join(APP_DIR, "nginx", "ssl", "server.crt")), \
            "SSL certificate must exist at /app/nginx/ssl/server.crt"

    def test_ssl_key_exists(self):
        assert os.path.isfile(os.path.join(APP_DIR, "nginx", "ssl", "server.key")), \
            "SSL key must exist at /app/nginx/ssl/server.key"

    def test_backend_dockerfile_exists(self):
        assert os.path.isfile(os.path.join(APP_DIR, "backend", "Dockerfile")), \
            "Backend Dockerfile must exist at /app/backend/Dockerfile"

    def test_docs_configuration_exists(self):
        assert os.path.isfile(os.path.join(APP_DIR, "docs", "configuration.md")), \
            "Documentation must exist at /app/docs/configuration.md"


# ============================================================================
# 2. SSL certificate tests
# ============================================================================

class TestSSLCertificate:
    """Validate SSL certificate properties using openssl."""

    CERT_PATH = os.path.join(APP_DIR, "nginx", "ssl", "server.crt")
    KEY_PATH = os.path.join(APP_DIR, "nginx", "ssl", "server.key")

    def test_cert_is_valid_x509(self):
        output = run_cmd(f"openssl x509 -in {self.CERT_PATH} -noout -text")
        assert "Certificate:" in output or "Issuer:" in output, \
            "server.crt must be a valid X.509 certificate"

    def test_cert_cn_is_localhost(self):
        output = run_cmd(f"openssl x509 -in {self.CERT_PATH} -noout -subject")
        assert "localhost" in output, \
            "Certificate CN must be set to localhost"

    def test_cert_rsa_key_at_least_2048(self):
        output = run_cmd(f"openssl x509 -in {self.CERT_PATH} -noout -text")
        # Look for RSA key size: "Public-Key: (2048 bit)" or similar
        match = re.search(r"Public-Key:\s*\((\d+)\s*bit\)", output)
        assert match is not None, "Certificate must use RSA public key"
        key_bits = int(match.group(1))
        assert key_bits >= 2048, \
            f"RSA key must be at least 2048 bits, got {key_bits}"

    def test_cert_validity_at_least_365_days(self):
        output = run_cmd(
            f"openssl x509 -in {self.CERT_PATH} -noout -enddate -startdate"
        )
        # Parse dates using openssl's output
        from datetime import datetime
        start_match = re.search(r"notBefore=(.+)", output)
        end_match = re.search(r"notAfter=(.+)", output)
        assert start_match and end_match, \
            "Could not parse certificate validity dates"
        fmt = "%b %d %H:%M:%S %Y %Z"
        # Try alternate format without leading zero
        start_str = start_match.group(1).strip()
        end_str = end_match.group(1).strip()
        try:
            start = datetime.strptime(start_str, fmt)
            end = datetime.strptime(end_str, fmt)
        except ValueError:
            # Some openssl versions use different format
            fmt2 = "%b  %d %H:%M:%S %Y %Z"
            start = datetime.strptime(start_str, fmt2)
            end = datetime.strptime(end_str, fmt2)
        diff_days = (end - start).days
        assert diff_days >= 365, \
            f"Certificate must be valid for at least 365 days, got {diff_days}"

    def test_key_matches_cert(self):
        cert_mod = run_cmd(
            f"openssl x509 -in {self.CERT_PATH} -noout -modulus"
        ).strip()
        key_mod = run_cmd(
            f"openssl rsa -in {self.KEY_PATH} -noout -modulus"
        ).strip()
        assert cert_mod and key_mod, "Could not read certificate/key modulus"
        assert cert_mod == key_mod, \
            "SSL certificate and key must match (modulus mismatch)"


# ============================================================================
# 3. Nginx configuration tests
# ============================================================================

class TestNginxConfig:
    """Validate nginx.conf content for required directives."""

    @staticmethod
    def _conf():
        return read_file(os.path.join(APP_DIR, "nginx", "nginx.conf"))

    def test_conf_not_empty(self):
        conf = self._conf()
        assert len(conf.strip()) > 50, "nginx.conf must not be empty"

    # --- Upstream block ---
    def test_upstream_named_backend_servers(self):
        conf = self._conf()
        assert re.search(r"upstream\s+backend_servers\s*\{", conf), \
            "Must define upstream block named 'backend_servers'"

    def test_upstream_least_conn(self):
        conf = self._conf()
        # least_conn must appear inside the upstream block
        upstream_match = re.search(
            r"upstream\s+backend_servers\s*\{([^}]+)\}", conf, re.DOTALL
        )
        assert upstream_match, "upstream backend_servers block not found"
        upstream_body = upstream_match.group(1)
        assert "least_conn" in upstream_body, \
            "upstream must use least_conn algorithm"

    def test_upstream_has_three_backends(self):
        conf = self._conf()
        upstream_match = re.search(
            r"upstream\s+backend_servers\s*\{([^}]+)\}", conf, re.DOTALL
        )
        assert upstream_match, "upstream backend_servers block not found"
        body = upstream_match.group(1)
        assert re.search(r"server\s+backend1:8080", body), \
            "upstream must include backend1:8080"
        assert re.search(r"server\s+backend2:8081", body), \
            "upstream must include backend2:8081"
        assert re.search(r"server\s+backend3:8082", body), \
            "upstream must include backend3:8082"

    def test_upstream_max_fails_and_fail_timeout(self):
        conf = self._conf()
        upstream_match = re.search(
            r"upstream\s+backend_servers\s*\{([^}]+)\}", conf, re.DOTALL
        )
        assert upstream_match, "upstream backend_servers block not found"
        body = upstream_match.group(1)
        # Each server line should have max_fails=3 and fail_timeout=30s
        server_lines = re.findall(r"server\s+backend\d+:\d+[^;]*;", body)
        assert len(server_lines) >= 3, \
            "upstream must have at least 3 server entries"
        for line in server_lines:
            assert "max_fails=3" in line, \
                f"Server line missing max_fails=3: {line}"
            assert "fail_timeout=30s" in line, \
                f"Server line missing fail_timeout=30s: {line}"

    # --- HTTPS server block (port 443) ---
    def test_listen_443_ssl(self):
        conf = self._conf()
        assert re.search(r"listen\s+443\s+ssl", conf), \
            "Must have a server block listening on 443 with SSL"

    def test_server_name_localhost(self):
        conf = self._conf()
        assert re.search(r"server_name\s+localhost\s*;", conf), \
            "server_name must be set to localhost"

    def test_ssl_certificate_path(self):
        conf = self._conf()
        assert re.search(r"ssl_certificate\s+/etc/nginx/ssl/server\.crt\s*;", conf), \
            "ssl_certificate must point to /etc/nginx/ssl/server.crt"

    def test_ssl_certificate_key_path(self):
        conf = self._conf()
        assert re.search(r"ssl_certificate_key\s+/etc/nginx/ssl/server\.key\s*;", conf), \
            "ssl_certificate_key must point to /etc/nginx/ssl/server.key"

    def test_ssl_protocols_tls12_tls13(self):
        conf = self._conf()
        proto_match = re.search(r"ssl_protocols\s+([^;]+);", conf)
        assert proto_match, "ssl_protocols directive must be present"
        protocols = proto_match.group(1)
        assert "TLSv1.2" in protocols, "Must enable TLSv1.2"
        assert "TLSv1.3" in protocols, "Must enable TLSv1.3"
        # Must NOT include older insecure protocols
        assert "TLSv1.0" not in protocols, "Must not enable TLSv1.0"
        assert "TLSv1.1" not in protocols, "Must not enable TLSv1.1"
        assert "SSLv3" not in protocols, "Must not enable SSLv3"

    def test_proxy_pass_to_upstream(self):
        conf = self._conf()
        assert re.search(r"proxy_pass\s+https?://backend_servers", conf), \
            "proxy_pass must route to backend_servers upstream"

    def test_proxy_headers(self):
        conf = self._conf()
        required_headers = [
            (r"proxy_set_header\s+Host\s+", "Host"),
            (r"proxy_set_header\s+X-Real-IP\s+", "X-Real-IP"),
            (r"proxy_set_header\s+X-Forwarded-For\s+", "X-Forwarded-For"),
            (r"proxy_set_header\s+X-Forwarded-Proto\s+", "X-Forwarded-Proto"),
        ]
        for pattern, name in required_headers:
            assert re.search(pattern, conf), \
                f"proxy_set_header {name} must be configured"

    # --- HTTP server block (port 80) ---
    def test_listen_80(self):
        conf = self._conf()
        assert re.search(r"listen\s+80\s*;", conf), \
            "Must have a server block listening on port 80"

    def test_http_to_https_redirect_301(self):
        conf = self._conf()
        assert re.search(r"return\s+301\s+https://", conf), \
            "Port 80 must return 301 redirect to HTTPS"

    # --- Logging ---
    def test_access_log(self):
        conf = self._conf()
        assert re.search(r"access_log\s+/var/log/nginx/access\.log", conf), \
            "access_log must be set to /var/log/nginx/access.log"

    def test_error_log(self):
        conf = self._conf()
        assert re.search(r"error_log\s+/var/log/nginx/error\.log", conf), \
            "error_log must be set to /var/log/nginx/error.log"


# ============================================================================
# 4. Docker Compose tests
# ============================================================================

class TestDockerCompose:
    """Validate docker-compose.yml structure and content."""

    @staticmethod
    def _compose():
        content = read_file(os.path.join(APP_DIR, "docker-compose.yml"))
        if not content.strip():
            return None
        try:
            return yaml.safe_load(content)
        except yaml.YAMLError:
            return None

    def test_compose_is_valid_yaml(self):
        data = self._compose()
        assert data is not None, \
            "docker-compose.yml must be valid YAML"

    def test_compose_has_services(self):
        data = self._compose()
        assert data and "services" in data, \
            "docker-compose.yml must define 'services'"

    def test_compose_has_all_four_services(self):
        data = self._compose()
        assert data and "services" in data
        services = data["services"]
        for svc in ["nginx", "backend1", "backend2", "backend3"]:
            assert svc in services, \
                f"Service '{svc}' must be defined in docker-compose.yml"

    def test_nginx_port_80_mapped(self):
        data = self._compose()
        assert data and "services" in data
        nginx = data["services"].get("nginx", {})
        ports = [str(p) for p in nginx.get("ports", [])]
        ports_str = " ".join(ports)
        assert "80:80" in ports_str, \
            "nginx service must map host port 80 to container port 80"

    def test_nginx_port_443_mapped(self):
        data = self._compose()
        assert data and "services" in data
        nginx = data["services"].get("nginx", {})
        ports = [str(p) for p in nginx.get("ports", [])]
        ports_str = " ".join(ports)
        assert "443:443" in ports_str, \
            "nginx service must map host port 443 to container port 443"

    def test_nginx_depends_on_backends(self):
        data = self._compose()
        assert data and "services" in data
        nginx = data["services"].get("nginx", {})
        depends = nginx.get("depends_on", [])
        # depends_on can be a list or a dict
        if isinstance(depends, dict):
            dep_names = list(depends.keys())
        else:
            dep_names = list(depends)
        for backend in ["backend1", "backend2", "backend3"]:
            assert backend in dep_names, \
                f"nginx must depend_on {backend}"

    def test_nginx_volumes_mount_conf(self):
        data = self._compose()
        assert data and "services" in data
        nginx = data["services"].get("nginx", {})
        volumes = nginx.get("volumes", [])
        volumes_str = " ".join(str(v) for v in volumes)
        assert "nginx.conf" in volumes_str, \
            "nginx must mount nginx.conf as a volume"

    def test_nginx_volumes_mount_ssl(self):
        data = self._compose()
        assert data and "services" in data
        nginx = data["services"].get("nginx", {})
        volumes = nginx.get("volumes", [])
        volumes_str = " ".join(str(v) for v in volumes)
        assert "ssl" in volumes_str, \
            "nginx must mount ssl directory as a volume"

    def test_app_network_defined(self):
        data = self._compose()
        assert data is not None
        # Network can be defined at top level or implicitly via services
        networks = data.get("networks", {})
        assert "app_network" in networks, \
            "docker-compose.yml must define 'app_network' network"

    def test_all_services_on_app_network(self):
        data = self._compose()
        assert data and "services" in data
        for svc_name in ["nginx", "backend1", "backend2", "backend3"]:
            svc = data["services"].get(svc_name, {})
            svc_networks = svc.get("networks", [])
            if isinstance(svc_networks, dict):
                net_names = list(svc_networks.keys())
            else:
                net_names = list(svc_networks)
            assert "app_network" in net_names, \
                f"Service '{svc_name}' must be on 'app_network'"


# ============================================================================
# 5. Backend Dockerfile tests
# ============================================================================

class TestBackendDockerfile:
    """Validate backend Dockerfile structure."""

    @staticmethod
    def _dockerfile():
        return read_file(os.path.join(APP_DIR, "backend", "Dockerfile"))

    def test_dockerfile_not_empty(self):
        content = self._dockerfile()
        assert len(content.strip()) > 10, \
            "Backend Dockerfile must not be empty"

    def test_dockerfile_has_from(self):
        content = self._dockerfile()
        assert re.search(r"^FROM\s+", content, re.MULTILINE | re.IGNORECASE), \
            "Backend Dockerfile must have a FROM instruction"

    def test_dockerfile_exposes_port(self):
        content = self._dockerfile()
        # Should expose a port (8080 or variable)
        assert re.search(r"EXPOSE", content, re.IGNORECASE), \
            "Backend Dockerfile should EXPOSE a port"

    def test_dockerfile_has_cmd_or_entrypoint(self):
        content = self._dockerfile()
        has_cmd = re.search(r"^CMD\s+", content, re.MULTILINE | re.IGNORECASE)
        has_entry = re.search(r"^ENTRYPOINT\s+", content, re.MULTILINE | re.IGNORECASE)
        assert has_cmd or has_entry, \
            "Backend Dockerfile must have CMD or ENTRYPOINT"


# ============================================================================
# 6. Documentation tests
# ============================================================================

class TestDocumentation:
    """Validate configuration.md content."""

    @staticmethod
    def _doc():
        return read_file(os.path.join(APP_DIR, "docs", "configuration.md"))

    def test_doc_not_empty(self):
        doc = self._doc()
        assert len(doc.strip()) > 100, \
            "configuration.md must contain substantial documentation"

    def test_doc_mentions_all_services(self):
        doc = self._doc().lower()
        for svc in ["nginx", "backend1", "backend2", "backend3"]:
            assert svc in doc, \
                f"Documentation must mention service '{svc}'"

    def test_doc_has_service_table(self):
        doc = self._doc()
        # Markdown tables use | as delimiter; expect at least a few rows
        pipe_lines = [l for l in doc.split("\n") if l.strip().startswith("|")]
        assert len(pipe_lines) >= 3, \
            "Documentation must include a table (at least header + separator + 1 row)"

    def test_doc_mentions_load_balancing_algorithm(self):
        doc = self._doc().lower()
        assert "least_conn" in doc or "least conn" in doc, \
            "Documentation must mention the least_conn load balancing algorithm"

    def test_doc_explains_algorithm_rationale(self):
        doc = self._doc().lower()
        # Should explain WHY least_conn is chosen
        rationale_keywords = ["even", "distribut", "connection", "balanc", "vary"]
        matches = sum(1 for kw in rationale_keywords if kw in doc)
        assert matches >= 2, \
            "Documentation must explain why the load balancing algorithm was chosen"

    def test_doc_mentions_ssl_protocols(self):
        doc = self._doc()
        assert "TLSv1.2" in doc and "TLSv1.3" in doc, \
            "Documentation must mention TLSv1.2 and TLSv1.3 protocols"

    def test_doc_mentions_certificate_type(self):
        doc = self._doc().lower()
        assert "self-signed" in doc or "self signed" in doc, \
            "Documentation must mention self-signed certificate type"

    def test_doc_mentions_health_checks(self):
        doc = self._doc().lower()
        assert "health" in doc, \
            "Documentation must describe health check mechanism"

    def test_doc_mentions_ports(self):
        doc = self._doc()
        for port in ["8080", "8081", "8082"]:
            assert port in doc, \
                f"Documentation must mention port {port}"
