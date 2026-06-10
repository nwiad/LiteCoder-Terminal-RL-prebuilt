"""
Tests for the Nginx Docker Load Balancer task.
Validates all generated configuration files, SSL certs, and output.json
without requiring Docker runtime.
"""

import os
import json
import subprocess
import re
import yaml

BASE = "/app"


# ============================================================
# Helper utilities
# ============================================================

def read_file(rel_path):
    """Read a file relative to /app and return its contents."""
    full = os.path.join(BASE, rel_path)
    assert os.path.isfile(full), f"File not found: {full}"
    with open(full, "r") as f:
        return f.read()


def load_json(rel_path):
    content = read_file(rel_path)
    return json.loads(content)


def load_yaml(rel_path):
    content = read_file(rel_path)
    return yaml.safe_load(content)


# ============================================================
# 1. File existence tests
# ============================================================

REQUIRED_FILES = [
    "docker-compose.yml",
    "nginx/nginx.conf",
    "nginx/ssl/server.crt",
    "nginx/ssl/server.key",
    "backend/Dockerfile",
    "backend/app.py",
    "prometheus/prometheus.yml",
    "output.json",
]


def test_all_required_files_exist():
    """Every file listed in instruction.md must exist and be non-empty."""
    for rel in REQUIRED_FILES:
        full = os.path.join(BASE, rel)
        assert os.path.isfile(full), f"Missing required file: {full}"
        assert os.path.getsize(full) > 0, f"File is empty: {full}"


# ============================================================
# 2. output.json validation
# ============================================================

def test_output_json_structure():
    data = load_json("output.json")
    assert isinstance(data, dict), "output.json must be a JSON object"

    # Required keys
    for key in ["services", "network", "nginx_ports", "ssl_cn",
                "lb_method", "backend_count", "health_check_endpoint"]:
        assert key in data, f"output.json missing key: {key}"


def test_output_json_services():
    data = load_json("output.json")
    expected = {"backend1", "backend2", "backend3", "nginx", "prometheus", "grafana"}
    actual = set(data["services"])
    assert actual == expected, f"services mismatch: got {actual}"


def test_output_json_values():
    data = load_json("output.json")
    assert data["network"] == "lb-network"
    assert set(data["nginx_ports"]) == {80, 443}
    assert data["ssl_cn"] == "localhost"
    assert data["lb_method"] == "least_conn"
    assert data["backend_count"] == 3
    assert data["health_check_endpoint"] == "/health"


# ============================================================
# 3. docker-compose.yml validation
# ============================================================

def _load_compose():
    return load_yaml("docker-compose.yml")


def test_compose_has_all_services():
    dc = _load_compose()
    services = dc.get("services", {})
    expected = {"backend1", "backend2", "backend3", "nginx", "prometheus", "grafana"}
    assert expected.issubset(set(services.keys())), \
        f"Missing services. Found: {set(services.keys())}"


def test_compose_network_lb_network():
    dc = _load_compose()
    networks = dc.get("networks", {})
    assert "lb-network" in networks, "Network 'lb-network' not defined in docker-compose.yml"
    # Verify it's a bridge network (if driver is specified)
    net_cfg = networks["lb-network"]
    if isinstance(net_cfg, dict) and "driver" in net_cfg:
        assert net_cfg["driver"] == "bridge", "lb-network must use bridge driver"


def test_compose_services_on_lb_network():
    """All services must be connected to lb-network."""
    dc = _load_compose()
    services = dc.get("services", {})
    for name, svc in services.items():
        nets = svc.get("networks", [])
        if isinstance(nets, list):
            assert "lb-network" in nets, f"Service '{name}' not on lb-network"
        elif isinstance(nets, dict):
            assert "lb-network" in nets, f"Service '{name}' not on lb-network"


def test_compose_nginx_ports():
    dc = _load_compose()
    nginx = dc["services"]["nginx"]
    ports = nginx.get("ports", [])
    port_strs = [str(p) for p in ports]
    joined = " ".join(port_strs)
    assert "80" in joined, "Nginx must expose port 80"
    assert "443" in joined, "Nginx must expose port 443"


def test_compose_backends_no_host_ports():
    """Backend containers must NOT expose ports directly to the host."""
    dc = _load_compose()
    for name in ["backend1", "backend2", "backend3"]:
        svc = dc["services"][name]
        ports = svc.get("ports", [])
        assert len(ports) == 0, f"{name} must not expose ports to host, found: {ports}"


def test_compose_backend_healthchecks():
    """Each backend must have a healthcheck hitting /health with correct params."""
    dc = _load_compose()
    for name in ["backend1", "backend2", "backend3"]:
        svc = dc["services"][name]
        hc = svc.get("healthcheck", None)
        assert hc is not None, f"{name} missing healthcheck"

        test_cmd = hc.get("test", [])
        test_str = " ".join(str(x) for x in test_cmd) if isinstance(test_cmd, list) else str(test_cmd)
        assert "5000/health" in test_str or "5000/health" in test_str.replace(" ", ""), \
            f"{name} healthcheck must hit /health on port 5000"

        # Interval, timeout, retries — accept string or numeric forms
        interval = str(hc.get("interval", ""))
        assert "10" in interval, f"{name} healthcheck interval must be 10s"

        timeout = str(hc.get("timeout", ""))
        assert "5" in timeout, f"{name} healthcheck timeout must be 5s"

        retries = hc.get("retries", 0)
        assert int(retries) == 3, f"{name} healthcheck retries must be 3"


def test_compose_prometheus_port():
    dc = _load_compose()
    prom = dc["services"]["prometheus"]
    ports = prom.get("ports", [])
    port_strs = [str(p) for p in ports]
    joined = " ".join(port_strs)
    assert "9090" in joined, "Prometheus must expose port 9090"


def test_compose_grafana_port_and_password():
    dc = _load_compose()
    grafana = dc["services"]["grafana"]
    ports = grafana.get("ports", [])
    port_strs = [str(p) for p in ports]
    joined = " ".join(port_strs)
    assert "3000" in joined, "Grafana must expose port 3000"

    # Check admin password env var
    env = grafana.get("environment", [])
    if isinstance(env, list):
        env_str = " ".join(str(e) for e in env)
    elif isinstance(env, dict):
        env_str = " ".join(f"{k}={v}" for k, v in env.items())
    else:
        env_str = str(env)
    assert "GF_SECURITY_ADMIN_PASSWORD" in env_str, "Grafana must set GF_SECURITY_ADMIN_PASSWORD"
    assert "admin" in env_str, "Grafana admin password must be 'admin'"


# ============================================================
# 4. nginx.conf validation
# ============================================================

def test_nginx_upstream_block():
    """upstream 'backend' must list 3 backends on port 5000."""
    conf = read_file("nginx/nginx.conf")
    assert re.search(r"upstream\s+backend\s*\{", conf), \
        "nginx.conf must define an upstream block named 'backend'"
    for i in range(1, 4):
        assert f"backend{i}:5000" in conf, \
            f"nginx.conf upstream must include backend{i}:5000"


def test_nginx_least_conn():
    conf = read_file("nginx/nginx.conf")
    assert "least_conn" in conf, "nginx.conf must use least_conn load balancing"


def test_nginx_http_to_https_redirect():
    """Port 80 must redirect to HTTPS (301)."""
    conf = read_file("nginx/nginx.conf")
    assert "listen" in conf and "80" in conf, "nginx.conf must listen on port 80"
    assert re.search(r"return\s+301\s+https://", conf), \
        "nginx.conf must redirect HTTP to HTTPS with 301"


def test_nginx_ssl_config():
    conf = read_file("nginx/nginx.conf")
    assert re.search(r"listen\s+443\s+ssl", conf), \
        "nginx.conf must listen on 443 with ssl"
    assert "ssl_certificate" in conf, "nginx.conf must reference ssl_certificate"
    assert "ssl_certificate_key" in conf, "nginx.conf must reference ssl_certificate_key"


def test_nginx_proxy_headers():
    conf = read_file("nginx/nginx.conf")
    required_headers = ["X-Real-IP", "X-Forwarded-For", "X-Forwarded-Proto", "Host"]
    for hdr in required_headers:
        # Match proxy_set_header <Header> (case-insensitive for header name)
        pattern = rf"proxy_set_header\s+{re.escape(hdr)}\s+"
        assert re.search(pattern, conf, re.IGNORECASE), \
            f"nginx.conf must set proxy header: {hdr}"


def test_nginx_health_location():
    conf = read_file("nginx/nginx.conf")
    assert re.search(r"location\s+/health", conf), \
        "nginx.conf must have a location /health block"
    # Should return 200
    assert re.search(r"return\s+200", conf), \
        "nginx.conf /health must return 200"


def test_nginx_proxy_pass_to_upstream():
    conf = read_file("nginx/nginx.conf")
    assert re.search(r"proxy_pass\s+http://backend", conf), \
        "nginx.conf must proxy_pass to http://backend upstream"


# ============================================================
# 5. SSL certificate validation
# ============================================================

def test_ssl_certificate_is_valid_x509():
    """The .crt file must be a valid x509 certificate."""
    crt_path = os.path.join(BASE, "nginx/ssl/server.crt")
    result = subprocess.run(
        ["openssl", "x509", "-in", crt_path, "-noout", "-text"],
        capture_output=True, text=True
    )
    assert result.returncode == 0, f"server.crt is not a valid x509 cert: {result.stderr}"


def test_ssl_certificate_cn_localhost():
    crt_path = os.path.join(BASE, "nginx/ssl/server.crt")
    result = subprocess.run(
        ["openssl", "x509", "-in", crt_path, "-noout", "-subject"],
        capture_output=True, text=True
    )
    assert result.returncode == 0, f"Cannot read cert subject: {result.stderr}"
    assert "localhost" in result.stdout, \
        f"SSL cert CN must be 'localhost', got: {result.stdout.strip()}"


def test_ssl_certificate_validity_365_days():
    """Certificate must be valid for at least 365 days from its start date."""
    crt_path = os.path.join(BASE, "nginx/ssl/server.crt")
    result = subprocess.run(
        ["openssl", "x509", "-in", crt_path, "-noout", "-dates"],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    # Parse notBefore and notAfter
    from datetime import datetime
    lines = result.stdout.strip().split("\n")
    not_before = None
    not_after = None
    for line in lines:
        if line.startswith("notBefore="):
            not_before = line.split("=", 1)[1].strip()
        elif line.startswith("notAfter="):
            not_after = line.split("=", 1)[1].strip()

    assert not_before and not_after, "Could not parse certificate dates"

    # openssl date format: Mon DD HH:MM:SS YYYY GMT
    fmt = "%b %d %H:%M:%S %Y %Z"
    dt_before = datetime.strptime(not_before, fmt)
    dt_after = datetime.strptime(not_after, fmt)
    diff_days = (dt_after - dt_before).days
    assert diff_days >= 365, f"Cert validity {diff_days} days, must be >= 365"


def test_ssl_key_exists_and_valid():
    key_path = os.path.join(BASE, "nginx/ssl/server.key")
    # Try openssl pkey first (works for all key types), fall back to rsa
    result = subprocess.run(
        ["openssl", "pkey", "-in", key_path, "-noout"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        result = subprocess.run(
            ["openssl", "rsa", "-in", key_path, "-check", "-noout"],
            capture_output=True, text=True
        )
    assert result.returncode == 0, f"server.key is not a valid private key: {result.stderr}"


# ============================================================
# 6. Backend app.py validation
# ============================================================

def test_backend_app_has_flask():
    """Backend must be a Flask (or similar) app."""
    code = read_file("backend/app.py")
    # Accept Flask or other frameworks, but must import something web-related
    assert "flask" in code.lower() or "fastapi" in code.lower() or "http" in code.lower(), \
        "backend/app.py must use a web framework (Flask, FastAPI, etc.)"


def test_backend_app_root_route():
    code = read_file("backend/app.py")
    # Must define a route for "/"
    assert re.search(r'["\']\/["\']', code) or 'route("/")' in code or "route('/')" in code, \
        "backend/app.py must define a route for '/'"


def test_backend_app_health_route():
    code = read_file("backend/app.py")
    assert "/health" in code, "backend/app.py must define a /health endpoint"


def test_backend_app_json_response():
    """Root endpoint must return JSON with 'service' and 'status' keys."""
    code = read_file("backend/app.py")
    assert "service" in code, "backend/app.py root response must include 'service' key"
    assert "status" in code, "backend/app.py root response must include 'status' key"
    # Must use json in some form
    assert "json" in code.lower(), "backend/app.py must produce JSON responses"


def test_backend_app_port_5000():
    code = read_file("backend/app.py")
    assert "5000" in code, "backend/app.py must run on port 5000"


# ============================================================
# 7. Backend Dockerfile validation
# ============================================================

def test_backend_dockerfile_python_base():
    df = read_file("backend/Dockerfile")
    assert re.search(r"FROM\s+python", df, re.IGNORECASE), \
        "backend/Dockerfile must use a Python base image"


def test_backend_dockerfile_installs_flask():
    df = read_file("backend/Dockerfile")
    assert "flask" in df.lower(), \
        "backend/Dockerfile must install flask"


def test_backend_dockerfile_exposes_5000():
    df = read_file("backend/Dockerfile")
    assert "5000" in df, "backend/Dockerfile must reference port 5000"


# ============================================================
# 8. Prometheus configuration validation
# ============================================================

def test_prometheus_scrape_interval():
    prom = load_yaml("prometheus/prometheus.yml")
    global_cfg = prom.get("global", {})
    interval = str(global_cfg.get("scrape_interval", ""))
    assert "15" in interval, f"Prometheus scrape_interval must be 15s, got: {interval}"


def test_prometheus_nginx_job():
    prom = load_yaml("prometheus/prometheus.yml")
    scrape_configs = prom.get("scrape_configs", [])
    job_names = [sc.get("job_name", "") for sc in scrape_configs]
    assert "nginx" in job_names, \
        f"Prometheus must have a scrape job named 'nginx', found: {job_names}"
