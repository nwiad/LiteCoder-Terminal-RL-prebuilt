"""
Tests for Ubuntu Squid Proxy Server with Time and IP Restrictions.

Validates that the agent correctly:
1. Installed Squid and created a config backup
2. Configured ACLs and access rules
3. Ran proxy tests and recorded results
4. Wrote a valid /app/test_results.json with the correct schema and values
"""

import json
import os
import subprocess


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
TEST_RESULTS_PATH = "/app/test_results.json"
SQUID_CONF_PATH = "/etc/squid/squid.conf"
SQUID_CONF_BACKUP_PATH = "/etc/squid/squid.conf.bak"

# ---------------------------------------------------------------------------
# Expected schema for test_results.json
# ---------------------------------------------------------------------------
BOOLEAN_KEYS = [
    "squid_installed",
    "config_backup_exists",
    "acl_company_net_defined",
    "acl_work_hours_defined",
    "http_access_rules_configured",
    "squid_running",
    "squid_listening_on_3128",
]

TEST_KEYS = [
    "test_allowed_access",
    "test_denied_by_ip",
    "test_denied_by_time",
]

ALL_KEYS = BOOLEAN_KEYS + TEST_KEYS


# ===========================================================================
# Helper
# ===========================================================================
def load_test_results():
    """Load and return the test_results.json as a dict. Returns None on failure."""
    if not os.path.isfile(TEST_RESULTS_PATH):
        return None
    with open(TEST_RESULTS_PATH, "r") as f:
        content = f.read().strip()
    if not content:
        return None
    return json.loads(content)


# ===========================================================================
# 1. File existence & basic validity
# ===========================================================================
class TestFileExistence:
    """Verify that required output files exist and are non-empty."""

    def test_test_results_file_exists(self):
        assert os.path.isfile(TEST_RESULTS_PATH), (
            f"Expected output file {TEST_RESULTS_PATH} does not exist"
        )

    def test_test_results_file_not_empty(self):
        assert os.path.isfile(TEST_RESULTS_PATH), "File missing"
        size = os.path.getsize(TEST_RESULTS_PATH)
        assert size > 10, (
            f"{TEST_RESULTS_PATH} appears empty or too small ({size} bytes)"
        )

    def test_test_results_is_valid_json(self):
        data = load_test_results()
        assert data is not None, (
            f"{TEST_RESULTS_PATH} is missing or not valid JSON"
        )
        assert isinstance(data, dict), (
            f"Expected a JSON object (dict), got {type(data).__name__}"
        )


# ===========================================================================
# 2. Schema validation
# ===========================================================================
class TestSchema:
    """Verify the JSON has exactly the expected keys with correct types."""

    def test_all_required_keys_present(self):
        data = load_test_results()
        assert data is not None, "Cannot load test_results.json"
        for key in ALL_KEYS:
            assert key in data, f"Missing required key: '{key}'"

    def test_boolean_fields_are_booleans(self):
        data = load_test_results()
        assert data is not None, "Cannot load test_results.json"
        for key in BOOLEAN_KEYS:
            assert key in data, f"Missing key: '{key}'"
            assert isinstance(data[key], bool), (
                f"Key '{key}' should be a boolean, got {type(data[key]).__name__}: {data[key]}"
            )

    def test_test_fields_are_strings(self):
        data = load_test_results()
        assert data is not None, "Cannot load test_results.json"
        for key in TEST_KEYS:
            assert key in data, f"Missing key: '{key}'"
            assert isinstance(data[key], str), (
                f"Key '{key}' should be a string, got {type(data[key]).__name__}: {data[key]}"
            )

    def test_test_fields_valid_values(self):
        """test_* fields must be either 'pass' or 'fail'."""
        data = load_test_results()
        assert data is not None, "Cannot load test_results.json"
        for key in TEST_KEYS:
            val = data.get(key, "")
            assert val in ("pass", "fail"), (
                f"Key '{key}' must be 'pass' or 'fail', got '{val}'"
            )


# ===========================================================================
# 3. Core boolean results — all must be true
# ===========================================================================
class TestBooleanResults:
    """Every boolean field in test_results.json must be true."""

    def test_squid_installed(self):
        data = load_test_results()
        assert data is not None, "Cannot load test_results.json"
        assert data.get("squid_installed") is True, (
            "squid_installed should be true"
        )

    def test_config_backup_exists(self):
        data = load_test_results()
        assert data is not None, "Cannot load test_results.json"
        assert data.get("config_backup_exists") is True, (
            "config_backup_exists should be true"
        )

    def test_acl_company_net_defined(self):
        data = load_test_results()
        assert data is not None, "Cannot load test_results.json"
        assert data.get("acl_company_net_defined") is True, (
            "acl_company_net_defined should be true"
        )

    def test_acl_work_hours_defined(self):
        data = load_test_results()
        assert data is not None, "Cannot load test_results.json"
        assert data.get("acl_work_hours_defined") is True, (
            "acl_work_hours_defined should be true"
        )

    def test_http_access_rules_configured(self):
        data = load_test_results()
        assert data is not None, "Cannot load test_results.json"
        assert data.get("http_access_rules_configured") is True, (
            "http_access_rules_configured should be true"
        )

    def test_squid_running(self):
        data = load_test_results()
        assert data is not None, "Cannot load test_results.json"
        assert data.get("squid_running") is True, (
            "squid_running should be true"
        )

    def test_squid_listening_on_3128(self):
        data = load_test_results()
        assert data is not None, "Cannot load test_results.json"
        assert data.get("squid_listening_on_3128") is True, (
            "squid_listening_on_3128 should be true"
        )


# ===========================================================================
# 4. Proxy test results — all must be "pass"
# ===========================================================================
class TestProxyResults:
    """The three proxy test scenarios must all pass."""

    def test_allowed_access_pass(self):
        data = load_test_results()
        assert data is not None, "Cannot load test_results.json"
        assert data.get("test_allowed_access") == "pass", (
            f"test_allowed_access should be 'pass', got '{data.get('test_allowed_access')}'"
        )

    def test_denied_by_ip_pass(self):
        data = load_test_results()
        assert data is not None, "Cannot load test_results.json"
        assert data.get("test_denied_by_ip") == "pass", (
            f"test_denied_by_ip should be 'pass', got '{data.get('test_denied_by_ip')}'"
        )

    def test_denied_by_time_pass(self):
        data = load_test_results()
        assert data is not None, "Cannot load test_results.json"
        assert data.get("test_denied_by_time") == "pass", (
            f"test_denied_by_time should be 'pass', got '{data.get('test_denied_by_time')}'"
        )


# ===========================================================================
# 5. System-level verification (independent of test_results.json)
# ===========================================================================
class TestSystemState:
    """
    Cross-check actual system state to catch agents that just write a
    hardcoded JSON without actually performing the task.
    """

    def test_squid_package_installed(self):
        """Squid package must be installed (dpkg query)."""
        result = subprocess.run(
            ["dpkg", "-l", "squid"],
            capture_output=True, text=True
        )
        # dpkg -l output has '^ii' for installed packages
        assert "ii" in result.stdout, (
            "Squid package does not appear to be installed (dpkg -l squid)"
        )

    def test_squid_conf_backup_exists(self):
        """The backup config file must exist on disk."""
        assert os.path.isfile(SQUID_CONF_BACKUP_PATH), (
            f"Backup config {SQUID_CONF_BACKUP_PATH} does not exist on disk"
        )

    def test_squid_conf_backup_not_empty(self):
        """The backup config file must not be empty."""
        if not os.path.isfile(SQUID_CONF_BACKUP_PATH):
            assert False, f"{SQUID_CONF_BACKUP_PATH} does not exist"
        size = os.path.getsize(SQUID_CONF_BACKUP_PATH)
        assert size > 0, (
            f"{SQUID_CONF_BACKUP_PATH} is empty ({size} bytes)"
        )

    def test_squid_conf_exists(self):
        """The main squid.conf must exist (even after cleanup/restore)."""
        assert os.path.isfile(SQUID_CONF_PATH), (
            f"{SQUID_CONF_PATH} does not exist"
        )

    def test_squid_binary_exists(self):
        """The squid binary should be available on PATH."""
        result = subprocess.run(
            ["which", "squid"],
            capture_output=True, text=True
        )
        assert result.returncode == 0, (
            "squid binary not found on PATH"
        )


# ===========================================================================
# 6. Consistency checks
# ===========================================================================
class TestConsistency:
    """Cross-validate test_results.json against system state."""

    def test_all_checks_passed(self):
        """
        Holistic check: every boolean field is true AND every test field
        is 'pass'. This catches partial solutions.
        """
        data = load_test_results()
        assert data is not None, "Cannot load test_results.json"

        failures = []
        for key in BOOLEAN_KEYS:
            if data.get(key) is not True:
                failures.append(f"{key} = {data.get(key)} (expected true)")
        for key in TEST_KEYS:
            if data.get(key) != "pass":
                failures.append(f"{key} = {data.get(key)} (expected 'pass')")

        assert not failures, (
            "Some checks did not pass:\n  " + "\n  ".join(failures)
        )

    def test_json_no_extra_unexpected_types(self):
        """
        Values should only be bool or str — no nested objects, lists, or
        numbers that would indicate a malformed output.
        """
        data = load_test_results()
        assert data is not None, "Cannot load test_results.json"
        for key in ALL_KEYS:
            val = data.get(key)
            assert isinstance(val, (bool, str)), (
                f"Key '{key}' has unexpected type {type(val).__name__}: {val}"
            )
