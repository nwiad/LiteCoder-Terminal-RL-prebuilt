"""
Tests for Node.js Cluster-Based Load Balancer.

These tests validate the running load balancer by hitting its HTTP endpoints
and verifying correct behavior: structure, round-robin, health checks, status.
"""

import os
import json
import time
import subprocess
import socket
import urllib.request
import urllib.error


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

MASTER_PORT = 8080
WORKER_BASE_PORT = 3001
BASE_URL = f"http://127.0.0.1:{MASTER_PORT}"
INDEX_JS_PATH = "/app/index.js"


def http_get(url, timeout=5):
    """Simple HTTP GET returning (status_code, parsed_json_or_None, raw_body)."""
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                data = None
            return resp.status, data, body
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8") if e.fp else ""
        try:
            data = json.loads(body)
        except Exception:
            data = None
        return e.code, data, body
    except Exception as e:
        return None, None, str(e)


def wait_for_port(port, host="127.0.0.1", retries=30, delay=0.5):
    """Wait until a TCP port is accepting connections."""
    for _ in range(retries):
        try:
            with socket.create_connection((host, port), timeout=2):
                return True
        except OSError:
            time.sleep(delay)
    return False


# ---------------------------------------------------------------------------
# 1. File existence and basic validity
# ---------------------------------------------------------------------------

class TestFileExistence:
    """Verify the entry point file exists and is valid Node.js."""

    def test_index_js_exists(self):
        """index.js must exist at /app/index.js."""
        assert os.path.isfile(INDEX_JS_PATH), (
            f"Entry point {INDEX_JS_PATH} does not exist"
        )

    def test_index_js_not_empty(self):
        """index.js must not be empty."""
        assert os.path.getsize(INDEX_JS_PATH) > 100, (
            "index.js appears to be empty or trivially small"
        )

    def test_index_js_uses_cluster_module(self):
        """index.js must use the cluster module (core requirement)."""
        with open(INDEX_JS_PATH, "r") as f:
            content = f.read()
        assert "cluster" in content, (
            "index.js does not reference the cluster module"
        )

    def test_index_js_uses_http_module(self):
        """index.js must use the http module."""
        with open(INDEX_JS_PATH, "r") as f:
            content = f.read()
        assert "http" in content, (
            "index.js does not reference the http module"
        )

    def test_no_node_modules(self):
        """No external npm packages should be installed."""
        assert not os.path.isdir("/app/node_modules"), (
            "node_modules directory found — no external packages allowed"
        )

    def test_no_package_json_dependencies(self):
        """If package.json exists, it should have no dependencies."""
        pkg_path = "/app/package.json"
        if os.path.isfile(pkg_path):
            with open(pkg_path, "r") as f:
                try:
                    pkg = json.loads(f.read())
                except json.JSONDecodeError:
                    return  # malformed, but not our concern here
            deps = pkg.get("dependencies", {})
            assert len(deps) == 0, (
                f"package.json has external dependencies: {deps}"
            )


# ---------------------------------------------------------------------------
# 2. Master /lb-status endpoint
# ---------------------------------------------------------------------------

class TestLbStatus:
    """Validate the /lb-status endpoint served by the master process."""

    def test_lb_status_reachable(self):
        """Master must be listening on port 8080."""
        assert wait_for_port(MASTER_PORT, retries=30), (
            f"Port {MASTER_PORT} never became reachable"
        )

    def test_lb_status_returns_200(self):
        status, data, _ = http_get(f"{BASE_URL}/lb-status")
        assert status == 200, f"Expected 200, got {status}"

    def test_lb_status_is_json(self):
        status, data, raw = http_get(f"{BASE_URL}/lb-status")
        assert data is not None, f"Response is not valid JSON: {raw[:200]}"

    def test_lb_status_has_required_fields(self):
        """Must contain totalWorkers, healthyWorkers, unhealthyWorkers,
        totalRequests, and workers array."""
        _, data, _ = http_get(f"{BASE_URL}/lb-status")
        assert data is not None, "No JSON response"
        for field in ["totalWorkers", "healthyWorkers", "unhealthyWorkers",
                      "totalRequests", "workers"]:
            assert field in data, f"Missing field '{field}' in /lb-status"

    def test_lb_status_total_workers_at_least_2(self):
        """Minimum 2 workers even on single-core machines."""
        _, data, _ = http_get(f"{BASE_URL}/lb-status")
        assert data is not None
        assert isinstance(data["totalWorkers"], int)
        assert data["totalWorkers"] >= 2, (
            f"totalWorkers={data['totalWorkers']}, expected >= 2"
        )

    def test_lb_status_workers_array_length(self):
        """workers array length must match totalWorkers."""
        _, data, _ = http_get(f"{BASE_URL}/lb-status")
        assert data is not None
        assert len(data["workers"]) == data["totalWorkers"]

    def test_lb_status_worker_entries_have_required_fields(self):
        """Each worker entry must have workerId, port, pid, healthy,
        requestsServed."""
        _, data, _ = http_get(f"{BASE_URL}/lb-status")
        assert data is not None
        for i, w in enumerate(data["workers"]):
            for field in ["workerId", "port", "pid", "healthy",
                          "requestsServed"]:
                assert field in w, (
                    f"Worker {i} missing field '{field}'"
                )

    def test_lb_status_worker_ports_sequential(self):
        """Worker ports must start at 3001 and be sequential."""
        _, data, _ = http_get(f"{BASE_URL}/lb-status")
        assert data is not None
        ports = sorted(w["port"] for w in data["workers"])
        expected = list(range(WORKER_BASE_PORT,
                              WORKER_BASE_PORT + len(ports)))
        assert ports == expected, (
            f"Worker ports {ports} != expected {expected}"
        )

    def test_lb_status_healthy_unhealthy_sum(self):
        """healthyWorkers + unhealthyWorkers must equal totalWorkers."""
        _, data, _ = http_get(f"{BASE_URL}/lb-status")
        assert data is not None
        assert (data["healthyWorkers"] + data["unhealthyWorkers"]
                == data["totalWorkers"])

    def test_lb_status_all_healthy_at_start(self):
        """Under normal operation all workers should be healthy."""
        # Give health checks time to run
        time.sleep(4)
        _, data, _ = http_get(f"{BASE_URL}/lb-status")
        assert data is not None
        assert data["healthyWorkers"] == data["totalWorkers"], (
            f"Not all workers healthy: {data['healthyWorkers']}/{data['totalWorkers']}"
        )


# ---------------------------------------------------------------------------
# 3. Worker /health endpoint (direct access on worker ports)
# ---------------------------------------------------------------------------

class TestWorkerHealth:
    """Validate worker /health endpoints on their individual ports."""

    def test_worker_port_3001_reachable(self):
        assert wait_for_port(WORKER_BASE_PORT, retries=20), (
            f"Worker port {WORKER_BASE_PORT} not reachable"
        )

    def test_worker_health_returns_200(self):
        status, data, _ = http_get(
            f"http://127.0.0.1:{WORKER_BASE_PORT}/health"
        )
        assert status == 200, f"Expected 200, got {status}"

    def test_worker_health_json_fields(self):
        """Worker /health must return status, workerId, pid, uptime."""
        _, data, _ = http_get(
            f"http://127.0.0.1:{WORKER_BASE_PORT}/health"
        )
        assert data is not None, "Worker /health did not return JSON"
        for field in ["status", "workerId", "pid", "uptime"]:
            assert field in data, (
                f"Missing field '{field}' in worker /health"
            )

    def test_worker_health_status_ok(self):
        _, data, _ = http_get(
            f"http://127.0.0.1:{WORKER_BASE_PORT}/health"
        )
        assert data is not None
        assert data["status"] == "ok", (
            f"Expected status 'ok', got '{data.get('status')}'"
        )

    def test_worker_health_pid_is_integer(self):
        _, data, _ = http_get(
            f"http://127.0.0.1:{WORKER_BASE_PORT}/health"
        )
        assert data is not None
        assert isinstance(data["pid"], int), (
            f"pid should be int, got {type(data['pid'])}"
        )

    def test_worker_health_uptime_is_number(self):
        _, data, _ = http_get(
            f"http://127.0.0.1:{WORKER_BASE_PORT}/health"
        )
        assert data is not None
        assert isinstance(data["uptime"], (int, float)), (
            f"uptime should be a number, got {type(data['uptime'])}"
        )

    def test_multiple_worker_ports_reachable(self):
        """At least 2 worker ports (3001, 3002) must be listening."""
        for port in [WORKER_BASE_PORT, WORKER_BASE_PORT + 1]:
            assert wait_for_port(port, retries=10), (
                f"Worker port {port} not reachable"
            )

    def test_different_workers_have_different_pids(self):
        """Workers on different ports must be separate processes."""
        _, d1, _ = http_get(
            f"http://127.0.0.1:{WORKER_BASE_PORT}/health"
        )
        _, d2, _ = http_get(
            f"http://127.0.0.1:{WORKER_BASE_PORT + 1}/health"
        )
        assert d1 is not None and d2 is not None
        assert d1["pid"] != d2["pid"], (
            "Workers on different ports have the same PID — "
            "they should be separate processes"
        )


# ---------------------------------------------------------------------------
# 4. Round-robin proxying through master
# ---------------------------------------------------------------------------

class TestRoundRobin:
    """Verify that the master distributes requests across workers."""

    def test_proxied_request_returns_200(self):
        status, data, _ = http_get(f"{BASE_URL}/test-path")
        assert status == 200, f"Expected 200, got {status}"

    def test_proxied_request_has_worker_fields(self):
        """Proxied response must contain workerId, pid, path."""
        _, data, _ = http_get(f"{BASE_URL}/some-path")
        assert data is not None, "Proxied response is not JSON"
        for field in ["workerId", "pid", "path"]:
            assert field in data, (
                f"Missing field '{field}' in proxied response"
            )

    def test_proxied_request_returns_correct_path(self):
        _, data, _ = http_get(f"{BASE_URL}/hello-world")
        assert data is not None
        assert data["path"] == "/hello-world", (
            f"Expected path '/hello-world', got '{data.get('path')}'"
        )

    def test_round_robin_distributes_to_multiple_workers(self):
        """Sending multiple requests must hit more than one worker."""
        # Get number of workers first
        _, status_data, _ = http_get(f"{BASE_URL}/lb-status")
        assert status_data is not None
        num_workers = status_data["totalWorkers"]

        # Send enough requests to cycle through all workers at least once
        worker_ids = set()
        for i in range(num_workers * 2):
            _, data, _ = http_get(f"{BASE_URL}/rr-test-{i}")
            if data and "workerId" in data:
                worker_ids.add(data["workerId"])

        assert len(worker_ids) >= 2, (
            f"Only hit {len(worker_ids)} worker(s) — "
            "round-robin should distribute across multiple workers"
        )

    def test_round_robin_hits_all_workers(self):
        """With enough requests, all healthy workers should be hit."""
        _, status_data, _ = http_get(f"{BASE_URL}/lb-status")
        assert status_data is not None
        num_workers = status_data["totalWorkers"]

        worker_ids = set()
        # Send 3x workers requests to ensure full coverage
        for i in range(num_workers * 3):
            _, data, _ = http_get(f"{BASE_URL}/rr-all-{i}")
            if data and "workerId" in data:
                worker_ids.add(data["workerId"])

        assert len(worker_ids) == num_workers, (
            f"Hit {len(worker_ids)} workers out of {num_workers} — "
            "round-robin should eventually reach all workers"
        )

    def test_request_count_increments(self):
        """totalRequests in /lb-status must increase after proxied requests."""
        _, before, _ = http_get(f"{BASE_URL}/lb-status")
        assert before is not None
        before_count = before["totalRequests"]

        # Send 3 proxied requests
        for i in range(3):
            http_get(f"{BASE_URL}/count-test-{i}")

        _, after, _ = http_get(f"{BASE_URL}/lb-status")
        assert after is not None
        assert after["totalRequests"] >= before_count + 3, (
            f"totalRequests went from {before_count} to "
            f"{after['totalRequests']} after 3 requests — expected +3"
        )

    def test_requests_served_distributed(self):
        """requestsServed across workers should reflect distribution."""
        # Reset baseline
        _, before, _ = http_get(f"{BASE_URL}/lb-status")
        assert before is not None
        before_served = {
            w["port"]: w["requestsServed"] for w in before["workers"]
        }

        num_workers = before["totalWorkers"]
        # Send exactly num_workers requests
        for i in range(num_workers):
            http_get(f"{BASE_URL}/dist-test-{i}")

        _, after, _ = http_get(f"{BASE_URL}/lb-status")
        assert after is not None

        total_new = sum(
            w["requestsServed"] - before_served.get(w["port"], 0)
            for w in after["workers"]
        )
        assert total_new == num_workers, (
            f"Sum of new requestsServed={total_new}, expected {num_workers}"
        )


# ---------------------------------------------------------------------------
# 5. Content-Type and response format validation
# ---------------------------------------------------------------------------

class TestResponseFormat:
    """Verify JSON content type and response structure details."""

    def test_lb_status_content_type(self):
        """Master /lb-status must return application/json."""
        try:
            req = urllib.request.Request(f"{BASE_URL}/lb-status")
            with urllib.request.urlopen(req, timeout=5) as resp:
                ct = resp.headers.get("Content-Type", "")
                assert "application/json" in ct, (
                    f"Expected application/json, got '{ct}'"
                )
        except Exception as e:
            assert False, f"Failed to reach /lb-status: {e}"

    def test_worker_health_content_type(self):
        """Worker /health must return application/json."""
        try:
            req = urllib.request.Request(
                f"http://127.0.0.1:{WORKER_BASE_PORT}/health"
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                ct = resp.headers.get("Content-Type", "")
                assert "application/json" in ct, (
                    f"Expected application/json, got '{ct}'"
                )
        except Exception as e:
            assert False, f"Failed to reach worker /health: {e}"

    def test_proxied_response_content_type(self):
        """Proxied responses must return application/json."""
        try:
            req = urllib.request.Request(f"{BASE_URL}/ct-test")
            with urllib.request.urlopen(req, timeout=5) as resp:
                ct = resp.headers.get("Content-Type", "")
                assert "application/json" in ct, (
                    f"Expected application/json, got '{ct}'"
                )
        except Exception as e:
            assert False, f"Failed to reach proxied endpoint: {e}"

    def test_lb_status_total_requests_is_integer(self):
        _, data, _ = http_get(f"{BASE_URL}/lb-status")
        assert data is not None
        assert isinstance(data["totalRequests"], int), (
            f"totalRequests should be int, got {type(data['totalRequests'])}"
        )

    def test_lb_status_worker_healthy_is_boolean(self):
        _, data, _ = http_get(f"{BASE_URL}/lb-status")
        assert data is not None
        for w in data["workers"]:
            assert isinstance(w["healthy"], bool), (
                f"Worker healthy should be bool, got {type(w['healthy'])}"
            )

    def test_lb_status_worker_requests_served_is_integer(self):
        _, data, _ = http_get(f"{BASE_URL}/lb-status")
        assert data is not None
        for w in data["workers"]:
            assert isinstance(w["requestsServed"], int), (
                f"requestsServed should be int, got "
                f"{type(w['requestsServed'])}"
            )

    def test_lb_status_worker_pid_is_integer(self):
        _, data, _ = http_get(f"{BASE_URL}/lb-status")
        assert data is not None
        for w in data["workers"]:
            assert isinstance(w["pid"], int), (
                f"Worker pid should be int, got {type(w['pid'])}"
            )

    def test_lb_status_worker_port_is_integer(self):
        _, data, _ = http_get(f"{BASE_URL}/lb-status")
        assert data is not None
        for w in data["workers"]:
            assert isinstance(w["port"], int), (
                f"Worker port should be int, got {type(w['port'])}"
            )


# ---------------------------------------------------------------------------
# 6. Edge case: /lb-status is NOT proxied
# ---------------------------------------------------------------------------

class TestLbStatusNotProxied:
    """Verify /lb-status is served by master, not forwarded to a worker."""

    def test_lb_status_does_not_contain_worker_response_fields(self):
        """/lb-status response should NOT have workerId/pid/path at top level
        like a worker catch-all response would."""
        _, data, _ = http_get(f"{BASE_URL}/lb-status")
        assert data is not None
        # A worker catch-all returns {workerId, pid, path}
        # /lb-status returns {totalWorkers, healthyWorkers, ...}
        assert "totalWorkers" in data, (
            "/lb-status missing totalWorkers — may be proxied to worker"
        )
        assert "path" not in data, (
            "/lb-status has 'path' field — looks like it was proxied "
            "to a worker instead of handled by master"
        )

