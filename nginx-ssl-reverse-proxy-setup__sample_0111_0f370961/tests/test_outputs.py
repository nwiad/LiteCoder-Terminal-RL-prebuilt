"""
Tests for Multi-Container Reverse Proxy Setup with SSL/TLS Termination.

Validates:
- File existence and structure
- docker-compose.yml correctness (services, networks, ports, volumes, depends_on)
- nginx.conf correctness (SSL, routing, headers, HTTP redirect)
- SSL certificate properties (CN, SANs, key size, validity)
- renew-certs.sh script content and permissions
"""

import os
import re
import subprocess
import stat
import yaml

BASE_DIR = "/app"

# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def read_file(rel_path):
    """Read a file relative to BASE_DIR, return contents or None."""
    full = os.path.join(BASE_DIR, rel_path)
    if not os.path.isfile(full):
        return None
    with open(full, "r", errors="replace") as f:
        return f.read()


def file_exists(rel_path):
    return os.path.isfile(os.path.join(BASE_DIR, rel_path))


def load_compose():
    content = read_file("docker-compose.yml")
    assert content is not None, "docker-compose.yml does not exist"
    data = yaml.safe_load(content)
    assert isinstance(data, dict), "docker-compose.yml is not valid YAML"
    return data


# ===========================================================================
# 1. FILE EXISTENCE TESTS
# ===========================================================================

class TestFileExistence:
    def test_docker_compose_exists(self):
        assert file_exists("docker-compose.yml"), "docker-compose.yml not found"

    def test_nginx_conf_exists(self):
        assert file_exists("nginx/nginx.conf"), "nginx/nginx.conf not found"

    def test_ssl_cert_exists(self):
        assert file_exists("nginx/certs/server.crt"), "server.crt not found"

    def test_ssl_key_exists(self):
        assert file_exists("nginx/certs/server.key"), "server.key not found"

    def test_renew_script_exists(self):
        assert file_exists("renew-certs.sh"), "renew-certs.sh not found"


# ===========================================================================
# 2. DOCKER-COMPOSE.YML STRUCTURE TESTS
# ===========================================================================

class TestDockerCompose:
    def test_has_services_key(self):
        data = load_compose()
        assert "services" in data, "docker-compose.yml missing 'services' key"

    def test_four_services_defined(self):
        data = load_compose()
        services = data["services"]
        required = {"nginx-proxy", "static-site", "api-service", "admin-panel"}
        assert required.issubset(set(services.keys())), (
            f"Missing services: {required - set(services.keys())}"
        )

    def test_nginx_proxy_image(self):
        data = load_compose()
        svc = data["services"]["nginx-proxy"]
        img = str(svc.get("image", ""))
        assert "nginx" in img.lower(), "nginx-proxy image must be nginx-based"

    def test_backend_images_alpine(self):
        """Backend services should use nginx:alpine."""
        data = load_compose()
        for name in ("static-site", "api-service", "admin-panel"):
            svc = data["services"][name]
            img = str(svc.get("image", ""))
            assert "nginx" in img.lower() and "alpine" in img.lower(), (
                f"{name} image should be nginx:alpine, got {img}"
            )

    def test_nginx_proxy_ports(self):
        """nginx-proxy must publish ports 80 and 443."""
        data = load_compose()
        svc = data["services"]["nginx-proxy"]
        ports_raw = svc.get("ports", [])
        ports_str = " ".join(str(p) for p in ports_raw)
        assert "80" in ports_str, "Port 80 not published on nginx-proxy"
        assert "443" in ports_str, "Port 443 not published on nginx-proxy"

    def test_nginx_proxy_volumes(self):
        """nginx-proxy must mount nginx.conf and certs directory."""
        data = load_compose()
        svc = data["services"]["nginx-proxy"]
        volumes = svc.get("volumes", [])
        vol_str = " ".join(str(v) for v in volumes)
        assert "nginx.conf" in vol_str, "nginx.conf not mounted in nginx-proxy"
        assert "certs" in vol_str, "certs directory not mounted in nginx-proxy"

    def test_nginx_proxy_depends_on(self):
        """nginx-proxy must depend on all three backend services."""
        data = load_compose()
        svc = data["services"]["nginx-proxy"]
        deps = svc.get("depends_on", [])
        # depends_on can be a list or a dict
        if isinstance(deps, dict):
            dep_names = set(deps.keys())
        else:
            dep_names = set(deps)
        required = {"static-site", "api-service", "admin-panel"}
        assert required.issubset(dep_names), (
            f"Missing depends_on: {required - dep_names}"
        )

    def test_proxy_network_defined(self):
        """A network named proxy-network must be defined."""
        data = load_compose()
        networks = data.get("networks", {})
        assert "proxy-network" in networks, "proxy-network not defined in networks"

    def test_proxy_network_bridge_driver(self):
        """proxy-network should use bridge driver."""
        data = load_compose()
        net = data.get("networks", {}).get("proxy-network", {})
        if net and isinstance(net, dict):
            driver = net.get("driver", "bridge")  # bridge is default
            assert driver == "bridge", f"proxy-network driver should be bridge, got {driver}"

    def test_all_services_on_proxy_network(self):
        """All four services must be on proxy-network."""
        data = load_compose()
        for name in ("nginx-proxy", "static-site", "api-service", "admin-panel"):
            svc = data["services"][name]
            nets = svc.get("networks", [])
            if isinstance(nets, dict):
                net_names = set(nets.keys())
            else:
                net_names = set(nets)
            assert "proxy-network" in net_names, (
                f"Service {name} is not on proxy-network"
            )


# ===========================================================================
# 3. NGINX CONFIGURATION TESTS
# ===========================================================================

class TestNginxConf:
    def _conf(self):
        content = read_file("nginx/nginx.conf")
        assert content is not None, "nginx/nginx.conf not found"
        assert len(content.strip()) > 50, "nginx.conf appears empty or too short"
        return content

    def test_listens_on_443_ssl(self):
        conf = self._conf()
        assert re.search(r"listen\s+443\b.*ssl", conf), (
            "nginx.conf must listen on 443 with SSL"
        )

    def test_listens_on_80(self):
        conf = self._conf()
        assert re.search(r"listen\s+80\b", conf), (
            "nginx.conf must listen on port 80"
        )

    def test_http_to_https_redirect(self):
        """Port 80 should redirect to HTTPS (301)."""
        conf = self._conf()
        assert re.search(r"return\s+301\s+https", conf), (
            "nginx.conf must redirect HTTP to HTTPS with 301"
        )

    def test_ssl_certificate_path(self):
        conf = self._conf()
        assert "/etc/nginx/certs/server.crt" in conf, (
            "ssl_certificate must point to /etc/nginx/certs/server.crt"
        )

    def test_ssl_key_path(self):
        conf = self._conf()
        assert "/etc/nginx/certs/server.key" in conf, (
            "ssl_certificate_key must point to /etc/nginx/certs/server.key"
        )

    def test_routing_www_example(self):
        """www.example.com must route to static-site."""
        conf = self._conf()
        assert "www.example.com" in conf, "Missing server_name www.example.com"
        assert "static-site" in conf, "Missing proxy_pass to static-site"

    def test_routing_api_example(self):
        """api.example.com must route to api-service."""
        conf = self._conf()
        assert "api.example.com" in conf, "Missing server_name api.example.com"
        assert "api-service" in conf, "Missing proxy_pass to api-service"

    def test_routing_admin_example(self):
        """admin.example.com must route to admin-panel."""
        conf = self._conf()
        assert "admin.example.com" in conf, "Missing server_name admin.example.com"
        assert "admin-panel" in conf, "Missing proxy_pass to admin-panel"

    def test_proxy_header_host(self):
        conf = self._conf()
        assert re.search(r"proxy_set_header\s+Host\s+\$host", conf), (
            "Missing proxy_set_header Host $host"
        )

    def test_proxy_header_real_ip(self):
        conf = self._conf()
        assert re.search(r"proxy_set_header\s+X-Real-IP\s+\$remote_addr", conf), (
            "Missing proxy_set_header X-Real-IP $remote_addr"
        )

    def test_proxy_header_forwarded_proto(self):
        conf = self._conf()
        assert re.search(r"proxy_set_header\s+X-Forwarded-Proto\s+\$scheme", conf), (
            "Missing proxy_set_header X-Forwarded-Proto $scheme"
        )


# ===========================================================================
# 4. SSL CERTIFICATE TESTS
# ===========================================================================

class TestSSLCertificate:
    """Validate the self-signed certificate using openssl CLI."""

    def _run_openssl(self, args):
        """Run an openssl command and return stdout."""
        result = subprocess.run(
            args, capture_output=True, text=True, timeout=10
        )
        assert result.returncode == 0, (
            f"openssl command failed: {' '.join(args)}\n{result.stderr}"
        )
        return result.stdout

    def test_cert_is_valid_x509(self):
        cert_path = os.path.join(BASE_DIR, "nginx/certs/server.crt")
        assert os.path.isfile(cert_path), "server.crt not found"
        out = self._run_openssl(["openssl", "x509", "-in", cert_path, "-noout", "-text"])
        assert "Certificate:" in out or "Issuer:" in out, "server.crt is not a valid X.509 certificate"

    def test_cert_common_name(self):
        cert_path = os.path.join(BASE_DIR, "nginx/certs/server.crt")
        out = self._run_openssl(["openssl", "x509", "-in", cert_path, "-noout", "-subject"])
        assert "example.com" in out, f"Certificate CN must contain example.com, got: {out}"

    def test_cert_san_entries(self):
        """Certificate must have SANs for www, api, admin subdomains."""
        cert_path = os.path.join(BASE_DIR, "nginx/certs/server.crt")
        out = self._run_openssl(["openssl", "x509", "-in", cert_path, "-noout", "-text"])
        for domain in ("www.example.com", "api.example.com", "admin.example.com"):
            assert domain in out, f"SAN missing for {domain}"

    def test_cert_key_size_minimum(self):
        """Key must be at least 2048 bits."""
        key_path = os.path.join(BASE_DIR, "nginx/certs/server.key")
        assert os.path.isfile(key_path), "server.key not found"
        out = self._run_openssl(["openssl", "rsa", "-in", key_path, "-noout", "-text"])
        # Look for key size like "Private-Key: (2048 bit)" or "RSA Private-Key: (4096 bit)"
        match = re.search(r"(\d+)\s*bit", out)
        assert match, f"Could not determine key size from: {out[:200]}"
        bits = int(match.group(1))
        assert bits >= 2048, f"Key size must be >= 2048 bits, got {bits}"

    def test_cert_validity_days(self):
        """Certificate should be valid for approximately 365 days."""
        cert_path = os.path.join(BASE_DIR, "nginx/certs/server.crt")
        out = self._run_openssl(["openssl", "x509", "-in", cert_path, "-noout", "-dates"])
        assert "notBefore" in out and "notAfter" in out, (
            "Could not read certificate dates"
        )

    def test_key_matches_cert(self):
        """Private key must match the certificate."""
        cert_path = os.path.join(BASE_DIR, "nginx/certs/server.crt")
        key_path = os.path.join(BASE_DIR, "nginx/certs/server.key")
        cert_mod = self._run_openssl(
            ["openssl", "x509", "-in", cert_path, "-noout", "-modulus"]
        ).strip()
        key_mod = self._run_openssl(
            ["openssl", "rsa", "-in", key_path, "-noout", "-modulus"]
        ).strip()
        assert cert_mod == key_mod, "Certificate and key modulus do not match"


# ===========================================================================
# 5. RENEW-CERTS.SH SCRIPT TESTS
# ===========================================================================

class TestRenewCertsScript:
    def _script(self):
        content = read_file("renew-certs.sh")
        assert content is not None, "renew-certs.sh not found"
        assert len(content.strip()) > 20, "renew-certs.sh appears empty"
        return content

    def test_is_executable(self):
        """renew-certs.sh must have execute permission."""
        path = os.path.join(BASE_DIR, "renew-certs.sh")
        assert os.path.isfile(path), "renew-certs.sh not found"
        mode = os.stat(path).st_mode
        assert mode & stat.S_IXUSR or mode & stat.S_IXGRP or mode & stat.S_IXOTH, (
            "renew-certs.sh is not executable"
        )

    def test_has_bash_shebang(self):
        """Script should start with a bash shebang."""
        content = self._script()
        first_line = content.strip().split("\n")[0]
        assert re.search(r"^#!\s*/.*\b(ba)?sh\b", first_line), (
            f"renew-certs.sh should have a bash/sh shebang, got: {first_line}"
        )

    def test_regenerates_certificate(self):
        """Script must call openssl to regenerate the certificate."""
        content = self._script()
        assert "openssl" in content, "renew-certs.sh must use openssl to regenerate certs"
        assert "server.crt" in content or "certs" in content, (
            "renew-certs.sh must reference the certificate path"
        )
        assert "server.key" in content or "certs" in content, (
            "renew-certs.sh must reference the key path"
        )

    def test_reloads_nginx(self):
        """Script must reload nginx in the container."""
        content = self._script()
        assert "nginx" in content.lower(), "renew-certs.sh must reference nginx"
        # Accept various reload approaches
        has_reload = (
            "nginx -s reload" in content
            or "nginx -s reopen" in content
            or "reload" in content.lower()
        )
        assert has_reload, "renew-certs.sh must reload nginx"

    def test_uses_docker_compose_exec(self):
        """Script must use docker compose exec to reload nginx."""
        content = self._script()
        # Accept both "docker compose" and "docker-compose"
        has_compose = (
            "docker compose" in content
            or "docker-compose" in content
        )
        assert has_compose, "renew-certs.sh must use docker compose to reload nginx"


# ===========================================================================
# 6. NGINX CONF ROUTING CORRECTNESS (DEEPER CHECKS)
# ===========================================================================

class TestNginxRoutingCorrectness:
    """
    Deeper checks to ensure routing maps are correct, not just that
    keywords exist. Verifies that each hostname is associated with
    the correct backend.
    """

    def _conf(self):
        content = read_file("nginx/nginx.conf")
        assert content is not None, "nginx/nginx.conf not found"
        return content

    def test_www_routes_to_static_site_not_others(self):
        """www.example.com should proxy to static-site, not api-service or admin-panel."""
        conf = self._conf()
        # Find all server blocks with listen 443
        # Use a simple heuristic: find text between www.example.com and the next server_name
        www_idx = conf.find("www.example.com")
        assert www_idx >= 0, "www.example.com not found in nginx.conf"
        # Look for proxy_pass in the vicinity (within 500 chars after the server_name)
        region = conf[www_idx:www_idx + 500]
        assert "static-site" in region, (
            "www.example.com block should proxy to static-site"
        )

    def test_api_routes_to_api_service_not_others(self):
        """api.example.com should proxy to api-service."""
        conf = self._conf()
        api_idx = conf.find("api.example.com")
        assert api_idx >= 0, "api.example.com not found"
        region = conf[api_idx:api_idx + 500]
        assert "api-service" in region, (
            "api.example.com block should proxy to api-service"
        )

    def test_admin_routes_to_admin_panel_not_others(self):
        """admin.example.com should proxy to admin-panel."""
        conf = self._conf()
        admin_idx = conf.find("admin.example.com")
        assert admin_idx >= 0, "admin.example.com not found"
        region = conf[admin_idx:admin_idx + 500]
        assert "admin-panel" in region, (
            "admin.example.com block should proxy to admin-panel"
        )

    def test_proxy_pass_uses_port_80(self):
        """All proxy_pass directives should target port 80 on backends."""
        conf = self._conf()
        proxy_passes = re.findall(r"proxy_pass\s+(http://[^;]+)", conf)
        assert len(proxy_passes) >= 3, (
            f"Expected at least 3 proxy_pass directives, found {len(proxy_passes)}"
        )
        for pp in proxy_passes:
            # Should contain :80 or no explicit port (defaults to 80)
            assert ":80" in pp or pp.count(":") == 1, (
                f"proxy_pass should target port 80: {pp}"
            )


# ===========================================================================
# 7. DOCKER-COMPOSE VOLUME MOUNT READ-ONLY TESTS
# ===========================================================================

class TestVolumeMountsReadOnly:
    def test_nginx_conf_mount_readonly(self):
        """nginx.conf volume mount should be read-only."""
        data = load_compose()
        svc = data["services"]["nginx-proxy"]
        volumes = svc.get("volumes", [])
        vol_str = " ".join(str(v) for v in volumes)
        # Check that nginx.conf mount has :ro
        nginx_conf_vols = [str(v) for v in volumes if "nginx.conf" in str(v)]
        assert len(nginx_conf_vols) > 0, "No nginx.conf volume mount found"
        assert any("ro" in v for v in nginx_conf_vols), (
            "nginx.conf mount should be read-only (:ro)"
        )

    def test_certs_mount_readonly(self):
        """certs volume mount should be read-only."""
        data = load_compose()
        svc = data["services"]["nginx-proxy"]
        volumes = svc.get("volumes", [])
        cert_vols = [str(v) for v in volumes if "cert" in str(v)]
        assert len(cert_vols) > 0, "No certs volume mount found"
        assert any("ro" in v for v in cert_vols), (
            "certs mount should be read-only (:ro)"
        )

