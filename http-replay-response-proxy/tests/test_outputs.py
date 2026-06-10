"""
Tests for HTTP Request Replay & Response Modification task.

Validates:
- Required script files exist and have meaningful content
- Output JSON files exist, are valid JSON, and contain correct data
- The proxy correctly modifies the response (core functionality)
- The server script defines the right endpoints
- The proxy script uses sed for substitution
"""

import json
import os

# ---------------------------------------------------------------------------
# Paths — all under /app as specified in instruction.md
# ---------------------------------------------------------------------------
APP_DIR = "/app"

SERVER_SCRIPT = os.path.join(APP_DIR, "server.py")
PROXY_SCRIPT = os.path.join(APP_DIR, "proxy.sh")
TEST_SCRIPT = os.path.join(APP_DIR, "test_replay.sh")

OUTPUT_DIRECT = os.path.join(APP_DIR, "output_direct.json")
OUTPUT_PROXIED = os.path.join(APP_DIR, "output_proxied.json")
OUTPUT_HEALTH = os.path.join(APP_DIR, "output_health.json")


# ===========================================================================
# Helper utilities
# ===========================================================================

def _read_text(path):
    """Read a file and return stripped text, or None if missing/empty."""
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read().strip()


def _load_json(path):
    """Load and return parsed JSON from a file. Returns None on failure."""
    text = _read_text(path)
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


# ===========================================================================
# 1. Script file existence and non-trivial content
# ===========================================================================

class TestScriptFilesExist:
    """Verify the three required scripts exist and are not empty stubs."""

    def test_server_script_exists(self):
        assert os.path.isfile(SERVER_SCRIPT), f"{SERVER_SCRIPT} does not exist"

    def test_proxy_script_exists(self):
        assert os.path.isfile(PROXY_SCRIPT), f"{PROXY_SCRIPT} does not exist"

    def test_test_script_exists(self):
        assert os.path.isfile(TEST_SCRIPT), f"{TEST_SCRIPT} does not exist"

    def test_server_script_not_trivial(self):
        content = _read_text(SERVER_SCRIPT)
        assert content is not None and len(content) > 50, \
            "server.py is missing or trivially small"

    def test_proxy_script_not_trivial(self):
        content = _read_text(PROXY_SCRIPT)
        assert content is not None and len(content) > 30, \
            "proxy.sh is missing or trivially small"

    def test_test_script_not_trivial(self):
        content = _read_text(TEST_SCRIPT)
        assert content is not None and len(content) > 30, \
            "test_replay.sh is missing or trivially small"


# ===========================================================================
# 2. Server script content checks
# ===========================================================================

class TestServerScript:
    """Verify server.py looks like a real HTTP server, not a hardcoded stub."""

    def test_server_is_python(self):
        content = _read_text(SERVER_SCRIPT)
        assert content is not None
        # Must import or use http.server or equivalent
        has_http = ("http.server" in content or "HTTPServer" in content
                    or "flask" in content.lower() or "fastapi" in content.lower()
                    or "BaseHTTPRequestHandler" in content
                    or "aiohttp" in content.lower()
                    or "bottle" in content.lower())
        assert has_http, "server.py does not appear to implement an HTTP server"

    def test_server_uses_port_8080(self):
        content = _read_text(SERVER_SCRIPT)
        assert content is not None
        assert "8080" in content, "server.py does not reference port 8080"

    def test_server_defines_api_data_route(self):
        content = _read_text(SERVER_SCRIPT)
        assert content is not None
        assert "/api/data" in content, "server.py does not define /api/data endpoint"

    def test_server_defines_api_health_route(self):
        content = _read_text(SERVER_SCRIPT)
        assert content is not None
        assert "/api/health" in content, "server.py does not define /api/health endpoint"

    def test_server_returns_original_response(self):
        content = _read_text(SERVER_SCRIPT)
        assert content is not None
        assert "original response" in content, \
            "server.py does not contain the expected 'original response' string"

    def test_server_returns_count_42(self):
        content = _read_text(SERVER_SCRIPT)
        assert content is not None
        assert "42" in content, \
            "server.py does not contain the expected count value 42"


# ===========================================================================
# 3. Proxy script content checks
# ===========================================================================

class TestProxyScript:
    """Verify proxy.sh is a real response-modifying proxy using sed."""

    def test_proxy_uses_sed(self):
        content = _read_text(PROXY_SCRIPT)
        assert content is not None
        assert "sed" in content, "proxy.sh does not use sed for response modification"

    def test_proxy_uses_port_8081(self):
        content = _read_text(PROXY_SCRIPT)
        assert content is not None
        assert "8081" in content, "proxy.sh does not reference port 8081"

    def test_proxy_forwards_to_8080(self):
        content = _read_text(PROXY_SCRIPT)
        assert content is not None
        assert "8080" in content, "proxy.sh does not reference backend port 8080"

    def test_proxy_substitutes_modified_response(self):
        content = _read_text(PROXY_SCRIPT)
        assert content is not None
        assert "modified response" in content or "modified" in content, \
            "proxy.sh does not contain the 'modified response' substitution target"

    def test_proxy_substitutes_count_100(self):
        content = _read_text(PROXY_SCRIPT)
        assert content is not None
        assert "100" in content, \
            "proxy.sh does not contain the substituted count value 100"


# ===========================================================================
# 4. Test/replay script content checks
# ===========================================================================

class TestReplayScript:
    """Verify test_replay.sh orchestrates server, proxy, and curl requests."""

    def test_replay_starts_server(self):
        content = _read_text(TEST_SCRIPT)
        assert content is not None
        assert "server.py" in content, \
            "test_replay.sh does not reference server.py"

    def test_replay_starts_proxy(self):
        content = _read_text(TEST_SCRIPT)
        assert content is not None
        assert "proxy.sh" in content, \
            "test_replay.sh does not reference proxy.sh"

    def test_replay_uses_curl_or_wget(self):
        content = _read_text(TEST_SCRIPT)
        assert content is not None
        assert "curl" in content or "wget" in content, \
            "test_replay.sh does not use curl or wget to send requests"

    def test_replay_writes_output_files(self):
        content = _read_text(TEST_SCRIPT)
        assert content is not None
        assert "output_direct" in content, \
            "test_replay.sh does not reference output_direct"
        assert "output_proxied" in content, \
            "test_replay.sh does not reference output_proxied"
        assert "output_health" in content, \
            "test_replay.sh does not reference output_health"


# ===========================================================================
# 5. Output file existence and valid JSON
# ===========================================================================

class TestOutputFilesExist:
    """All three output JSON files must exist and be parseable."""

    def test_output_direct_exists(self):
        assert os.path.isfile(OUTPUT_DIRECT), \
            f"{OUTPUT_DIRECT} does not exist"

    def test_output_proxied_exists(self):
        assert os.path.isfile(OUTPUT_PROXIED), \
            f"{OUTPUT_PROXIED} does not exist"

    def test_output_health_exists(self):
        assert os.path.isfile(OUTPUT_HEALTH), \
            f"{OUTPUT_HEALTH} does not exist"

    def test_output_direct_is_valid_json(self):
        data = _load_json(OUTPUT_DIRECT)
        assert data is not None, \
            f"{OUTPUT_DIRECT} is not valid JSON"

    def test_output_proxied_is_valid_json(self):
        data = _load_json(OUTPUT_PROXIED)
        assert data is not None, \
            f"{OUTPUT_PROXIED} is not valid JSON"

    def test_output_health_is_valid_json(self):
        data = _load_json(OUTPUT_HEALTH)
        assert data is not None, \
            f"{OUTPUT_HEALTH} is not valid JSON"

    def test_output_direct_not_empty(self):
        text = _read_text(OUTPUT_DIRECT)
        assert text is not None and len(text) > 2, \
            f"{OUTPUT_DIRECT} is empty or trivially small"

    def test_output_proxied_not_empty(self):
        text = _read_text(OUTPUT_PROXIED)
        assert text is not None and len(text) > 2, \
            f"{OUTPUT_PROXIED} is empty or trivially small"

    def test_output_health_not_empty(self):
        text = _read_text(OUTPUT_HEALTH)
        assert text is not None and len(text) > 2, \
            f"{OUTPUT_HEALTH} is empty or trivially small"


# ===========================================================================
# 6. Direct response content — original, unmodified server output
# ===========================================================================

class TestOutputDirect:
    """output_direct.json must match the original server response exactly."""

    def test_status_field(self):
        data = _load_json(OUTPUT_DIRECT)
        assert data is not None, "Cannot parse output_direct.json"
        assert data.get("status") == "success", \
            f"Expected status='success', got {data.get('status')!r}"

    def test_message_field_original(self):
        data = _load_json(OUTPUT_DIRECT)
        assert data is not None, "Cannot parse output_direct.json"
        assert data.get("message") == "original response", \
            f"Expected message='original response', got {data.get('message')!r}"

    def test_count_field_42(self):
        data = _load_json(OUTPUT_DIRECT)
        assert data is not None, "Cannot parse output_direct.json"
        assert data.get("count") == 42, \
            f"Expected count=42, got {data.get('count')!r}"

    def test_has_exactly_three_keys(self):
        data = _load_json(OUTPUT_DIRECT)
        assert data is not None, "Cannot parse output_direct.json"
        assert set(data.keys()) == {"status", "message", "count"}, \
            f"Unexpected keys: {set(data.keys())}"


# ===========================================================================
# 7. Proxied response content — the CORE test: sed modifications applied
# ===========================================================================

class TestOutputProxied:
    """output_proxied.json must reflect the two sed substitutions."""

    def test_status_field(self):
        data = _load_json(OUTPUT_PROXIED)
        assert data is not None, "Cannot parse output_proxied.json"
        assert data.get("status") == "success", \
            f"Expected status='success', got {data.get('status')!r}"

    def test_message_field_modified(self):
        """Core check: 'original response' must have been replaced with 'modified response'."""
        data = _load_json(OUTPUT_PROXIED)
        assert data is not None, "Cannot parse output_proxied.json"
        assert data.get("message") == "modified response", \
            f"Expected message='modified response', got {data.get('message')!r}"

    def test_message_not_original(self):
        """Ensure the proxy actually changed the message — not still 'original response'."""
        data = _load_json(OUTPUT_PROXIED)
        assert data is not None, "Cannot parse output_proxied.json"
        assert data.get("message") != "original response", \
            "Proxied response still contains 'original response' — proxy did not modify it"

    def test_count_field_100(self):
        """Core check: count must have been changed from 42 to 100."""
        data = _load_json(OUTPUT_PROXIED)
        assert data is not None, "Cannot parse output_proxied.json"
        assert data.get("count") == 100, \
            f"Expected count=100, got {data.get('count')!r}"

    def test_count_not_42(self):
        """Ensure the proxy actually changed the count — not still 42."""
        data = _load_json(OUTPUT_PROXIED)
        assert data is not None, "Cannot parse output_proxied.json"
        assert data.get("count") != 42, \
            "Proxied response still has count=42 — proxy did not modify it"

    def test_has_exactly_three_keys(self):
        data = _load_json(OUTPUT_PROXIED)
        assert data is not None, "Cannot parse output_proxied.json"
        assert set(data.keys()) == {"status", "message", "count"}, \
            f"Unexpected keys: {set(data.keys())}"


# ===========================================================================
# 8. Health check output — passed through proxy, but no substitution needed
# ===========================================================================

class TestOutputHealth:
    """output_health.json must contain the health check response."""

    def test_status_field(self):
        data = _load_json(OUTPUT_HEALTH)
        assert data is not None, "Cannot parse output_health.json"
        assert data.get("status") == "healthy", \
            f"Expected status='healthy', got {data.get('status')!r}"

    def test_has_exactly_one_key(self):
        data = _load_json(OUTPUT_HEALTH)
        assert data is not None, "Cannot parse output_health.json"
        assert set(data.keys()) == {"status"}, \
            f"Unexpected keys: {set(data.keys())}"


# ===========================================================================
# 9. Cross-file consistency: direct vs proxied differ in the right way
# ===========================================================================

class TestProxyModificationConsistency:
    """
    Compare direct and proxied outputs to confirm the proxy changed
    exactly the right fields and nothing else.
    """

    def test_direct_and_proxied_differ(self):
        """The two outputs must NOT be identical — the proxy must have changed something."""
        direct = _load_json(OUTPUT_DIRECT)
        proxied = _load_json(OUTPUT_PROXIED)
        assert direct is not None and proxied is not None, \
            "Cannot load one or both output files"
        assert direct != proxied, \
            "output_direct.json and output_proxied.json are identical — proxy had no effect"

    def test_status_unchanged_by_proxy(self):
        """The 'status' field should be the same in both (proxy only changes message and count)."""
        direct = _load_json(OUTPUT_DIRECT)
        proxied = _load_json(OUTPUT_PROXIED)
        assert direct is not None and proxied is not None
        assert direct.get("status") == proxied.get("status"), \
            "Proxy unexpectedly changed the 'status' field"

    def test_message_changed_by_proxy(self):
        direct = _load_json(OUTPUT_DIRECT)
        proxied = _load_json(OUTPUT_PROXIED)
        assert direct is not None and proxied is not None
        assert direct.get("message") != proxied.get("message"), \
            "Proxy did not change the 'message' field"

    def test_count_changed_by_proxy(self):
        direct = _load_json(OUTPUT_DIRECT)
        proxied = _load_json(OUTPUT_PROXIED)
        assert direct is not None and proxied is not None
        assert direct.get("count") != proxied.get("count"), \
            "Proxy did not change the 'count' field"


# ===========================================================================
# 10. Output files must be clean JSON (no HTTP headers mixed in)
# ===========================================================================

class TestOutputCleanliness:
    """Output files must contain only JSON body — no HTTP headers or junk."""

    def test_direct_no_http_headers(self):
        text = _read_text(OUTPUT_DIRECT)
        assert text is not None
        assert not text.startswith("HTTP/"), \
            "output_direct.json starts with HTTP headers"
        assert "Content-Type" not in text, \
            "output_direct.json contains HTTP header 'Content-Type'"

    def test_proxied_no_http_headers(self):
        text = _read_text(OUTPUT_PROXIED)
        assert text is not None
        assert not text.startswith("HTTP/"), \
            "output_proxied.json starts with HTTP headers"
        assert "Content-Type" not in text, \
            "output_proxied.json contains HTTP header 'Content-Type'"

    def test_health_no_http_headers(self):
        text = _read_text(OUTPUT_HEALTH)
        assert text is not None
        assert not text.startswith("HTTP/"), \
            "output_health.json starts with HTTP headers"
        assert "Content-Type" not in text, \
            "output_health.json contains HTTP header 'Content-Type'"

    def test_direct_starts_with_brace(self):
        text = _read_text(OUTPUT_DIRECT)
        assert text is not None
        assert text.startswith("{"), \
            f"output_direct.json does not start with '{{': starts with {text[:20]!r}"

    def test_proxied_starts_with_brace(self):
        text = _read_text(OUTPUT_PROXIED)
        assert text is not None
        assert text.startswith("{"), \
            f"output_proxied.json does not start with '{{': starts with {text[:20]!r}"

    def test_health_starts_with_brace(self):
        text = _read_text(OUTPUT_HEALTH)
        assert text is not None
        assert text.startswith("{"), \
            f"output_health.json does not start with '{{': starts with {text[:20]!r}"
