"""
Tests for Multi-Container Micro-Service Health Dashboard.

Validates:
- Required file existence and structure
- Docker Compose configuration (services, network, ports)
- Prometheus configuration (scrape interval, jobs, targets)
- Nginx configuration (hostnames, SSL, redirect)
- Grafana provisioning (datasource, dashboard provider, dashboard panels)
- TLS certificate existence
- Live container status and network membership
- HTTP endpoint accessibility via Nginx reverse proxy
- HTTP -> HTTPS redirect behavior
"""

import os
import json
import subprocess
import re

import yaml

APP_DIR = "/app"


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def _read_file(path):
    """Read file content, return empty string if missing."""
    try:
        with open(path, "r") as f:
            return f.read()
    except (FileNotFoundError, IsADirectoryError):
        return ""


def _load_yaml(path):
    """Load a YAML file, return None on failure."""
    content = _read_file(path)
    if not content:
        return None
    try:
        return yaml.safe_load(content)
    except yaml.YAMLError:
        return None


def _load_json(path):
    """Load a JSON file, return None on failure."""
    content = _read_file(path)
    if not content:
        return None
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return None


def _find_nginx_config():
    """Locate the nginx config file — could be nginx.conf or conf.d/default.conf."""
    candidates = [
        os.path.join(APP_DIR, "nginx", "nginx.conf"),
        os.path.join(APP_DIR, "nginx", "conf.d", "default.conf"),
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    return None


def _run(cmd, timeout=30):
    """Run a shell command and return (returncode, stdout, stderr)."""
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "timeout"


# ===========================================================================
# 1. FILE EXISTENCE TESTS
# ===========================================================================

class TestFileExistence:
    """Verify all required files are present."""

    def test_docker_compose_exists(self):
        assert os.path.isfile(os.path.join(APP_DIR, "docker-compose.yml")), \
            "docker-compose.yml must exist at /app/docker-compose.yml"

    def test_prometheus_config_exists(self):
        assert os.path.isfile(os.path.join(APP_DIR, "prometheus", "prometheus.yml")), \
            "prometheus.yml must exist at /app/prometheus/prometheus.yml"

    def test_grafana_dashboard_exists(self):
        assert os.path.isfile(os.path.join(APP_DIR, "grafana", "dashboards", "services.json")), \
            "services.json must exist at /app/grafana/dashboards/services.json"

    def test_nginx_config_exists(self):
        cfg = _find_nginx_config()
        assert cfg is not None, \
            "Nginx config must exist at /app/nginx/nginx.conf or /app/nginx/conf.d/default.conf"

    def test_tls_cert_exists(self):
        assert os.path.isfile(os.path.join(APP_DIR, "nginx", "certs", "server.crt")), \
            "TLS certificate must exist at /app/nginx/certs/server.crt"

    def test_tls_key_exists(self):
        assert os.path.isfile(os.path.join(APP_DIR, "nginx", "certs", "server.key")), \
            "TLS key must exist at /app/nginx/certs/server.key"

    def test_service_dockerfiles_exist(self):
        for i in range(1, 4):
            svc_dir = os.path.join(APP_DIR, "services", f"svc{i}")
            dockerfile = os.path.join(svc_dir, "Dockerfile")
            assert os.path.isfile(dockerfile), \
                f"Dockerfile must exist for demo-svc-{i} at {dockerfile}"


# ===========================================================================
# 2. DOCKER COMPOSE CONFIGURATION TESTS
# ===========================================================================

class TestDockerCompose:
    """Validate docker-compose.yml structure."""

    def _load(self):
        return _load_yaml(os.path.join(APP_DIR, "docker-compose.yml"))

    def test_valid_yaml(self):
        dc = self._load()
        assert dc is not None, "docker-compose.yml must be valid YAML"

    def test_has_services_section(self):
        dc = self._load()
        assert dc and "services" in dc, "docker-compose.yml must have a 'services' section"

    def test_required_services_defined(self):
        dc = self._load()
        assert dc and "services" in dc
        services = dc["services"]
        required = ["demo-svc-1", "demo-svc-2", "demo-svc-3", "prometheus", "grafana", "nginx"]
        for svc in required:
            assert svc in services, f"Service '{svc}' must be defined in docker-compose.yml"

    def test_micro_stack_network_defined(self):
        dc = self._load()
        assert dc is not None
        networks = dc.get("networks", {})
        assert "micro-stack" in networks, \
            "A custom network named 'micro-stack' must be defined"

    def test_micro_stack_network_bridge_driver(self):
        dc = self._load()
        assert dc is not None
        networks = dc.get("networks", {})
        net = networks.get("micro-stack", {})
        # If driver is not specified, Docker defaults to bridge, which is acceptable.
        # But if specified, it must be bridge.
        if net and "driver" in net:
            assert net["driver"] == "bridge", \
                "micro-stack network driver must be 'bridge'"

    def test_all_services_on_micro_stack(self):
        dc = self._load()
        assert dc and "services" in dc
        for name, svc_cfg in dc["services"].items():
            nets = svc_cfg.get("networks", [])
            # networks can be a list or a dict
            if isinstance(nets, list):
                assert "micro-stack" in nets, \
                    f"Service '{name}' must be on the 'micro-stack' network"
            elif isinstance(nets, dict):
                assert "micro-stack" in nets, \
                    f"Service '{name}' must be on the 'micro-stack' network"

    def test_nginx_exposes_port_80(self):
        dc = self._load()
        assert dc and "services" in dc
        nginx = dc["services"].get("nginx", {})
        ports = [str(p) for p in nginx.get("ports", [])]
        port_str = " ".join(ports)
        assert "80" in port_str, "Nginx must expose port 80 to the host"

    def test_nginx_exposes_port_443(self):
        dc = self._load()
        assert dc and "services" in dc
        nginx = dc["services"].get("nginx", {})
        ports = [str(p) for p in nginx.get("ports", [])]
        port_str = " ".join(ports)
        assert "443" in port_str, "Nginx must expose port 443 to the host"


# ===========================================================================
# 3. PROMETHEUS CONFIGURATION TESTS
# ===========================================================================

class TestPrometheusConfig:
    """Validate prometheus.yml content."""

    def _load(self):
        return _load_yaml(os.path.join(APP_DIR, "prometheus", "prometheus.yml"))

    def test_valid_yaml(self):
        cfg = self._load()
        assert cfg is not None, "prometheus.yml must be valid YAML"

    def test_scrape_interval_5s(self):
        cfg = self._load()
        assert cfg is not None
        global_cfg = cfg.get("global", {})
        interval = str(global_cfg.get("scrape_interval", ""))
        assert interval.replace(" ", "") == "5s", \
            f"Global scrape_interval must be '5s', got '{interval}'"

    def test_has_scrape_configs(self):
        cfg = self._load()
        assert cfg is not None
        assert "scrape_configs" in cfg, "prometheus.yml must have scrape_configs"
        assert len(cfg["scrape_configs"]) >= 1

    def test_prometheus_self_scrape_job(self):
        cfg = self._load()
        assert cfg is not None
        jobs = cfg.get("scrape_configs", [])
        job_names = [j.get("job_name", "") for j in jobs]
        assert "prometheus" in job_names, \
            "Must have a scrape job named 'prometheus' for self-scraping"

    def test_demo_services_scrape_targets(self):
        """All three demo services must be scraped — either as one job or individual jobs."""
        cfg = self._load()
        assert cfg is not None
        jobs = cfg.get("scrape_configs", [])

        # Collect all targets across all jobs (excluding the prometheus self-scrape)
        all_targets = []
        for job in jobs:
            for sc in job.get("static_configs", []):
                targets = sc.get("targets", [])
                all_targets.extend(targets)

        all_targets_str = " ".join(all_targets).lower()

        for i in range(1, 4):
            port = 8000 + i
            # Check that the service is targeted — flexible on naming
            svc_found = (
                f"demo-svc-{i}:{port}" in all_targets_str
                or f"demo-svc-{i}" in all_targets_str
                or f"svc{i}" in all_targets_str
            )
            assert svc_found, \
                f"demo-svc-{i} (port {port}) must be a Prometheus scrape target"


# ===========================================================================
# 4. NGINX CONFIGURATION TESTS
# ===========================================================================

class TestNginxConfig:
    """Validate Nginx configuration content."""

    def _content(self):
        cfg_path = _find_nginx_config()
        if cfg_path is None:
            # Also try reading all files under nginx/ to find config
            nginx_dir = os.path.join(APP_DIR, "nginx")
            if os.path.isdir(nginx_dir):
                for root, _, files in os.walk(nginx_dir):
                    for f in files:
                        if f.endswith(".conf"):
                            return _read_file(os.path.join(root, f))
            return ""
        return _read_file(cfg_path)

    def test_has_all_hostnames(self):
        content = self._content()
        assert content, "Nginx config file must exist and be non-empty"
        required_hosts = [
            "svc1.local.dev", "svc2.local.dev", "svc3.local.dev",
            "prom.local.dev", "graf.local.dev",
        ]
        for host in required_hosts:
            assert host in content, \
                f"Nginx config must contain server_name for '{host}'"

    def test_listens_on_443(self):
        content = self._content()
        assert content
        assert re.search(r"listen\s+443", content), \
            "Nginx must listen on port 443 (HTTPS)"

    def test_listens_on_80(self):
        content = self._content()
        assert content
        assert re.search(r"listen\s+80", content), \
            "Nginx must listen on port 80 (HTTP)"

    def test_ssl_configured(self):
        content = self._content()
        assert content
        assert "ssl" in content.lower(), \
            "Nginx config must reference SSL/TLS"

    def test_http_to_https_redirect(self):
        content = self._content()
        assert content
        # Should have a 301 redirect from HTTP to HTTPS
        assert "301" in content, \
            "Nginx config must include a 301 redirect (HTTP -> HTTPS)"

    def test_proxy_pass_demo_services(self):
        content = self._content()
        assert content
        for i in range(1, 4):
            port = 8000 + i
            # Flexible: proxy_pass could reference service name or localhost
            pattern = f"demo-svc-{i}:{port}"
            assert pattern in content, \
                f"Nginx must proxy_pass to demo-svc-{i}:{port}"

    def test_proxy_pass_prometheus(self):
        content = self._content()
        assert content
        assert re.search(r"prometheus[:\s]+9090", content) or "prometheus:9090" in content, \
            "Nginx must proxy_pass to prometheus:9090"

    def test_proxy_pass_grafana(self):
        content = self._content()
        assert content
        assert re.search(r"grafana[:\s]+3000", content) or "grafana:3000" in content, \
            "Nginx must proxy_pass to grafana:3000"


# ===========================================================================
# 5. GRAFANA PROVISIONING TESTS
# ===========================================================================

class TestGrafanaProvisioning:
    """Validate Grafana datasource, dashboard provider, and dashboard JSON."""

    def test_datasource_provisioning_exists(self):
        prov_dir = os.path.join(APP_DIR, "grafana", "provisioning", "datasources")
        assert os.path.isdir(prov_dir), \
            "Grafana datasource provisioning directory must exist"
        yamls = [f for f in os.listdir(prov_dir) if f.endswith((".yml", ".yaml"))]
        assert len(yamls) >= 1, \
            "At least one datasource YAML must exist in provisioning/datasources/"

    def test_datasource_points_to_prometheus(self):
        prov_dir = os.path.join(APP_DIR, "grafana", "provisioning", "datasources")
        if not os.path.isdir(prov_dir):
            assert False, "Datasource provisioning dir missing"
        combined = ""
        for f in os.listdir(prov_dir):
            if f.endswith((".yml", ".yaml")):
                combined += _read_file(os.path.join(prov_dir, f))
        assert "prometheus" in combined.lower(), \
            "Datasource provisioning must reference Prometheus"

    def test_dashboard_provider_exists(self):
        prov_dir = os.path.join(APP_DIR, "grafana", "provisioning", "dashboards")
        assert os.path.isdir(prov_dir), \
            "Grafana dashboard provisioning directory must exist"
        yamls = [f for f in os.listdir(prov_dir) if f.endswith((".yml", ".yaml"))]
        assert len(yamls) >= 1, \
            "At least one dashboard provider YAML must exist in provisioning/dashboards/"

    def test_dashboard_json_valid(self):
        dash = _load_json(os.path.join(APP_DIR, "grafana", "dashboards", "services.json"))
        assert dash is not None, "services.json must be valid JSON"

    def test_dashboard_has_panels(self):
        dash = _load_json(os.path.join(APP_DIR, "grafana", "dashboards", "services.json"))
        assert dash is not None
        panels = dash.get("panels", [])
        # At least 6 panels: 3 UP status + 3 requests/s
        assert len(panels) >= 6, \
            f"Dashboard must have at least 6 panels (3 UP + 3 RPS), found {len(panels)}"

    def test_dashboard_has_up_panels(self):
        """Each demo service must have a panel using the 'up' metric."""
        dash = _load_json(os.path.join(APP_DIR, "grafana", "dashboards", "services.json"))
        assert dash is not None
        panels_json = json.dumps(dash.get("panels", []))
        # Check that 'up' metric is referenced
        assert re.search(r'\bup\b', panels_json), \
            "Dashboard must contain panels using the 'up' metric"

    def test_dashboard_has_requests_panels(self):
        """Each demo service must have a panel using http_requests_total."""
        dash = _load_json(os.path.join(APP_DIR, "grafana", "dashboards", "services.json"))
        assert dash is not None
        panels_json = json.dumps(dash.get("panels", []))
        assert "http_requests_total" in panels_json, \
            "Dashboard must contain panels using 'http_requests_total' metric"

    def test_dashboard_covers_all_services(self):
        """Dashboard panels must reference all three demo services."""
        dash = _load_json(os.path.join(APP_DIR, "grafana", "dashboards", "services.json"))
        assert dash is not None
        panels_json = json.dumps(dash.get("panels", [])).lower()
        for i in range(1, 4):
            assert f"svc-{i}" in panels_json or f"svc{i}" in panels_json, \
                f"Dashboard must reference demo-svc-{i}"


# ===========================================================================
# 6. LIVE CONTAINER TESTS
# ===========================================================================

class TestContainersRunning:
    """Verify Docker containers are up and on the correct network."""

    def test_all_containers_running(self):
        """All 6 containers must be in running state."""
        rc, out, _ = _run("docker compose -f /app/docker-compose.yml ps --format json", timeout=30)
        if rc != 0:
            # Fallback: try plain ps
            rc, out, _ = _run("docker compose -f /app/docker-compose.yml ps", timeout=30)
        assert rc == 0, "docker compose ps must succeed"

        required = ["demo-svc-1", "demo-svc-2", "demo-svc-3", "prometheus", "grafana", "nginx"]
        out_lower = out.lower()
        for svc in required:
            assert svc.lower() in out_lower, \
                f"Container '{svc}' must appear in docker compose ps output"

    def test_containers_on_micro_stack_network(self):
        """At least the key containers must be on a network containing 'micro-stack'."""
        rc, out, _ = _run("docker network ls --format '{{.Name}}'", timeout=15)
        assert rc == 0
        # Find the actual network name (may have a project prefix)
        network_name = None
        for line in out.strip().splitlines():
            if "micro-stack" in line:
                network_name = line.strip()
                break
        assert network_name is not None, \
            "A Docker network containing 'micro-stack' must exist"

        rc2, inspect_out, _ = _run(
            f"docker network inspect {network_name} --format '{{{{json .Containers}}}}'",
            timeout=15,
        )
        assert rc2 == 0
        inspect_lower = inspect_out.lower()
        # At least nginx and one demo service should be on the network
        assert "nginx" in inspect_lower, "nginx must be on the micro-stack network"
        assert "demo-svc" in inspect_lower or "demo_svc" in inspect_lower, \
            "Demo services must be on the micro-stack network"


# ===========================================================================
# 7. LIVE HTTP ENDPOINT TESTS
# ===========================================================================

class TestHTTPEndpoints:
    """Verify services are reachable through Nginx reverse proxy."""

    def test_svc1_https_200(self):
        rc, out, _ = _run(
            "curl -sk --resolve svc1.local.dev:443:127.0.0.1 "
            "https://svc1.local.dev/ -o /dev/null -w '%{http_code}'",
            timeout=15,
        )
        assert rc == 0 and out.strip().strip("'") == "200", \
            f"svc1.local.dev HTTPS must return 200, got rc={rc} out={out}"

    def test_svc2_https_200(self):
        rc, out, _ = _run(
            "curl -sk --resolve svc2.local.dev:443:127.0.0.1 "
            "https://svc2.local.dev/ -o /dev/null -w '%{http_code}'",
            timeout=15,
        )
        assert rc == 0 and out.strip().strip("'") == "200", \
            f"svc2.local.dev HTTPS must return 200, got rc={rc} out={out}"

    def test_svc3_https_200(self):
        rc, out, _ = _run(
            "curl -sk --resolve svc3.local.dev:443:127.0.0.1 "
            "https://svc3.local.dev/ -o /dev/null -w '%{http_code}'",
            timeout=15,
        )
        assert rc == 0 and out.strip().strip("'") == "200", \
            f"svc3.local.dev HTTPS must return 200, got rc={rc} out={out}"

    def test_prometheus_https_200(self):
        rc, out, _ = _run(
            "curl -sk --resolve prom.local.dev:443:127.0.0.1 "
            "https://prom.local.dev/ -o /dev/null -w '%{http_code}'",
            timeout=15,
        )
        code = out.strip().strip("'")
        # Prometheus may return 200 or 302 (redirect to /graph)
        assert rc == 0 and code in ("200", "302"), \
            f"prom.local.dev HTTPS must return 200 or 302, got rc={rc} out={out}"

    def test_grafana_https_200(self):
        rc, out, _ = _run(
            "curl -sk --resolve graf.local.dev:443:127.0.0.1 "
            "https://graf.local.dev/ -o /dev/null -w '%{http_code}'",
            timeout=15,
        )
        code = out.strip().strip("'")
        # Grafana may return 200 or 302 (redirect to /login)
        assert rc == 0 and code in ("200", "302"), \
            f"graf.local.dev HTTPS must return 200 or 302, got rc={rc} out={out}"

    def test_svc1_returns_json(self):
        """Demo service 1 must return JSON with service name and status ok."""
        rc, out, _ = _run(
            "curl -sk --resolve svc1.local.dev:443:127.0.0.1 "
            "https://svc1.local.dev/",
            timeout=15,
        )
        assert rc == 0 and out.strip(), "svc1 must return a response body"
        try:
            body = json.loads(out.strip())
        except json.JSONDecodeError:
            assert False, f"svc1 response must be valid JSON, got: {out[:200]}"
        assert body.get("status") == "ok", \
            f"svc1 JSON must have status=ok, got {body}"
        assert "svc" in body.get("service", "").lower() or "1" in body.get("service", ""), \
            f"svc1 JSON must identify the service, got {body}"

    def test_http_to_https_redirect(self):
        """HTTP port 80 must return 301 redirect to HTTPS."""
        rc, out, _ = _run(
            "curl -sI --resolve svc1.local.dev:80:127.0.0.1 "
            "http://svc1.local.dev/ 2>&1",
            timeout=15,
        )
        assert rc == 0, "curl to HTTP port 80 must succeed"
        out_lower = out.lower()
        assert "301" in out, \
            f"HTTP request must get 301 redirect, got: {out[:300]}"
        assert "https" in out_lower, \
            f"301 Location header must point to https, got: {out[:300]}"
