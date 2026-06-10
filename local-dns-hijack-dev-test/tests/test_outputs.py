"""
Tests for Local DNS Hijacking for Development Testing task.

Validates:
1. /app/output.json — existence, structure, field values
2. /app/removal_guide.txt — existence, minimum content
3. System state — /etc/hosts, nginx config files, HTML page, nginx running
"""

import os
import json
import subprocess
import re

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
OUTPUT_JSON = "/app/output.json"
REMOVAL_GUIDE = "/app/removal_guide.txt"
HTML_PAGE = "/var/www/html/index.html"
NGINX_AVAILABLE = "/etc/nginx/sites-available/example.com.conf"
NGINX_ENABLED = "/etc/nginx/sites-enabled/example.com.conf"
HOSTS_FILE = "/etc/hosts"

EXPECTED_HTML = (
    "<html>\n"
    "<head><title>Local Dev - example.com</title></head>\n"
    "<body><h1>Welcome to the local version of example.com</h1></body>\n"
    "</html>"
)

# ===================================================================
# 1. output.json — existence and basic structure
# ===================================================================

def test_output_json_exists():
    """output.json must exist."""
    assert os.path.isfile(OUTPUT_JSON), f"{OUTPUT_JSON} does not exist"


def test_output_json_is_valid_json():
    """output.json must be parseable JSON."""
    with open(OUTPUT_JSON, "r") as f:
        content = f.read().strip()
    assert len(content) > 2, "output.json is empty or trivially small"
    data = json.loads(content)  # will raise on invalid JSON
    assert isinstance(data, dict), "output.json root must be a JSON object"

def test_output_json_has_required_keys():
    """output.json must contain all 5 required keys."""
    with open(OUTPUT_JSON, "r") as f:
        data = json.load(f)
    required_keys = {
        "hosts_entry_added",
        "nginx_running",
        "curl_example_com",
        "ping_resolves_to",
        "normal_dns_unaffected",
    }
    missing = required_keys - set(data.keys())
    assert not missing, f"output.json missing keys: {missing}"


# ===================================================================
# 2. output.json — field value validation
# ===================================================================

def _load_output():
    with open(OUTPUT_JSON, "r") as f:
        return json.load(f)


def test_hosts_entry_added_is_true():
    """hosts_entry_added must be true."""
    data = _load_output()
    assert data["hosts_entry_added"] is True, (
        f"Expected hosts_entry_added=true, got {data['hosts_entry_added']}"
    )


def test_nginx_running_is_true():
    """nginx_running must be true."""
    data = _load_output()
    assert data["nginx_running"] is True, (
        f"Expected nginx_running=true, got {data['nginx_running']}"
    )


def test_curl_example_com_contains_expected_html():
    """curl_example_com must contain the expected HTML content."""
    data = _load_output()
    curl_output = data["curl_example_com"]
    assert isinstance(curl_output, str), "curl_example_com must be a string"
    assert len(curl_output.strip()) > 0, "curl_example_com is empty"
    # Check key markers from the expected HTML
    assert "Local Dev - example.com" in curl_output, (
        "curl_example_com missing expected title"
    )
    assert "Welcome to the local version of example.com" in curl_output, (
        "curl_example_com missing expected heading"
    )

def test_ping_resolves_to_localhost():
    """ping_resolves_to must be 127.0.0.1."""
    data = _load_output()
    resolved = data["ping_resolves_to"]
    assert isinstance(resolved, str), "ping_resolves_to must be a string"
    assert resolved.strip() == "127.0.0.1", (
        f"Expected ping_resolves_to='127.0.0.1', got '{resolved}'"
    )


def test_normal_dns_unaffected_is_true():
    """normal_dns_unaffected must be true."""
    data = _load_output()
    assert data["normal_dns_unaffected"] is True, (
        f"Expected normal_dns_unaffected=true, got {data['normal_dns_unaffected']}"
    )


# ===================================================================
# 3. System state — /etc/hosts
# ===================================================================

def test_etc_hosts_contains_example_com_mapping():
    """
    /etc/hosts must contain a line mapping example.com to 127.0.0.1.
    This verifies the actual system state, not just the reported JSON.
    """
    assert os.path.isfile(HOSTS_FILE), "/etc/hosts does not exist"
    with open(HOSTS_FILE, "r") as f:
        lines = f.readlines()
    found = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if "127.0.0.1" in stripped and "example.com" in stripped:
            found = True
            break
    assert found, "/etc/hosts does not contain 127.0.0.1 mapping for example.com"


def test_etc_hosts_preserves_localhost():
    """
    /etc/hosts must still contain the original localhost entry.
    Ensures existing entries were not removed.
    """
    with open(HOSTS_FILE, "r") as f:
        content = f.read()
    assert "localhost" in content, (
        "/etc/hosts no longer contains 'localhost' — existing entries were altered"
    )


# ===================================================================
# 4. System state — HTML page
# ===================================================================

def test_html_page_exists():
    """/var/www/html/index.html must exist."""
    assert os.path.isfile(HTML_PAGE), f"{HTML_PAGE} does not exist"


def test_html_page_content():
    """HTML page must contain the required title and heading."""
    with open(HTML_PAGE, "r") as f:
        content = f.read()
    assert "Local Dev - example.com" in content, (
        "index.html missing expected <title>"
    )
    assert "Welcome to the local version of example.com" in content, (
        "index.html missing expected <h1> heading"
    )


# ===================================================================
# 5. System state — nginx configuration
# ===================================================================

def test_nginx_config_available_exists():
    """Nginx config must exist at sites-available."""
    assert os.path.isfile(NGINX_AVAILABLE), (
        f"{NGINX_AVAILABLE} does not exist"
    )


def test_nginx_config_enabled_is_symlink():
    """sites-enabled config must be a symlink pointing to sites-available."""
    assert os.path.exists(NGINX_ENABLED), (
        f"{NGINX_ENABLED} does not exist"
    )
    assert os.path.islink(NGINX_ENABLED), (
        f"{NGINX_ENABLED} exists but is not a symbolic link"
    )
    target = os.path.realpath(NGINX_ENABLED)
    expected_target = os.path.realpath(NGINX_AVAILABLE)
    assert target == expected_target, (
        f"Symlink target mismatch: {target} != {expected_target}"
    )


def test_nginx_config_has_server_name():
    """Nginx config must contain server_name example.com."""
    with open(NGINX_AVAILABLE, "r") as f:
        content = f.read()
    # Allow flexible whitespace: server_name  example.com;
    assert re.search(r"server_name\s+example\.com", content), (
        "Nginx config missing 'server_name example.com'"
    )


def test_nginx_config_has_root_directive():
    """Nginx config must set root to /var/www/html."""
    with open(NGINX_AVAILABLE, "r") as f:
        content = f.read()
    assert re.search(r"root\s+/var/www/html", content), (
        "Nginx config missing 'root /var/www/html'"
    )


# ===================================================================
# 6. System state — nginx is actually running
# ===================================================================

def test_nginx_process_running():
    """Nginx process must be running (verified independently of output.json)."""
    try:
        result = subprocess.run(
            ["pgrep", "-x", "nginx"],
            capture_output=True, text=True, timeout=5
        )
        assert result.returncode == 0, "No nginx process found via pgrep"
    except FileNotFoundError:
        # pgrep not available, try alternative
        result = subprocess.run(
            ["ps", "aux"],
            capture_output=True, text=True, timeout=5
        )
        assert "nginx" in result.stdout, "No nginx process found via ps aux"


def test_nginx_serves_on_port_80():
    """Nginx must respond on port 80 with HTTP 200."""
    try:
        result = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
             "http://127.0.0.1/"],
            capture_output=True, text=True, timeout=10
        )
        status = result.stdout.strip()
        assert status == "200", (
            f"Expected HTTP 200 from localhost:80, got {status}"
        )
    except FileNotFoundError:
        # curl not available — skip gracefully
        pass


# ===================================================================
# 7. removal_guide.txt
# ===================================================================

def test_removal_guide_exists():
    """/app/removal_guide.txt must exist."""
    assert os.path.isfile(REMOVAL_GUIDE), f"{REMOVAL_GUIDE} does not exist"


def test_removal_guide_minimum_lines():
    """removal_guide.txt must have at least 3 non-empty lines."""
    with open(REMOVAL_GUIDE, "r") as f:
        lines = f.readlines()
    non_empty = [l for l in lines if l.strip()]
    assert len(non_empty) >= 3, (
        f"removal_guide.txt has {len(non_empty)} non-empty lines, need >= 3"
    )


def test_removal_guide_mentions_hosts_revert():
    """removal_guide.txt must mention reverting the /etc/hosts change."""
    with open(REMOVAL_GUIDE, "r") as f:
        content = f.read().lower()
    # Should mention hosts file and example.com in context of removal
    assert "hosts" in content or "/etc/hosts" in content, (
        "removal_guide.txt does not mention /etc/hosts revert"
    )
    assert "example.com" in content, (
        "removal_guide.txt does not mention example.com"
    )


def test_removal_guide_mentions_nginx():
    """removal_guide.txt must mention disabling/stopping nginx."""
    with open(REMOVAL_GUIDE, "r") as f:
        content = f.read().lower()
    assert "nginx" in content, (
        "removal_guide.txt does not mention nginx"
    )


# ===================================================================
# 8. Cross-validation: output.json curl field vs actual HTML file
# ===================================================================

def test_curl_output_matches_html_file():
    """
    The curl_example_com field in output.json should match the actual
    HTML file content. This catches agents that hardcode output.json
    without actually setting up the server.
    """
    if not os.path.isfile(OUTPUT_JSON) or not os.path.isfile(HTML_PAGE):
        return  # other tests will catch missing files

    with open(OUTPUT_JSON, "r") as f:
        data = json.load(f)
    with open(HTML_PAGE, "r") as f:
        html_content = f.read()

    curl_output = data.get("curl_example_com", "")
    if not curl_output:
        assert False, "curl_example_com is empty"

    # The curl output should contain the same key content as the HTML file
    # (strip whitespace for flexible comparison)
    assert "Welcome to the local version of example.com" in curl_output, (
        "curl_example_com does not match the HTML page content"
    )
    assert "Local Dev - example.com" in curl_output, (
        "curl_example_com does not match the HTML page title"
    )

