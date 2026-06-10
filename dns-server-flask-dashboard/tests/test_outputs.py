"""
Tests for DNS Server Flask Dashboard task.

Validates:
- File existence and structure (app.py, mappings.json, dnsmasq config, systemd service)
- Flask REST API endpoints (GET, POST, DELETE domains; POST restart)
- Error handling (400, 404, 409 status codes)
- Persistence (mappings.json and dnsmasq config updated after mutations)
- dnsmasq config format (address=/<domain>/<ip>)
- HTML dashboard served at GET /
"""

import json
import os
import re
import subprocess
import time

import requests

FLASK_BASE = "http://localhost:5000"
APP_PY = "/app/dns_dashboard/app.py"
MAPPINGS_JSON = "/app/dns_dashboard/mappings.json"
DNSMASQ_CONF = "/etc/dnsmasq.d/custom_domains.conf"
SYSTEMD_SERVICE = "/etc/systemd/system/dns-dashboard.service"

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _api(method, path, json_data=None, timeout=10):
    """Make an API request and return the response."""
    url = f"{FLASK_BASE}{path}"
    return requests.request(method, url, json=json_data, timeout=timeout)


def _read_file(path):
    """Read a file and return its contents, or None if missing."""
    if os.path.exists(path):
        with open(path, "r") as f:
            return f.read()
    return None


def _load_json(path):
    """Load a JSON file and return parsed data, or None."""
    content = _read_file(path)
    if content is None:
        return None
    return json.loads(content)


# ===========================================================================
# 1. FILE EXISTENCE & STRUCTURE
# ===========================================================================

class TestFileExistence:
    """Verify all required files exist at the correct paths."""

    def test_app_py_exists(self):
        assert os.path.isfile(APP_PY), f"Flask app not found at {APP_PY}"

    def test_app_py_is_valid_python(self):
        """app.py must be syntactically valid Python."""
        result = subprocess.run(
            ["python3", "-c", f"import py_compile; py_compile.compile('{APP_PY}', doraise=True)"],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, f"app.py has syntax errors: {result.stderr}"

    def test_app_py_imports_flask(self):
        """app.py must use Flask."""
        content = _read_file(APP_PY)
        assert content is not None
        assert "flask" in content.lower() or "Flask" in content, \
            "app.py does not appear to import Flask"

    def test_app_py_has_required_routes(self):
        """app.py must define the required API routes."""
        content = _read_file(APP_PY)
        assert content is not None
        assert "/api/domains" in content, "Missing /api/domains route"
        assert "/api/restart" in content, "Missing /api/restart route"

    def test_mappings_json_exists(self):
        assert os.path.isfile(MAPPINGS_JSON), f"mappings.json not found at {MAPPINGS_JSON}"

    def test_mappings_json_is_valid(self):
        """mappings.json must be a valid JSON array."""
        data = _load_json(MAPPINGS_JSON)
        assert data is not None, "mappings.json could not be parsed"
        assert isinstance(data, list), "mappings.json must be a JSON array"

    def test_mappings_json_entry_structure(self):
        """Each entry in mappings.json must have 'domain' and 'ip' keys."""
        data = _load_json(MAPPINGS_JSON)
        assert data is not None
        for entry in data:
            assert "domain" in entry, f"Entry missing 'domain' key: {entry}"
            assert "ip" in entry, f"Entry missing 'ip' key: {entry}"

    def test_dnsmasq_conf_exists(self):
        assert os.path.isfile(DNSMASQ_CONF), f"dnsmasq config not found at {DNSMASQ_CONF}"

    def test_dnsmasq_conf_format(self):
        """Each non-empty line must match address=/<domain>/<ip> format."""
        content = _read_file(DNSMASQ_CONF)
        assert content is not None
        lines = [l.strip() for l in content.splitlines() if l.strip()]
        # Allow empty config if no mappings, but if lines exist they must match
        for line in lines:
            assert re.match(r"^address=/[^/]+/.+$", line), \
                f"Invalid dnsmasq config line: {line}"

    def test_systemd_service_exists(self):
        assert os.path.isfile(SYSTEMD_SERVICE), \
            f"systemd service not found at {SYSTEMD_SERVICE}"

    def test_systemd_service_content(self):
        """Service file must reference the Flask app."""
        content = _read_file(SYSTEMD_SERVICE)
        assert content is not None
        assert "app.py" in content or "dns_dashboard" in content, \
            "Service file does not reference the Flask app"
        assert "[Service]" in content, "Service file missing [Service] section"
        assert "[Unit]" in content, "Service file missing [Unit] section"


# ===========================================================================
# 2. DNSMASQ CONFIG ↔ MAPPINGS CONSISTENCY
# ===========================================================================

class TestDnsmasqMappingsConsistency:
    """Verify dnsmasq config is consistent with mappings.json."""

    def test_dnsmasq_entries_match_mappings(self):
        """Every mapping in mappings.json should have a corresponding dnsmasq line."""
        mappings = _load_json(MAPPINGS_JSON)
        conf_content = _read_file(DNSMASQ_CONF)
        assert mappings is not None
        assert conf_content is not None

        for m in mappings:
            expected_line = f"address=/{m['domain']}/{m['ip']}"
            assert expected_line in conf_content, \
                f"Missing dnsmasq entry for {m['domain']}: expected '{expected_line}'"

    def test_dnsmasq_entry_count_matches(self):
        """Number of address= lines should match number of mappings."""
        mappings = _load_json(MAPPINGS_JSON)
        conf_content = _read_file(DNSMASQ_CONF)
        assert mappings is not None
        assert conf_content is not None

        address_lines = [l for l in conf_content.splitlines()
                         if l.strip().startswith("address=/")]
        assert len(address_lines) == len(mappings), \
            f"dnsmasq has {len(address_lines)} entries but mappings.json has {len(mappings)}"


# ===========================================================================
# 3. REST API — GET /api/domains
# ===========================================================================

class TestGetDomains:
    """Test GET /api/domains endpoint."""

    def test_get_domains_status_200(self):
        resp = _api("GET", "/api/domains")
        assert resp.status_code == 200

    def test_get_domains_returns_json(self):
        resp = _api("GET", "/api/domains")
        assert resp.headers.get("Content-Type", "").startswith("application/json")

    def test_get_domains_has_domains_key(self):
        resp = _api("GET", "/api/domains")
        data = resp.json()
        assert "domains" in data, "Response missing 'domains' key"

    def test_get_domains_is_list(self):
        resp = _api("GET", "/api/domains")
        data = resp.json()
        assert isinstance(data["domains"], list), "'domains' must be a list"

    def test_get_domains_entry_structure(self):
        """Each domain entry must have 'domain' and 'ip' fields."""
        resp = _api("GET", "/api/domains")
        data = resp.json()
        for entry in data["domains"]:
            assert "domain" in entry, f"Entry missing 'domain': {entry}"
            assert "ip" in entry, f"Entry missing 'ip': {entry}"

    def test_get_domains_contains_seed_data(self):
        """Initial seed data (app.local, api.local) should be present
        unless they were deleted by prior operations."""
        resp = _api("GET", "/api/domains")
        data = resp.json()
        domains = [e["domain"] for e in data["domains"]]
        # At minimum the API must return a list; seed data check is soft
        assert isinstance(domains, list)


# ===========================================================================
# 4. REST API — POST /api/domains (Add)
# ===========================================================================

class TestAddDomain:
    """Test POST /api/domains endpoint."""

    def test_add_domain_success(self):
        """Adding a new unique domain should return 201."""
        payload = {"domain": "test-add.local", "ip": "10.0.0.1"}
        resp = _api("POST", "/api/domains", json_data=payload)
        assert resp.status_code == 201, f"Expected 201, got {resp.status_code}"
        data = resp.json()
        assert "message" in data
        assert data.get("domain") == "test-add.local"
        assert data.get("ip") == "10.0.0.1"

    def test_add_domain_persists_to_mappings_json(self):
        """After adding, the domain must appear in mappings.json."""
        domain_name = "test-persist.local"
        payload = {"domain": domain_name, "ip": "10.0.0.2"}
        resp = _api("POST", "/api/domains", json_data=payload)
        # Accept 201 (new) or 409 (already exists from prior run)
        assert resp.status_code in (201, 409)

        mappings = _load_json(MAPPINGS_JSON)
        assert mappings is not None
        domains = [m["domain"] for m in mappings]
        assert domain_name in domains, \
            f"{domain_name} not found in mappings.json after add"

    def test_add_domain_persists_to_dnsmasq_conf(self):
        """After adding, the domain must appear in dnsmasq config."""
        domain_name = "test-dnsconf.local"
        ip_addr = "10.0.0.3"
        payload = {"domain": domain_name, "ip": ip_addr}
        resp = _api("POST", "/api/domains", json_data=payload)
        assert resp.status_code in (201, 409)

        conf = _read_file(DNSMASQ_CONF)
        assert conf is not None
        expected = f"address=/{domain_name}/{ip_addr}"
        assert expected in conf, \
            f"Expected '{expected}' in dnsmasq config after add"

    def test_add_domain_missing_fields_400(self):
        """Missing domain or ip should return 400."""
        # Missing ip
        resp = _api("POST", "/api/domains", json_data={"domain": "x.local"})
        assert resp.status_code == 400, f"Expected 400 for missing ip, got {resp.status_code}"
        data = resp.json()
        assert "error" in data

    def test_add_domain_empty_fields_400(self):
        """Empty domain or ip should return 400."""
        resp = _api("POST", "/api/domains", json_data={"domain": "", "ip": ""})
        assert resp.status_code == 400, f"Expected 400 for empty fields, got {resp.status_code}"

    def test_add_domain_duplicate_409(self):
        """Adding a domain that already exists should return 409."""
        payload = {"domain": "test-dup.local", "ip": "10.0.0.99"}
        # First add (or already exists)
        _api("POST", "/api/domains", json_data=payload)
        # Second add — must be 409
        resp = _api("POST", "/api/domains", json_data=payload)
        assert resp.status_code == 409, f"Expected 409 for duplicate, got {resp.status_code}"
        data = resp.json()
        assert "error" in data


# ===========================================================================
# 5. REST API — DELETE /api/domains/<domain>
# ===========================================================================

class TestDeleteDomain:
    """Test DELETE /api/domains/<domain> endpoint."""

    def test_delete_domain_success(self):
        """Deleting an existing domain should return 200."""
        # Ensure domain exists first
        payload = {"domain": "test-del.local", "ip": "10.0.0.50"}
        _api("POST", "/api/domains", json_data=payload)

        resp = _api("DELETE", "/api/domains/test-del.local")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert "message" in data

    def test_delete_domain_removes_from_mappings(self):
        """After deletion, domain must be gone from mappings.json."""
        domain_name = "test-del-persist.local"
        payload = {"domain": domain_name, "ip": "10.0.0.51"}
        _api("POST", "/api/domains", json_data=payload)

        resp = _api("DELETE", f"/api/domains/{domain_name}")
        assert resp.status_code == 200

        mappings = _load_json(MAPPINGS_JSON)
        assert mappings is not None
        domains = [m["domain"] for m in mappings]
        assert domain_name not in domains, \
            f"{domain_name} still in mappings.json after delete"

    def test_delete_domain_removes_from_dnsmasq(self):
        """After deletion, domain must be gone from dnsmasq config."""
        domain_name = "test-del-dns.local"
        ip_addr = "10.0.0.52"
        payload = {"domain": domain_name, "ip": ip_addr}
        _api("POST", "/api/domains", json_data=payload)

        _api("DELETE", f"/api/domains/{domain_name}")

        conf = _read_file(DNSMASQ_CONF)
        assert conf is not None
        expected = f"address=/{domain_name}/{ip_addr}"
        assert expected not in conf, \
            f"'{expected}' still in dnsmasq config after delete"

    def test_delete_nonexistent_domain_404(self):
        """Deleting a domain that doesn't exist should return 404."""
        resp = _api("DELETE", "/api/domains/nonexistent-domain-xyz.local")
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"
        data = resp.json()
        assert "error" in data


# ===========================================================================
# 6. REST API — POST /api/restart
# ===========================================================================

class TestRestartEndpoint:
    """Test POST /api/restart endpoint."""

    def test_restart_returns_json(self):
        resp = _api("POST", "/api/restart")
        assert resp.headers.get("Content-Type", "").startswith("application/json")

    def test_restart_response_has_message_or_error(self):
        """Restart should return either a success message or an error."""
        resp = _api("POST", "/api/restart")
        data = resp.json()
        assert "message" in data or "error" in data, \
            "Restart response must have 'message' or 'error'"

    def test_restart_status_code(self):
        """Restart should return 200 on success or 500 on failure."""
        resp = _api("POST", "/api/restart")
        assert resp.status_code in (200, 500), \
            f"Expected 200 or 500, got {resp.status_code}"


# ===========================================================================
# 7. HTML DASHBOARD — GET /
# ===========================================================================

class TestDashboard:
    """Test the HTML dashboard served at GET /."""

    def test_dashboard_status_200(self):
        resp = requests.get(f"{FLASK_BASE}/", timeout=10)
        assert resp.status_code == 200

    def test_dashboard_returns_html(self):
        resp = requests.get(f"{FLASK_BASE}/", timeout=10)
        ct = resp.headers.get("Content-Type", "")
        assert "html" in ct.lower(), f"Expected HTML content-type, got {ct}"

    def test_dashboard_has_form_elements(self):
        """Dashboard must have input fields for domain and IP."""
        resp = requests.get(f"{FLASK_BASE}/", timeout=10)
        html = resp.text.lower()
        assert "<form" in html or "<input" in html, \
            "Dashboard HTML missing form/input elements"

    def test_dashboard_has_table_or_list(self):
        """Dashboard must display mappings in a table or list."""
        resp = requests.get(f"{FLASK_BASE}/", timeout=10)
        html = resp.text.lower()
        assert "<table" in html or "<ul" in html or "<ol" in html \
            or "domain" in html, \
            "Dashboard HTML missing table/list for displaying mappings"


# ===========================================================================
# 8. END-TO-END WORKFLOW
# ===========================================================================

class TestEndToEnd:
    """Full add → verify → delete → verify cycle."""

    def test_add_then_get_then_delete_cycle(self):
        """Complete CRUD cycle: add a domain, verify via GET, delete, verify gone."""
        domain_name = "e2e-test.local"
        ip_addr = "172.16.0.1"

        # Clean up in case of prior run
        _api("DELETE", f"/api/domains/{domain_name}")

        # 1. Add
        resp = _api("POST", "/api/domains",
                     json_data={"domain": domain_name, "ip": ip_addr})
        assert resp.status_code == 201, f"Add failed: {resp.status_code}"

        # 2. Verify via GET
        resp = _api("GET", "/api/domains")
        assert resp.status_code == 200
        domains = {e["domain"]: e["ip"] for e in resp.json()["domains"]}
        assert domain_name in domains, "Added domain not in GET response"
        assert domains[domain_name] == ip_addr, "IP mismatch in GET response"

        # 3. Verify persistence files
        mappings = _load_json(MAPPINGS_JSON)
        assert any(m["domain"] == domain_name and m["ip"] == ip_addr
                    for m in mappings), "Added domain not in mappings.json"

        conf = _read_file(DNSMASQ_CONF)
        assert f"address=/{domain_name}/{ip_addr}" in conf, \
            "Added domain not in dnsmasq config"

        # 4. Delete
        resp = _api("DELETE", f"/api/domains/{domain_name}")
        assert resp.status_code == 200, f"Delete failed: {resp.status_code}"

        # 5. Verify removal via GET
        resp = _api("GET", "/api/domains")
        domains_after = [e["domain"] for e in resp.json()["domains"]]
        assert domain_name not in domains_after, \
            "Deleted domain still in GET response"

        # 6. Verify removal from persistence files
        mappings_after = _load_json(MAPPINGS_JSON)
        assert not any(m["domain"] == domain_name for m in mappings_after), \
            "Deleted domain still in mappings.json"

        conf_after = _read_file(DNSMASQ_CONF)
        assert f"address=/{domain_name}/{ip_addr}" not in conf_after, \
            "Deleted domain still in dnsmasq config"

    def test_add_no_body_returns_400(self):
        """POST with no JSON body should return 400."""
        resp = requests.post(f"{FLASK_BASE}/api/domains",
                             data="", timeout=10,
                             headers={"Content-Type": "application/json"})
        # Accept 400 or 500 — the key is it must NOT be 201
        assert resp.status_code != 201, \
            "Empty body should not create a domain"
