import os
import json
import re


def test_haproxy_config_exists():
    """Test that HAProxy configuration file exists."""
    assert os.path.exists("/app/haproxy.cfg"), "HAProxy configuration file /app/haproxy.cfg not found"
    assert os.path.getsize("/app/haproxy.cfg") > 0, "HAProxy configuration file is empty"


def test_haproxy_config_frontend():
    """Test that HAProxy frontend is configured correctly."""
    with open("/app/haproxy.cfg", "r") as f:
        config = f.read()

    # Check for frontend section
    assert "frontend" in config, "Frontend section not found in HAProxy config"

    # Check frontend binds to port 80
    assert re.search(r"bind\s+[*:]*80", config), "Frontend not binding to port 80"

    # Check stats page is enabled
    assert "stats enable" in config or "stats uri" in config, "Stats page not enabled"
    assert "/haproxy?stats" in config, "Stats URI not set to /haproxy?stats"


def test_haproxy_config_backend():
    """Test that HAProxy backend is configured with 3 servers."""
    with open("/app/haproxy.cfg", "r") as f:
        config = f.read()

    # Check for backend section
    assert "backend" in config, "Backend section not found in HAProxy config"

    # Check for round-robin algorithm
    assert "roundrobin" in config, "Round-robin load balancing not configured"

    # Check for 3 backend servers on correct ports
    assert re.search(r"server\s+\w+\s+127\.0\.0\.1:8081", config), "Server on port 8081 not found"
    assert re.search(r"server\s+\w+\s+127\.0\.0\.1:8082", config), "Server on port 8082 not found"
    assert re.search(r"server\s+\w+\s+127\.0\.0\.1:8083", config), "Server on port 8083 not found"

    # Count server definitions (should be exactly 3)
    server_count = len(re.findall(r"server\s+\w+\s+127\.0\.0\.1:\d+", config))
    assert server_count == 3, f"Expected 3 backend servers, found {server_count}"


def test_haproxy_config_health_checks():
    """Test that health checks are properly configured."""
    with open("/app/haproxy.cfg", "r") as f:
        config = f.read()

    # Check for health check configuration
    assert "check" in config, "Health checks not enabled on servers"

    # Check for HTTP health check method
    assert "httpchk" in config or "option httpchk" in config, "HTTP health check method not configured"

    # Check for 3-second interval (inter 3s or inter 3000)
    assert re.search(r"inter\s+3s|inter\s+3000", config), "Health check interval not set to 3 seconds"


def test_verification_json_exists():
    """Test that verification JSON file exists and is valid."""
    assert os.path.exists("/app/verification.json"), "Verification JSON file /app/verification.json not found"
    assert os.path.getsize("/app/verification.json") > 0, "Verification JSON file is empty"

    # Verify it's valid JSON
    with open("/app/verification.json", "r") as f:
        data = json.load(f)

    assert isinstance(data, dict), "Verification JSON is not a dictionary"


def test_verification_json_structure():
    """Test that verification JSON has the correct structure."""
    with open("/app/verification.json", "r") as f:
        data = json.load(f)

    # Check required top-level keys
    required_keys = [
        "haproxy_frontend_port",
        "backend_servers",
        "load_balancing_algorithm",
        "health_check_enabled",
        "stats_page_enabled",
        "stats_page_path",
        "load_distribution_test"
    ]

    for key in required_keys:
        assert key in data, f"Missing required key: {key}"


def test_verification_json_frontend_port():
    """Test that frontend port is correctly set to 80."""
    with open("/app/verification.json", "r") as f:
        data = json.load(f)

    assert data["haproxy_frontend_port"] == 80, f"Frontend port should be 80, got {data['haproxy_frontend_port']}"


def test_verification_json_backend_servers():
    """Test that backend servers are correctly configured."""
    with open("/app/verification.json", "r") as f:
        data = json.load(f)

    servers = data["backend_servers"]
    assert isinstance(servers, list), "backend_servers should be a list"
    assert len(servers) == 3, f"Expected 3 backend servers, got {len(servers)}"

    # Check each server has required fields
    ports = set()
    for server in servers:
        assert "name" in server, "Server missing 'name' field"
        assert "host" in server, "Server missing 'host' field"
        assert "port" in server, "Server missing 'port' field"
        assert "status" in server, "Server missing 'status' field"

        # Verify host is localhost
        assert server["host"] in ["127.0.0.1", "localhost"], f"Server host should be localhost, got {server['host']}"

        # Verify status is 'up'
        assert server["status"] == "up", f"Server {server['name']} status should be 'up', got {server['status']}"

        ports.add(server["port"])

    # Verify all three ports are present and unique
    expected_ports = {8081, 8082, 8083}
    assert ports == expected_ports, f"Expected ports {expected_ports}, got {ports}"


def test_verification_json_load_balancing():
    """Test that load balancing algorithm is roundrobin."""
    with open("/app/verification.json", "r") as f:
        data = json.load(f)

    assert data["load_balancing_algorithm"] == "roundrobin", \
        f"Load balancing algorithm should be 'roundrobin', got {data['load_balancing_algorithm']}"


def test_verification_json_health_checks():
    """Test that health checks are enabled."""
    with open("/app/verification.json", "r") as f:
        data = json.load(f)

    assert data["health_check_enabled"] is True, "Health checks should be enabled"


def test_verification_json_stats_page():
    """Test that stats page is enabled with correct path."""
    with open("/app/verification.json", "r") as f:
        data = json.load(f)

    assert data["stats_page_enabled"] is True, "Stats page should be enabled"
    assert data["stats_page_path"] == "/haproxy?stats", \
        f"Stats page path should be '/haproxy?stats', got {data['stats_page_path']}"


def test_verification_json_load_distribution():
    """Test that load distribution test was performed correctly."""
    with open("/app/verification.json", "r") as f:
        data = json.load(f)

    load_test = data["load_distribution_test"]

    # Check required fields
    assert "total_requests" in load_test, "Missing 'total_requests' in load_distribution_test"
    assert "server1_hits" in load_test, "Missing 'server1_hits' in load_distribution_test"
    assert "server2_hits" in load_test, "Missing 'server2_hits' in load_distribution_test"
    assert "server3_hits" in load_test, "Missing 'server3_hits' in load_distribution_test"

    # Verify total requests is 9
    assert load_test["total_requests"] == 9, \
        f"Total requests should be 9, got {load_test['total_requests']}"

    # Verify hits are integers
    assert isinstance(load_test["server1_hits"], int), "server1_hits should be an integer"
    assert isinstance(load_test["server2_hits"], int), "server2_hits should be an integer"
    assert isinstance(load_test["server3_hits"], int), "server3_hits should be an integer"

    # Verify hits are non-negative
    assert load_test["server1_hits"] >= 0, "server1_hits should be non-negative"
    assert load_test["server2_hits"] >= 0, "server2_hits should be non-negative"
    assert load_test["server3_hits"] >= 0, "server3_hits should be non-negative"

    # Verify sum of hits equals total requests
    total_hits = load_test["server1_hits"] + load_test["server2_hits"] + load_test["server3_hits"]
    assert total_hits == 9, \
        f"Sum of server hits ({total_hits}) should equal total_requests (9)"

    # Verify round-robin distribution (each server should get exactly 3 hits)
    assert load_test["server1_hits"] == 3, \
        f"With round-robin, server1 should get 3 hits, got {load_test['server1_hits']}"
    assert load_test["server2_hits"] == 3, \
        f"With round-robin, server2 should get 3 hits, got {load_test['server2_hits']}"
    assert load_test["server3_hits"] == 3, \
        f"With round-robin, server3 should get 3 hits, got {load_test['server3_hits']}"


def test_no_hardcoded_dummy_data():
    """Test that the verification JSON contains actual test results, not dummy data."""
    with open("/app/verification.json", "r") as f:
        content = f.read()
        data = json.loads(content)

    # Ensure the file doesn't contain placeholder text
    assert "TODO" not in content.upper(), "Verification JSON contains TODO placeholder"
    assert "PLACEHOLDER" not in content.upper(), "Verification JSON contains PLACEHOLDER text"
    assert "DUMMY" not in content.upper(), "Verification JSON contains DUMMY text"

    # Verify that load distribution test actually ran (not all zeros)
    load_test = data["load_distribution_test"]
    total_hits = load_test["server1_hits"] + load_test["server2_hits"] + load_test["server3_hits"]
    assert total_hits > 0, "Load distribution test appears to not have run (all hits are 0)"
