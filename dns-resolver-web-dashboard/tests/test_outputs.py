"""
Tests for DNS Resolver Web Dashboard task.
Validates: file existence, module imports, function signatures,
stats computation, query logging, CLI client, and web dashboard endpoints.
"""

import os
import sys
import json
import subprocess
import time
import signal
import math

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
APP_DIR = "/app"
DNS_RESOLVER = os.path.join(APP_DIR, "dns_resolver.py")
QUERY_LOGGER = os.path.join(APP_DIR, "query_logger.py")
STATS_COLLECTOR = os.path.join(APP_DIR, "stats_collector.py")
CLI_CLIENT = os.path.join(APP_DIR, "cli_client.py")
WEB_DASHBOARD = os.path.join(APP_DIR, "web_dashboard.py")
CONFIG_FILE = os.path.join(APP_DIR, "config.json")
LOG_FILE = os.path.join(APP_DIR, "dns_log.json")
EMPTY_LOG = os.path.join(APP_DIR, "test_data", "empty_log.json")
SMALL_LOG = os.path.join(APP_DIR, "test_data", "small_log.json")

# Ensure /app is importable
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)


# ===================================================================
# 1. FILE EXISTENCE TESTS
# ===================================================================

class TestFileExistence:
    """All required files must exist."""

    def test_dns_resolver_exists(self):
        assert os.path.isfile(DNS_RESOLVER), f"{DNS_RESOLVER} not found"

    def test_query_logger_exists(self):
        assert os.path.isfile(QUERY_LOGGER), f"{QUERY_LOGGER} not found"

    def test_stats_collector_exists(self):
        assert os.path.isfile(STATS_COLLECTOR), f"{STATS_COLLECTOR} not found"

    def test_cli_client_exists(self):
        assert os.path.isfile(CLI_CLIENT), f"{CLI_CLIENT} not found"

    def test_web_dashboard_exists(self):
        assert os.path.isfile(WEB_DASHBOARD), f"{WEB_DASHBOARD} not found"

    def test_config_json_exists(self):
        assert os.path.isfile(CONFIG_FILE), f"{CONFIG_FILE} not found"


# ===================================================================
# 2. CONFIG FILE TESTS
# ===================================================================

class TestConfig:
    """config.json must be valid JSON with required keys."""

    def test_config_is_valid_json(self):
        with open(CONFIG_FILE, "r") as f:
            cfg = json.load(f)
        assert isinstance(cfg, dict)

    def test_config_has_required_keys(self):
        with open(CONFIG_FILE, "r") as f:
            cfg = json.load(f)
        for key in ("upstream_dns", "dns_port", "web_port", "log_file", "log_level"):
            assert key in cfg, f"config.json missing key: {key}"

    def test_config_web_port_is_int(self):
        with open(CONFIG_FILE, "r") as f:
            cfg = json.load(f)
        assert isinstance(cfg["web_port"], int)


# ===================================================================
# 3. DNS RESOLVER MODULE TESTS
# ===================================================================

class TestDnsResolverModule:
    """dns_resolver.py must be importable and expose resolve()."""

    def test_importable(self):
        import importlib
        mod = importlib.import_module("dns_resolver")
        assert mod is not None

    def test_resolve_function_exists(self):
        from dns_resolver import resolve
        assert callable(resolve)

    def test_resolve_returns_dict(self):
        """resolve() must return a dict regardless of network availability."""
        from dns_resolver import resolve
        result = resolve("example.com", "A")
        assert isinstance(result, dict), "resolve() must return a dict"

    def test_resolve_result_has_required_keys(self):
        from dns_resolver import resolve
        result = resolve("example.com", "A")
        for key in ("domain", "query_type", "answers", "response_time_ms", "status", "timestamp"):
            assert key in result, f"resolve() result missing key: {key}"

    def test_resolve_domain_field(self):
        from dns_resolver import resolve
        result = resolve("example.com", "A")
        assert result["domain"] == "example.com"

    def test_resolve_query_type_field(self):
        from dns_resolver import resolve
        result = resolve("example.com", "AAAA")
        assert result["query_type"] == "AAAA"

    def test_resolve_answers_is_list(self):
        from dns_resolver import resolve
        result = resolve("example.com", "A")
        assert isinstance(result["answers"], list)

    def test_resolve_status_is_string(self):
        from dns_resolver import resolve
        result = resolve("example.com", "A")
        assert result["status"] in ("success", "error")

    def test_resolve_response_time_is_number(self):
        from dns_resolver import resolve
        result = resolve("example.com", "A")
        assert isinstance(result["response_time_ms"], (int, float))

    def test_resolve_error_has_error_key(self):
        """On error status, an 'error' key with a string description must be present."""
        from dns_resolver import resolve
        result = resolve("nonexistent.invalid", "A")
        if result["status"] == "error":
            assert "error" in result
            assert isinstance(result["error"], str)
            assert len(result["error"]) > 0

    def test_resolve_error_has_empty_answers(self):
        """On error, answers must be an empty list."""
        from dns_resolver import resolve
        result = resolve("nonexistent.invalid", "A")
        if result["status"] == "error":
            assert result["answers"] == []



# ===================================================================
# 4. QUERY LOGGER MODULE TESTS
# ===================================================================

class TestQueryLoggerModule:
    """query_logger.py must be importable and expose log_query()."""

    def test_importable(self):
        import importlib
        mod = importlib.import_module("query_logger")
        assert mod is not None

    def test_log_query_function_exists(self):
        from query_logger import log_query
        assert callable(log_query)

    def test_log_query_appends_jsonl(self, tmp_path):
        """log_query must append a JSON line with an 'id' field."""
        # Temporarily override config to use a temp log file
        temp_log = str(tmp_path / "test_log.json")
        temp_config = str(tmp_path / "config.json")
        cfg = {
            "upstream_dns": "8.8.8.8",
            "dns_port": 53,
            "web_port": 5353,
            "log_file": temp_log,
            "log_level": "INFO"
        }
        with open(temp_config, "w") as f:
            json.dump(cfg, f)

        # We need to patch the config path; run as subprocess for isolation
        script = f"""
import sys, json, os
sys.path.insert(0, "/app")

# Patch config path
import query_logger
original_load = query_logger._load_config
def patched_load():
    return {{"log_file": "{temp_log}"}}
query_logger._load_config = patched_load

result = {{
    "domain": "test.com",
    "query_type": "A",
    "answers": ["1.2.3.4"],
    "response_time_ms": 10.0,
    "status": "success",
    "timestamp": "2025-01-15T10:30:00Z"
}}
query_logger.log_query(result)
query_logger.log_query(result)
"""
        proc = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True, text=True, timeout=10
        )
        assert proc.returncode == 0, f"log_query script failed: {proc.stderr}"
        assert os.path.isfile(temp_log), "Log file was not created"

        with open(temp_log, "r") as f:
            lines = [l.strip() for l in f if l.strip()]
        assert len(lines) == 2, f"Expected 2 log lines, got {len(lines)}"

        entry1 = json.loads(lines[0])
        entry2 = json.loads(lines[1])
        assert "id" in entry1, "Log entry missing 'id' field"
        assert "id" in entry2, "Log entry missing 'id' field"
        assert entry1["id"] < entry2["id"], "IDs must be auto-incrementing"
        assert entry1["domain"] == "test.com"
        assert "query_type" in entry1
        assert "answers" in entry1
        assert "status" in entry1


# ===================================================================
# 5. STATS COLLECTOR MODULE TESTS
# ===================================================================

class TestStatsCollectorModule:
    """stats_collector.py must be importable and expose compute_stats()."""

    def test_importable(self):
        import importlib
        mod = importlib.import_module("stats_collector")
        assert mod is not None

    def test_compute_stats_function_exists(self):
        from stats_collector import compute_stats
        assert callable(compute_stats)

    def test_stats_returns_dict(self):
        from stats_collector import compute_stats
        result = compute_stats(LOG_FILE)
        assert isinstance(result, dict)

    def test_stats_has_required_keys(self):
        from stats_collector import compute_stats
        result = compute_stats(LOG_FILE)
        for key in ("total_queries", "successful_queries", "failed_queries",
                     "query_type_counts", "avg_response_time_ms",
                     "top_domains", "queries_per_minute"):
            assert key in result, f"compute_stats() missing key: {key}"

    def test_stats_main_log_total_queries(self):
        """The pre-populated dns_log.json has 10 entries."""
        from stats_collector import compute_stats
        result = compute_stats(LOG_FILE)
        assert result["total_queries"] == 10

    def test_stats_main_log_successful(self):
        """8 of 10 entries in dns_log.json have status=success."""
        from stats_collector import compute_stats
        result = compute_stats(LOG_FILE)
        assert result["successful_queries"] == 8

    def test_stats_main_log_failed(self):
        """2 of 10 entries in dns_log.json have status=error."""
        from stats_collector import compute_stats
        result = compute_stats(LOG_FILE)
        assert result["failed_queries"] == 2

    def test_stats_main_log_query_type_counts(self):
        """Verify query type distribution from dns_log.json."""
        from stats_collector import compute_stats
        result = compute_stats(LOG_FILE)
        qtc = result["query_type_counts"]
        assert isinstance(qtc, dict)
        # dns_log.json: A=7, AAAA=1, MX=1, CNAME=1 (success+error combined)
        # ids 1,2,6,7,10 are A (success); ids 4,9 are A (error)
        # id 3 is AAAA; id 5 is MX; id 8 is CNAME
        assert qtc.get("A", 0) == 7, f"Expected A=7, got {qtc.get('A')}"
        assert qtc.get("AAAA", 0) == 1
        assert qtc.get("MX", 0) == 1
        assert qtc.get("CNAME", 0) == 1

    def test_stats_main_log_avg_response_time(self):
        """avg_response_time_ms should be average of successful queries only."""
        from stats_collector import compute_stats
        result = compute_stats(LOG_FILE)
        # Successful entries: 12.5, 8.3, 15.1, 20.7, 11.2, 9.8, 14.0, 7.9
        # Sum = 99.5, count = 8, avg = 12.4375 -> rounded to 12.4
        expected_avg = 12.4
        assert math.isclose(result["avg_response_time_ms"], expected_avg, abs_tol=0.2), \
            f"Expected avg ~{expected_avg}, got {result['avg_response_time_ms']}"

    def test_stats_main_log_top_domains_is_list(self):
        from stats_collector import compute_stats
        result = compute_stats(LOG_FILE)
        assert isinstance(result["top_domains"], list)

    def test_stats_main_log_top_domains_sorted(self):
        """top_domains must be sorted by count descending."""
        from stats_collector import compute_stats
        result = compute_stats(LOG_FILE)
        td = result["top_domains"]
        if len(td) >= 2:
            for i in range(len(td) - 1):
                assert td[i]["count"] >= td[i + 1]["count"], \
                    "top_domains not sorted descending by count"

    def test_stats_main_log_top_domains_structure(self):
        """Each entry in top_domains must have 'domain' and 'count'."""
        from stats_collector import compute_stats
        result = compute_stats(LOG_FILE)
        for entry in result["top_domains"]:
            assert "domain" in entry
            assert "count" in entry

    def test_stats_main_log_top_domain_is_example(self):
        """example.com appears 4 times in dns_log.json — should be #1."""
        from stats_collector import compute_stats
        result = compute_stats(LOG_FILE)
        td = result["top_domains"]
        assert len(td) > 0, "top_domains is empty"
        assert td[0]["domain"] == "example.com"
        assert td[0]["count"] == 4

    def test_stats_main_log_top_domains_max_10(self):
        from stats_collector import compute_stats
        result = compute_stats(LOG_FILE)
        assert len(result["top_domains"]) <= 10

    def test_stats_empty_log(self):
        """Empty log file must return zeroed stats."""
        from stats_collector import compute_stats
        result = compute_stats(EMPTY_LOG)
        assert result["total_queries"] == 0
        assert result["successful_queries"] == 0
        assert result["failed_queries"] == 0
        assert result["query_type_counts"] == {}
        assert result["avg_response_time_ms"] == 0.0
        assert result["top_domains"] == []

    def test_stats_missing_log(self):
        """Non-existent log file must return zeroed stats."""
        from stats_collector import compute_stats
        result = compute_stats("/tmp/nonexistent_log_file_xyz.json")
        assert result["total_queries"] == 0

    def test_stats_small_log(self):
        """Verify stats against the 3-entry small_log.json."""
        from stats_collector import compute_stats
        result = compute_stats(SMALL_LOG)
        assert result["total_queries"] == 3
        assert result["successful_queries"] == 2
        assert result["failed_queries"] == 1
        # avg of successful: (10.0 + 20.0) / 2 = 15.0
        assert math.isclose(result["avg_response_time_ms"], 15.0, abs_tol=0.2)


# ===================================================================
# 6. CLI CLIENT TESTS
# ===================================================================

class TestCliClient:
    """cli_client.py must be runnable and produce JSON output."""

    def test_cli_runs_without_crash(self):
        """CLI must not crash when given a domain (network may fail, that's ok)."""
        proc = subprocess.run(
            [sys.executable, CLI_CLIENT, "example.com"],
            capture_output=True, text=True, timeout=15
        )
        # Exit 0 (success) or 1 (DNS error) are both acceptable
        assert proc.returncode in (0, 1), \
            f"CLI exited with unexpected code {proc.returncode}: {proc.stderr}"

    def test_cli_outputs_json(self):
        """CLI stdout must be valid JSON."""
        proc = subprocess.run(
            [sys.executable, CLI_CLIENT, "example.com"],
            capture_output=True, text=True, timeout=15
        )
        stdout = proc.stdout.strip()
        assert len(stdout) > 0, "CLI produced no output"
        data = json.loads(stdout)  # will raise if not valid JSON
        assert isinstance(data, dict)

    def test_cli_output_has_required_keys(self):
        """CLI JSON output must contain resolver result keys."""
        proc = subprocess.run(
            [sys.executable, CLI_CLIENT, "example.com", "A"],
            capture_output=True, text=True, timeout=15
        )
        data = json.loads(proc.stdout.strip())
        for key in ("domain", "query_type", "answers", "status"):
            assert key in data, f"CLI output missing key: {key}"

    def test_cli_domain_in_output(self):
        """The domain in the output must match the requested domain."""
        proc = subprocess.run(
            [sys.executable, CLI_CLIENT, "example.com", "A"],
            capture_output=True, text=True, timeout=15
        )
        data = json.loads(proc.stdout.strip())
        assert data["domain"] == "example.com"

    def test_cli_query_type_default_A(self):
        """When query_type is omitted, it should default to A."""
        proc = subprocess.run(
            [sys.executable, CLI_CLIENT, "example.com"],
            capture_output=True, text=True, timeout=15
        )
        data = json.loads(proc.stdout.strip())
        assert data["query_type"] == "A"

    def test_cli_no_args_exits_nonzero(self):
        """CLI with no arguments should exit with non-zero or print usage."""
        proc = subprocess.run(
            [sys.executable, CLI_CLIENT],
            capture_output=True, text=True, timeout=10
        )
        # Either exits non-zero or prints an error/usage message
        assert proc.returncode != 0 or "error" in proc.stdout.lower() or "usage" in proc.stdout.lower()


# ===================================================================
# 7. WEB DASHBOARD TESTS
# ===================================================================

def _start_dashboard():
    """Start the web dashboard and return (process, port)."""
    with open(CONFIG_FILE, "r") as f:
        cfg = json.load(f)
    port = cfg.get("web_port", 5353)

    # Kill any existing process on the port
    subprocess.run(
        ["bash", "-c", f"fuser -k {port}/tcp 2>/dev/null || true"],
        capture_output=True, timeout=5
    )
    time.sleep(0.5)

    proc = subprocess.Popen(
        [sys.executable, WEB_DASHBOARD],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        cwd=APP_DIR
    )
    # Wait for server to be ready
    for _ in range(20):
        time.sleep(0.5)
        try:
            import urllib.request
            urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=2)
            return proc, port
        except Exception:
            if proc.poll() is not None:
                break
            continue

    return proc, port


def _stop_dashboard(proc):
    """Stop the web dashboard process."""
    if proc and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


class TestWebDashboard:
    """Web dashboard HTTP endpoint tests."""

    @classmethod
    def setup_class(cls):
        cls.proc, cls.port = _start_dashboard()
        cls.base_url = f"http://127.0.0.1:{cls.port}"

    @classmethod
    def teardown_class(cls):
        _stop_dashboard(cls.proc)

    def _get(self, path):
        import urllib.request
        url = f"{self.base_url}{path}"
        req = urllib.request.Request(url)
        try:
            resp = urllib.request.urlopen(req, timeout=10)
            body = resp.read().decode("utf-8")
            return resp.status, resp.headers.get("Content-Type", ""), body
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8") if e.fp else ""
            return e.code, e.headers.get("Content-Type", ""), body

    def test_dashboard_running(self):
        """The web dashboard process must be alive."""
        assert self.proc is not None, "Dashboard process is None"
        assert self.proc.poll() is None, "Dashboard process exited prematurely"

    def test_root_returns_200(self):
        """GET / must return HTTP 200."""
        status, ctype, body = self._get("/")
        assert status == 200, f"GET / returned {status}"

    def test_root_returns_html(self):
        """GET / must return HTML content."""
        status, ctype, body = self._get("/")
        assert "html" in ctype.lower() or "<html" in body.lower() or "<!doctype" in body.lower()

    def test_api_stats_returns_200(self):
        """GET /api/stats must return HTTP 200."""
        status, ctype, body = self._get("/api/stats")
        assert status == 200, f"GET /api/stats returned {status}"

    def test_api_stats_returns_json(self):
        """GET /api/stats must return valid JSON."""
        status, ctype, body = self._get("/api/stats")
        assert "json" in ctype.lower(), f"Content-Type is {ctype}, expected JSON"
        data = json.loads(body)
        assert isinstance(data, dict)

    def test_api_stats_has_required_keys(self):
        """GET /api/stats JSON must contain all stats keys."""
        status, ctype, body = self._get("/api/stats")
        data = json.loads(body)
        for key in ("total_queries", "successful_queries", "failed_queries",
                     "query_type_counts", "avg_response_time_ms",
                     "top_domains", "queries_per_minute"):
            assert key in data, f"/api/stats missing key: {key}"

    def test_api_stats_total_queries_positive(self):
        """Stats should reflect the pre-populated log (at least 10 entries)."""
        status, ctype, body = self._get("/api/stats")
        data = json.loads(body)
        assert data["total_queries"] >= 10

    def test_api_logs_returns_200(self):
        """GET /api/logs must return HTTP 200."""
        status, ctype, body = self._get("/api/logs")
        assert status == 200

    def test_api_logs_returns_json_array(self):
        """GET /api/logs must return a JSON array."""
        status, ctype, body = self._get("/api/logs")
        data = json.loads(body)
        assert isinstance(data, list), "Expected JSON array from /api/logs"

    def test_api_logs_entries_have_id(self):
        """Each log entry must have an 'id' field."""
        status, ctype, body = self._get("/api/logs")
        data = json.loads(body)
        if len(data) > 0:
            for entry in data[:5]:  # check first 5
                assert "id" in entry, "Log entry missing 'id'"

    def test_api_logs_limit(self):
        """GET /api/logs?limit=2 must return at most 2 entries."""
        status, ctype, body = self._get("/api/logs?limit=2")
        data = json.loads(body)
        assert len(data) <= 2, f"Expected <=2 entries, got {len(data)}"

    def test_api_resolve_missing_domain_returns_400(self):
        """GET /api/resolve without domain must return HTTP 400."""
        status, ctype, body = self._get("/api/resolve")
        assert status == 400, f"Expected 400, got {status}"

    def test_api_resolve_missing_domain_returns_error_json(self):
        """GET /api/resolve without domain must return JSON with 'error' key."""
        status, ctype, body = self._get("/api/resolve")
        data = json.loads(body)
        assert "error" in data, "400 response missing 'error' key"

    def test_api_resolve_with_domain(self):
        """GET /api/resolve?domain=example.com must return JSON with resolver keys."""
        status, ctype, body = self._get("/api/resolve?domain=example.com&type=A")
        assert status == 200, f"Expected 200, got {status}"
        data = json.loads(body)
        assert isinstance(data, dict)
        assert data.get("domain") == "example.com"
        assert "status" in data
        assert "answers" in data
        assert isinstance(data["answers"], list)

    def test_api_resolve_default_type_A(self):
        """GET /api/resolve?domain=example.com (no type) should default to A."""
        status, ctype, body = self._get("/api/resolve?domain=example.com")
        data = json.loads(body)
        assert data.get("query_type") == "A"


# ===================================================================
# 8. DNS LOG FILE FORMAT TESTS
# ===================================================================

class TestDnsLogFormat:
    """Validate the dns_log.json file format."""

    def test_log_file_exists(self):
        assert os.path.isfile(LOG_FILE), f"{LOG_FILE} not found"

    def test_log_file_is_jsonl(self):
        """Each non-empty line must be valid JSON."""
        with open(LOG_FILE, "r") as f:
            lines = [l.strip() for l in f if l.strip()]
        assert len(lines) > 0, "Log file is empty"
        for i, line in enumerate(lines):
            try:
                json.loads(line)
            except json.JSONDecodeError:
                assert False, f"Line {i+1} is not valid JSON: {line[:80]}"

    def test_log_entries_have_required_keys(self):
        """Each log entry must have id, domain, query_type, answers, status."""
        with open(LOG_FILE, "r") as f:
            lines = [l.strip() for l in f if l.strip()]
        for i, line in enumerate(lines):
            entry = json.loads(line)
            for key in ("id", "domain", "query_type", "answers", "status"):
                assert key in entry, f"Line {i+1} missing key: {key}"

    def test_log_ids_are_unique(self):
        """All log entry IDs must be unique."""
        with open(LOG_FILE, "r") as f:
            lines = [l.strip() for l in f if l.strip()]
        ids = [json.loads(l)["id"] for l in lines]
        assert len(ids) == len(set(ids)), "Duplicate IDs found in log"
