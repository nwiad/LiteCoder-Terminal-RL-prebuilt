"""
Tests for Honeypot Log Monitor & Web Dashboard.

Validates:
1. File existence and structure of all required modules
2. log_parser.py: parse_log() correctness including malformed line handling
3. stats.py: compute_stats() correctness with known data
4. app.py: Flask endpoints (/, /api/stats, /events SSE)
5. honeypot_log.jsonl: sample data requirements
"""

import os
import sys
import json
import subprocess
import time
import signal
import importlib
import importlib.util

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
APP_DIR = "/app"
LOG_FILE = os.path.join(APP_DIR, "honeypot_log.jsonl")
LOG_PARSER = os.path.join(APP_DIR, "log_parser.py")
STATS_MODULE = os.path.join(APP_DIR, "stats.py")
APP_MODULE = os.path.join(APP_DIR, "app.py")

REQUIRED_FIELDS = {"timestamp", "src_ip", "username", "password", "success", "session_id"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _load_module(name, filepath):
    """Dynamically load a Python module from a file path."""
    spec = importlib.util.spec_from_file_location(name, filepath)
    mod = importlib.util.module_from_spec(spec)
    # Ensure /app is on sys.path so intra-project imports work
    if APP_DIR not in sys.path:
        sys.path.insert(0, APP_DIR)
    spec.loader.exec_module(mod)
    return mod


def _parse_jsonl_manually(filepath):
    """Reference parser: read JSONL, skip bad lines, return valid entries."""
    entries = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except (json.JSONDecodeError, ValueError):
                continue
            if not isinstance(obj, dict):
                continue
            if not REQUIRED_FIELDS.issubset(obj.keys()):
                continue
            entries.append(obj)
    return entries


# ===========================================================================
# 1. FILE EXISTENCE TESTS
# ===========================================================================
class TestFileExistence:
    def test_log_parser_exists(self):
        assert os.path.isfile(LOG_PARSER), f"{LOG_PARSER} not found"

    def test_stats_module_exists(self):
        assert os.path.isfile(STATS_MODULE), f"{STATS_MODULE} not found"

    def test_app_module_exists(self):
        assert os.path.isfile(APP_MODULE), f"{APP_MODULE} not found"

    def test_log_file_exists(self):
        assert os.path.isfile(LOG_FILE), f"{LOG_FILE} not found"


# ===========================================================================
# 2. SAMPLE LOG FILE VALIDATION
# ===========================================================================
class TestLogFile:
    def test_log_file_not_empty(self):
        assert os.path.getsize(LOG_FILE) > 0, "Log file is empty"

    def test_at_least_10_valid_entries(self):
        entries = _parse_jsonl_manually(LOG_FILE)
        assert len(entries) >= 10, f"Expected >=10 valid entries, got {len(entries)}"

    def test_at_least_2_malformed_lines(self):
        """Count lines that are NOT valid JSON or missing required fields."""
        malformed = 0
        with open(LOG_FILE, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    if not isinstance(obj, dict) or not REQUIRED_FIELDS.issubset(obj.keys()):
                        malformed += 1
                except (json.JSONDecodeError, ValueError):
                    malformed += 1
        assert malformed >= 2, f"Expected >=2 malformed lines, got {malformed}"

    def test_at_least_3_distinct_ips(self):
        entries = _parse_jsonl_manually(LOG_FILE)
        ips = {e["src_ip"] for e in entries}
        assert len(ips) >= 3, f"Expected >=3 distinct IPs, got {len(ips)}"

    def test_at_least_4_distinct_usernames(self):
        entries = _parse_jsonl_manually(LOG_FILE)
        usernames = {e["username"] for e in entries}
        assert len(usernames) >= 4, f"Expected >=4 distinct usernames, got {len(usernames)}"

    def test_entries_have_all_required_fields(self):
        entries = _parse_jsonl_manually(LOG_FILE)
        for i, e in enumerate(entries):
            for field in REQUIRED_FIELDS:
                assert field in e, f"Entry {i} missing field '{field}'"


# ===========================================================================
# 3. LOG PARSER MODULE TESTS
# ===========================================================================
class TestLogParser:
    def test_parse_log_function_exists(self):
        mod = _load_module("log_parser", LOG_PARSER)
        assert hasattr(mod, "parse_log"), "log_parser.py must define parse_log()"
        assert callable(mod.parse_log)

    def test_parse_log_returns_list(self):
        mod = _load_module("log_parser", LOG_PARSER)
        result = mod.parse_log(LOG_FILE)
        assert isinstance(result, list), f"parse_log should return list, got {type(result)}"

    def test_parse_log_skips_malformed(self):
        """parse_log must skip malformed lines — result count should match manual parse."""
        mod = _load_module("log_parser", LOG_PARSER)
        result = mod.parse_log(LOG_FILE)
        expected = _parse_jsonl_manually(LOG_FILE)
        assert len(result) == len(expected), (
            f"parse_log returned {len(result)} entries, expected {len(expected)} "
            "(malformed lines should be skipped)"
        )

    def test_parse_log_entry_fields(self):
        mod = _load_module("log_parser", LOG_PARSER)
        result = mod.parse_log(LOG_FILE)
        assert len(result) > 0, "parse_log returned empty list"
        for i, entry in enumerate(result):
            assert isinstance(entry, dict), f"Entry {i} is not a dict"
            for field in REQUIRED_FIELDS:
                assert field in entry, f"Entry {i} missing field '{field}'"

    def test_parse_log_preserves_values(self):
        """Spot-check that parsed values match the raw file."""
        mod = _load_module("log_parser", LOG_PARSER)
        result = mod.parse_log(LOG_FILE)
        expected = _parse_jsonl_manually(LOG_FILE)
        # Compare first and last entries
        for idx in [0, -1]:
            for field in REQUIRED_FIELDS:
                assert result[idx][field] == expected[idx][field], (
                    f"Mismatch at entry[{idx}]['{field}']: "
                    f"{result[idx][field]} != {expected[idx][field]}"
                )

    def test_parse_log_missing_file(self):
        """parse_log on a non-existent file should return empty list, not crash."""
        mod = _load_module("log_parser", LOG_PARSER)
        result = mod.parse_log("/app/nonexistent_file_xyz.jsonl")
        assert isinstance(result, list), "Should return a list for missing file"
        assert len(result) == 0, "Should return empty list for missing file"

    def test_parse_log_with_crafted_malformed(self, tmp_path):
        """Test with a file containing only malformed data."""
        bad_file = tmp_path / "bad.jsonl"
        bad_file.write_text("not json\n{broken\n[1,2,3]\n")
        mod = _load_module("log_parser", LOG_PARSER)
        result = mod.parse_log(str(bad_file))
        assert result == [], f"Expected empty list for all-malformed file, got {len(result)} entries"

    def test_parse_log_with_missing_fields(self, tmp_path):
        """Entries missing required fields should be skipped."""
        partial_file = tmp_path / "partial.jsonl"
        # Missing 'session_id'
        partial_file.write_text(
            '{"timestamp":"2025-01-01T00:00:00Z","src_ip":"1.2.3.4","username":"a","password":"b","success":false}\n'
        )
        mod = _load_module("log_parser", LOG_PARSER)
        result = mod.parse_log(str(partial_file))
        assert result == [], "Entries missing required fields should be skipped"


# ===========================================================================
# 4. STATS MODULE TESTS
# ===========================================================================
class TestStats:
    def _get_stats(self):
        parser = _load_module("log_parser", LOG_PARSER)
        stats_mod = _load_module("stats", STATS_MODULE)
        entries = parser.parse_log(LOG_FILE)
        return stats_mod.compute_stats(entries), entries

    def test_compute_stats_function_exists(self):
        mod = _load_module("stats", STATS_MODULE)
        assert hasattr(mod, "compute_stats"), "stats.py must define compute_stats()"
        assert callable(mod.compute_stats)

    def test_compute_stats_returns_dict(self):
        stats, _ = self._get_stats()
        assert isinstance(stats, dict), f"compute_stats should return dict, got {type(stats)}"

    def test_required_keys_present(self):
        stats, _ = self._get_stats()
        required_keys = {
            "total_attempts", "unique_ips", "top_usernames",
            "top_ips", "earliest_timestamp", "latest_timestamp", "success_count",
        }
        for key in required_keys:
            assert key in stats, f"Missing key '{key}' in compute_stats output"

    def test_total_attempts(self):
        stats, entries = self._get_stats()
        assert stats["total_attempts"] == len(entries), (
            f"total_attempts={stats['total_attempts']}, expected {len(entries)}"
        )

    def test_unique_ips(self):
        stats, entries = self._get_stats()
        expected_unique = len({e["src_ip"] for e in entries})
        assert stats["unique_ips"] == expected_unique, (
            f"unique_ips={stats['unique_ips']}, expected {expected_unique}"
        )

    def test_success_count(self):
        stats, entries = self._get_stats()
        expected_success = sum(1 for e in entries if e.get("success") is True)
        assert stats["success_count"] == expected_success, (
            f"success_count={stats['success_count']}, expected {expected_success}"
        )

    def test_earliest_timestamp(self):
        stats, entries = self._get_stats()
        expected = min(e["timestamp"] for e in entries)
        assert stats["earliest_timestamp"] == expected, (
            f"earliest_timestamp={stats['earliest_timestamp']}, expected {expected}"
        )

    def test_latest_timestamp(self):
        stats, entries = self._get_stats()
        expected = max(e["timestamp"] for e in entries)
        assert stats["latest_timestamp"] == expected, (
            f"latest_timestamp={stats['latest_timestamp']}, expected {expected}"
        )

    def test_top_usernames_format(self):
        stats, _ = self._get_stats()
        top = stats["top_usernames"]
        assert isinstance(top, list), "top_usernames must be a list"
        assert len(top) <= 5, f"top_usernames has {len(top)} items, max is 5"
        for item in top:
            assert isinstance(item, (list, tuple)) and len(item) == 2, (
                f"Each top_usernames item must be [username, count], got {item}"
            )
            assert isinstance(item[0], str), f"Username must be str, got {type(item[0])}"
            assert isinstance(item[1], int), f"Count must be int, got {type(item[1])}"

    def test_top_usernames_sorted_correctly(self):
        """Top usernames: sorted by count desc, then username asc."""
        stats, entries = self._get_stats()
        top = stats["top_usernames"]
        from collections import Counter
        counter = Counter(e["username"] for e in entries)
        expected = sorted(counter.items(), key=lambda x: (-x[1], x[0]))[:5]
        expected = [[u, c] for u, c in expected]
        assert len(top) == len(expected), (
            f"top_usernames length {len(top)} != expected {len(expected)}"
        )
        for i, (got, exp) in enumerate(zip(top, expected)):
            assert got[0] == exp[0] and got[1] == exp[1], (
                f"top_usernames[{i}]={got}, expected {exp}"
            )

    def test_top_ips_format(self):
        stats, _ = self._get_stats()
        top = stats["top_ips"]
        assert isinstance(top, list), "top_ips must be a list"
        assert len(top) <= 5, f"top_ips has {len(top)} items, max is 5"
        for item in top:
            assert isinstance(item, (list, tuple)) and len(item) == 2, (
                f"Each top_ips item must be [ip, count], got {item}"
            )

    def test_top_ips_sorted_correctly(self):
        """Top IPs: sorted by count desc, then IP string asc."""
        stats, entries = self._get_stats()
        top = stats["top_ips"]
        from collections import Counter
        counter = Counter(e["src_ip"] for e in entries)
        expected = sorted(counter.items(), key=lambda x: (-x[1], x[0]))[:5]
        expected = [[ip, c] for ip, c in expected]
        for i, (got, exp) in enumerate(zip(top, expected)):
            assert got[0] == exp[0] and got[1] == exp[1], (
                f"top_ips[{i}]={got}, expected {exp}"
            )

    def test_compute_stats_empty_input(self):
        """compute_stats with empty list should return zeros/nulls."""
        stats_mod = _load_module("stats", STATS_MODULE)
        stats = stats_mod.compute_stats([])
        assert stats["total_attempts"] == 0
        assert stats["unique_ips"] == 0
        assert stats["success_count"] == 0
        assert stats["earliest_timestamp"] is None
        assert stats["latest_timestamp"] is None
        assert stats["top_usernames"] == []
        assert stats["top_ips"] == []


# ===========================================================================
# 5. FLASK APP TESTS
# ===========================================================================
import requests
import threading

# We start the Flask server once for all web tests
_server_process = None
_BASE_URL = "http://127.0.0.1:8080"


def _ensure_server_running():
    """Start the Flask server if not already running."""
    global _server_process
    if _server_process is not None and _server_process.poll() is None:
        return  # already running

    # Try to connect first — maybe the agent already started it
    try:
        r = requests.get(_BASE_URL + "/", timeout=2)
        if r.status_code == 200:
            return
    except Exception:
        pass

    # Start the server as a subprocess
    _server_process = subprocess.Popen(
        [sys.executable, APP_MODULE],
        cwd=APP_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    # Wait for it to be ready
    for _ in range(20):
        try:
            r = requests.get(_BASE_URL + "/", timeout=1)
            if r.status_code == 200:
                return
        except Exception:
            pass
        time.sleep(0.5)
    raise RuntimeError("Flask server did not start within 10 seconds")


def _stop_server():
    global _server_process
    if _server_process is not None and _server_process.poll() is None:
        _server_process.terminate()
        try:
            _server_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _server_process.kill()
        _server_process = None


class TestFlaskApp:
    @classmethod
    def setup_class(cls):
        _ensure_server_running()

    def test_index_returns_200(self):
        r = requests.get(f"{_BASE_URL}/", timeout=5)
        assert r.status_code == 200, f"GET / returned {r.status_code}"

    def test_index_is_html(self):
        r = requests.get(f"{_BASE_URL}/", timeout=5)
        ct = r.headers.get("Content-Type", "")
        assert "text/html" in ct, f"GET / Content-Type should be text/html, got {ct}"

    def test_index_has_log_table(self):
        r = requests.get(f"{_BASE_URL}/", timeout=5)
        body = r.text
        assert 'id="log-table"' in body or "id='log-table'" in body, (
            "HTML must contain a <table> with id='log-table'"
        )

    def test_index_has_stats_div(self):
        r = requests.get(f"{_BASE_URL}/", timeout=5)
        body = r.text
        assert 'id="stats"' in body or "id='stats'" in body, (
            "HTML must contain a <div> with id='stats'"
        )

    def test_index_has_eventsource_js(self):
        """The HTML must include JS that connects to /events SSE endpoint."""
        r = requests.get(f"{_BASE_URL}/", timeout=5)
        body = r.text
        assert "EventSource" in body, (
            "HTML must include JavaScript using EventSource for SSE"
        )
        assert "/events" in body, (
            "HTML must reference the /events SSE endpoint"
        )

    def test_api_stats_returns_json(self):
        r = requests.get(f"{_BASE_URL}/api/stats", timeout=5)
        assert r.status_code == 200, f"GET /api/stats returned {r.status_code}"
        ct = r.headers.get("Content-Type", "")
        assert "application/json" in ct, f"Expected application/json, got {ct}"

    def test_api_stats_has_required_keys(self):
        r = requests.get(f"{_BASE_URL}/api/stats", timeout=5)
        data = r.json()
        required_keys = {
            "total_attempts", "unique_ips", "top_usernames",
            "top_ips", "earliest_timestamp", "latest_timestamp", "success_count",
        }
        for key in required_keys:
            assert key in data, f"Missing key '{key}' in /api/stats response"

    def test_api_stats_values_match_modules(self):
        """The /api/stats endpoint should return the same data as compute_stats."""
        r = requests.get(f"{_BASE_URL}/api/stats", timeout=5)
        api_data = r.json()

        parser = _load_module("log_parser", LOG_PARSER)
        stats_mod = _load_module("stats", STATS_MODULE)
        entries = parser.parse_log(LOG_FILE)
        expected = stats_mod.compute_stats(entries)

        assert api_data["total_attempts"] == expected["total_attempts"]
        assert api_data["unique_ips"] == expected["unique_ips"]
        assert api_data["success_count"] == expected["success_count"]

    def test_events_endpoint_content_type(self):
        """GET /events must return text/event-stream."""
        r = requests.get(f"{_BASE_URL}/events", timeout=5, stream=True)
        ct = r.headers.get("Content-Type", "")
        assert "text/event-stream" in ct, (
            f"GET /events Content-Type should be text/event-stream, got {ct}"
        )
        r.close()

    def test_events_streams_valid_entries(self):
        """SSE endpoint should stream existing log entries as data: <json> messages."""
        r = requests.get(f"{_BASE_URL}/events", timeout=5, stream=True)
        entries_received = []
        deadline = time.time() + 8  # read for up to 8 seconds

        try:
            for raw_line in r.iter_lines(decode_unicode=True):
                if time.time() > deadline:
                    break
                if raw_line is None:
                    continue
                line = raw_line.strip()
                if not line:
                    continue
                if line.startswith("data:"):
                    payload = line[len("data:"):].strip()
                    try:
                        obj = json.loads(payload)
                        if isinstance(obj, dict) and "src_ip" in obj:
                            entries_received.append(obj)
                    except (json.JSONDecodeError, ValueError):
                        pass
                # Stop once we've received a reasonable number
                expected_count = len(_parse_jsonl_manually(LOG_FILE))
                if len(entries_received) >= expected_count:
                    break
        finally:
            r.close()

        expected_count = len(_parse_jsonl_manually(LOG_FILE))
        assert len(entries_received) >= expected_count, (
            f"SSE streamed {len(entries_received)} entries, expected >= {expected_count}"
        )

        # Verify each streamed entry has required fields
        for i, entry in enumerate(entries_received[:expected_count]):
            for field in REQUIRED_FIELDS:
                assert field in entry, (
                    f"SSE entry {i} missing field '{field}'"
                )

    def test_events_sse_format(self):
        """Each SSE message must use 'data: <json>\\n\\n' format."""
        r = requests.get(f"{_BASE_URL}/events", timeout=5, stream=True)
        raw_data = b""
        deadline = time.time() + 5

        try:
            for chunk in r.iter_content(chunk_size=1024):
                raw_data += chunk
                if time.time() > deadline or len(raw_data) > 8192:
                    break
        finally:
            r.close()

        text = raw_data.decode("utf-8", errors="replace")
        # Must contain at least one "data: " line
        assert "data: " in text, "SSE stream must contain 'data: ' prefixed messages"
        # Check double-newline separation (SSE spec)
        assert "\n\n" in text, "SSE messages must be separated by double newlines"
